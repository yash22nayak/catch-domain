# catch-domain

A small Python CLI that helps you pick a brand / product name. It reads your
candidate names from a text file, checks each one (and its common lookalike
variants) against **free** internet signals, and prints a ranked
**CLEAN / RISKY / TAKEN** report — so you spend your manual research time only
on names that are actually worth it.

No API keys, no paid services. Results are cached on disk, so re-runs only
perform checks that are new.

## What it checks

Each name goes through a staged funnel, cheapest checks first:

| Stage | Check | Source |
|-------|-------|--------|
| 0 | Variant expansion — `name` plus suffix/prefix lookalikes (`nameit`, `namehq`, `getname`, …) | local |
| 1 | DNS resolution for every variant × TLD (`com, in, io, tech, dev, agency` by default) | DNS |
| 1.5 | Existing lookalike domains that ever had an HTTPS certificate | [crt.sh](https://crt.sh) Certificate Transparency logs |
| 2 | Registration status of non-resolving domains | [rdap.org](https://rdap.org) (official RDAP bootstrap) |
| 2b | Does a resolving domain actually serve a website? | HTTPS/HTTP probe |
| 3 | Exact-match web presence (only for names not already TAKEN) | DuckDuckGo |

Evidence is combined into a weighted risk score:

- **TAKEN** — score ≥ 50, or the base name has a **live website on .com** (hard rule)
- **RISKY** — score ≥ 15
- **CLEAN** — everything below

## Install

Requires Python 3.11+.

```bash
git clone https://github.com/yash22nayak/catch-domain.git
cd catch-domain
python -m pip install -r requirements.txt
```

## Usage

1. Put your candidate names in a text file, one per line (`#` starts a comment):

   ```
   # my shortlist
   zetavolve
   flintlogic
   En-Lance        # case/punctuation is normalized -> "enlance"
   ```

2. Run the checker:

   ```bash
   python -m catch_domain names.txt
   ```

3. Read the report — safest names first:

   ```
   NAME        VERDICT  SCORE  EVIDENCE
   zetavolve   CLEAN        2  nothing found
   flintlogic  TAKEN       58  1 domain(s) taken: flintlogic.com
   ```

   Full row-by-row evidence (every domain, lookalike, and search hit) is
   written to `report.csv`, and the run ends with a short checklist of manual
   checks no free API covers (trademarks, social handles).

### Options

| Flag | Effect |
|------|--------|
| `--tlds com,in,io` | Override the TLD list for this run |
| `--no-search` | Skip the DuckDuckGo stage (much faster, DNS/RDAP/crt.sh only) |
| `--refresh` | Ignore the cache and re-check everything |
| `--cache PATH` | Cache file location (default `cache.json`) |
| `--report PATH` | CSV report location (default `report.csv`) |

### Caching and re-runs

Every definitive result is stored in `cache.json`, so running the tool again
only checks what's new (new names, or checks that previously failed).
`unknown` and `pending` results are never cached — they retry automatically on
the next run. DuckDuckGo sometimes throttles; affected names are marked
`search pending` in the report and simply picked up next time.

### Tuning

All knobs live in [`catch_domain/config.py`](catch_domain/config.py): TLD
lists, suffix/prefix variants, scoring weights, verdict thresholds, timeouts,
and politeness delays. Edit that file rather than the logic.

## Interpreting verdicts

- **CLEAN** — no meaningful presence found. Good candidate; still do the
  manual trademark/social checks printed at the end of each run.
- **RISKY** — the name itself may be free, but there are collisions nearby
  (registered variants, lookalike domains, search results). Check the
  `report.csv` evidence before committing.
- **TAKEN** — someone already has a real presence on this name. Move on.

A note on trust: this tool ranks, it doesn't decide. A CLEAN verdict means
"no signal found via free sources", not a legal clearance.

## Development

```bash
python -m pytest        # 49 tests, no network access needed
```

Each pipeline stage is one module (`dns_check`, `rdap_check`, `liveness`,
`ct_check`, `search_check`) returning plain string tokens; `pipeline.py`
composes them, `scoring.py` turns evidence into a verdict, and `report.py`
renders the output. Design and implementation plan live in
[`docs/superpowers/`](docs/superpowers/).
