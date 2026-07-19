# catch-domain — Design Spec

**Date:** 2026-07-19
**Status:** Approved design, pending implementation plan

## Purpose

A personal Python CLI tool that takes a list of candidate brand names and reports
which ones are safe to use — meaning the name (and its likely lookalikes, e.g.
`enlanceit` for `enlance`) is not already claimed on the internet.

Primary use: shortlist a name for the user's new IT services agency.
A public web product was considered and deliberately deferred; this tool should be
structured cleanly enough to grow into one later, but nothing is built for that now.

## Non-goals

- **No name generation.** Candidates come from an input file (LLM chat + user ideas).
- **No trademark automation.** No reliable free API (especially IP India). The report
  reminds the user to check trademarks manually for the final shortlist.
- **No social-handle scraping.** Brittle, bot-blocked. Manual step for finalists.
- **No web UI, no hosting, no async.** Sequential script is fast enough for ~50 names.

## User workflow

1. Put candidate names in `names.txt` (one per line, `#` comments allowed).
2. Run: `python -m catch_domain names.txt`
3. Read the ranked console table; open `report.csv` for full evidence.
4. Manually check trademarks + social handles for the top 3–5 CLEAN names.

## Pipeline (cheap checks first, expensive check last)

### Stage 0 — Normalize + variant expansion
- Normalize: lowercase, strip whitespace/punctuation.
- Expand each name into collision variants using configurable lists:
  - Suffixes (default): `it, hq, app, tech, labs, io, agency, ly`
  - Prefixes (default): `get, my, the`
  - The base name itself is always included.
- Lists live in `config.py` so the user can tune them without touching logic.

### Stage 1 — DNS resolution (free, unlimited)
- For every (base + variant) × TLD combo, attempt DNS resolution (A/AAAA/CNAME/NS).
- Default TLDs: `.com, .in, .io, .tech, .dev, .agency` (overridable via `--tlds`).
- Resolves → domain is registered and active. Record it; skip RDAP for this combo.

### Stage 1.5 — Lookalike discovery via Certificate Transparency (free, wildcard)
- One wildcard query per base name: `https://crt.sh/?q=%25<name>%25&output=json`.
  Certificate Transparency logs record every HTTPS certificate ever issued, and
  crt.sh supports SQL-LIKE `%` wildcards — so this finds *real existing* lookalike
  domains (`enlancesolutions.com`, `techenlance.in`, …), not just guessed ones.
- Parse the JSON, extract distinct registrable domains containing the name,
  dedupe (a cert's `name_value` may list several hosts), record as evidence.
- Noise guard: skip this stage (with a console warning) for names shorter than
  5 characters — substring matching on short names is mostly false positives
  (e.g. `flint` → `flintstonecars.com`).
- Complementary, not a replacement: CT only sees domains that ever had an HTTPS
  cert, so the generated-variant checks (Stages 1–2) still catch cert-less
  parked domains.
- crt.sh is free and often slow: generous timeout, one retry, then `unknown`.

### Stage 2 — RDAP registration check (free, official)
- For combos that did NOT resolve, query RDAP (official WHOIS successor, no key):
  - Use the rdap.org bootstrap redirect (`https://rdap.org/domain/<domain>`).
  - HTTP 404 → genuinely unregistered. HTTP 200 → registered but inactive (parked).
  - Other statuses / timeouts → `unknown` (scored cautiously, does not abort run).
- Polite pacing: small fixed delay between RDAP requests.

### Stage 2b — Liveness probe
- For domains that resolved in Stage 1, issue an HTTP(S) HEAD/GET with a short
  timeout to distinguish "live website" from "registered, DNS on, but no real site".
- Any 2xx/3xx response → live. Errors/timeouts → registered-but-not-live.

### Stage 3 — Web presence via DuckDuckGo (`ddgs` library), survivors only
- Skip entirely for names already verdicted TAKEN by domain evidence.
- Queries per surviving name (max 3): exact-match `"<base>"`, plus the first two
  suffix variants (e.g. `"<base>it"`, `"<base>hq"`).
- Record result count and top hits (title + URL) as evidence.
- Politeness: ~3s delay between queries. If DDG throttles or errors, mark the
  name's search status `pending` and continue — never crash the run.
- `--no-search` flag skips this stage entirely.

## Scoring and verdicts

Rank names by a risk score (lower = safer). Initial weights (tunable in `config.py`):

| Signal | Points |
|---|---|
| Base name live website on `.com` or `.in` | +50 each |
| Base name registered (no live site) on `.com`/`.in` | +25 |
| Base name live on other TLD | +15 |
| Base name registered on other TLD | +8 |
| Variant live website (any TLD) | +10 |
| Variant registered on `.com` | +6 |
| Variant registered on other TLD | +3 |
| Distinct lookalike domain found via CT logs (Stage 1.5) | +3 each (cap +15) |
| DDG hit matching base name (exact name token appears in the hit's title or URL) | +5 each (cap +30) |
| DDG hit matching a variant (same rule) | +2 each (cap +10) |
| Any check returned `unknown` | +2 each |

Verdicts:
- **TAKEN** — score ≥ 50, or hard rule: live website on base `.com`.
- **RISKY** — score 15–49. Evidence attached; user judges.
- **CLEAN** — score ≤ 14.

Ranking, not binary rejection: literal zero-footprint is an impossible bar, so the
tool surfaces evidence and lets the user decide on RISKY names.

## Caching

- Every check result is cached in `cache.json` in the project directory,
  keyed `"<check_type>:<target>"` with the result and a timestamp.
- Reruns only perform checks missing from the cache (new names/variants).
- `--refresh` ignores and rewrites the cache.

## Output

- **Console:** table sorted safest-first: name, verdict, score, one-line evidence
  summary. Search-pending names flagged.
- **`report.csv`:** one row per (name, evidence item) with check type, target,
  result — the full audit trail.
- **Footer / final section:** manual next-steps checklist for shortlisted names:
  1. Trademark search — IP India public search; USPTO TESS if targeting US.
  2. Social handles — GitHub, LinkedIn, Instagram, X.

## Code structure

```
catch_domain/
  __main__.py      # CLI entry: args, orchestration
  config.py        # TLDs, variant lists, scoring weights, delays
  variants.py      # normalization + variant expansion
  dns_check.py     # Stage 1
  ct_check.py      # Stage 1.5 (crt.sh wildcard lookalike discovery)
  rdap_check.py    # Stage 2
  liveness.py      # Stage 2b
  search_check.py  # Stage 3 (ddgs)
  scoring.py       # score + verdict
  cache.py         # JSON cache load/save
  report.py        # console table + CSV
tests/             # pytest; network clients mocked
names.txt          # user's candidate list (example committed)
```

**Stack:** Python 3.11+, `dnspython`, `requests`, `ddgs`, `pytest`.

## Error handling

- Network failures/timeouts → result `unknown`, +2 score, run continues.
- DDG throttling → search status `pending` for remaining names, run continues.
- RDAP per-TLD failures fall back through the rdap.org bootstrap; still `unknown`
  on total failure.
- crt.sh timeout or bad response → one retry, then `unknown`; run continues with
  the other evidence sources.
- Malformed input lines (spaces, uppercase, punctuation) are normalized, not rejected;
  empty file or unreadable file → clear error message.

## Success criteria

- First run on ~50 names completes in under ~10 minutes.
- Rerun with cache is near-instant and only checks new names.
- Output ranks names with clear evidence; DDG failure degrades gracefully
  (domain-level verdicts still delivered).
- User ends up with 3–5 CLEAN candidates plus a manual-check reminder.
