# catch-domain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Python CLI that reads candidate brand names from a text file, checks each (and its lookalikes) against free internet signals, and prints a ranked CLEAN/RISKY/TAKEN report.

**Architecture:** A staged funnel per name — variant expansion → DNS → liveness → RDAP → crt.sh wildcard lookalike discovery → DuckDuckGo exact search (survivors only) — with every result cached in a JSON file. Each stage is one module returning plain string tokens; a pipeline module composes them into `NameResult` records; scoring converts records to a score + verdict; report renders console table + CSV. (Note: `models.py` and `pipeline.py` are added beyond the spec's file list — dataclasses and orchestration need homes; everything else matches the spec.)

**Tech Stack:** Python 3.11+, `dnspython`, `requests`, `ddgs`, `pytest`.

**Spec:** `docs/superpowers/specs/2026-07-19-catch-domain-design.md`

## Global Constraints

- Dependencies limited to: `dnspython>=2.4`, `requests>=2.31`, `ddgs>=9.0`, `pytest>=8.0`. No others.
- Tests NEVER touch the network — monkeypatch every DNS/HTTP/ddgs call.
- Run all test commands from the repo root as `python -m pytest ...` (this puts the repo root on `sys.path` so `catch_domain` imports work).
- Exact result tokens (used across modules — do not invent variants):
  - domain status: `"live"`, `"registered"`, `"unregistered"`, `"unknown"`
  - DNS: `"resolves"`, `"no_resolve"`, `"unknown"`
  - CT status: `"done"`, `"skipped_short"`, `"unknown"`
  - search status: `"done"`, `"pending"`, `"skipped"`
  - verdicts: `"CLEAN"`, `"RISKY"`, `"TAKEN"`
- Never cache `"unknown"` or `"pending"` results (they must retry next run).
- Default TLDs `com, in, io, tech, dev, agency`; primary TLDs `com, in`; scoring weights exactly as in the spec's table.
- Commit after each green test cycle. Commit messages end with:
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: Scaffolding, config, and variant expansion (Stage 0)

**Files:**
- Create: `requirements.txt`, `.gitignore`, `catch_domain/__init__.py`, `catch_domain/config.py`, `catch_domain/variants.py`
- Test: `tests/test_variants.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `config` constants (`TLDS`, `PRIMARY_TLDS`, `SUFFIXES`, `PREFIXES`, `SEARCH_VARIANT_COUNT`, `MIN_CT_NAME_LEN`, `DNS_TIMEOUT`, `HTTP_TIMEOUT`, `CT_TIMEOUT`, `RDAP_DELAY`, `SEARCH_DELAY`, `USER_AGENT`, `WEIGHTS` dict, `VERDICT_TAKEN_AT`, `VERDICT_RISKY_AT`); `variants.normalize(raw: str) -> str`; `variants.expand(name: str) -> list[str]` (base name first, deduped).

- [ ] **Step 1: Create scaffolding files**

`requirements.txt`:
```
dnspython>=2.4
requests>=2.31
ddgs>=9.0
pytest>=8.0
```

`.gitignore`:
```
__pycache__/
*.pyc
cache.json
report.csv
.venv/
```

`catch_domain/__init__.py`: empty file.

`catch_domain/config.py`:
```python
"""Tunable settings for catch-domain. Edit lists/weights here, not in logic."""

TLDS = ["com", "in", "io", "tech", "dev", "agency"]
PRIMARY_TLDS = ["com", "in"]

SUFFIXES = ["it", "hq", "app", "tech", "labs", "io", "agency", "ly"]
PREFIXES = ["get", "my", "the"]

SEARCH_VARIANT_COUNT = 2   # how many suffix variants get their own DDG query
MIN_CT_NAME_LEN = 5        # skip crt.sh wildcard search for shorter names

DNS_TIMEOUT = 5.0
HTTP_TIMEOUT = 8.0
CT_TIMEOUT = 30.0
RDAP_DELAY = 0.5           # seconds between RDAP requests
SEARCH_DELAY = 3.0         # seconds between DDG queries

USER_AGENT = "catch-domain/0.1 (personal brand-name research tool)"

WEIGHTS = {
    "base_live_primary": 50,
    "base_registered_primary": 25,
    "base_live_other": 15,
    "base_registered_other": 8,
    "variant_live": 10,
    "variant_registered_com": 6,
    "variant_registered_other": 3,
    "ct_lookalike": 3,
    "ct_cap": 15,
    "search_hit_base": 5,
    "search_cap_base": 30,
    "search_hit_variant": 2,
    "search_cap_variant": 10,
    "unknown": 2,
}
VERDICT_TAKEN_AT = 50
VERDICT_RISKY_AT = 15
```

Then install dependencies: `python -m pip install -r requirements.txt`

- [ ] **Step 2: Write the failing test**

`tests/test_variants.py`:
```python
from catch_domain.variants import expand, normalize


def test_normalize_strips_case_spaces_punctuation():
    assert normalize("  En-Lance IT ") == "enlanceit"


def test_normalize_empty_and_junk_lines():
    assert normalize("   ") == ""
    assert normalize("###") == ""


def test_expand_starts_with_base(monkeypatch):
    variants = expand("enlance")
    assert variants[0] == "enlance"


def test_expand_adds_suffixes_and_prefixes():
    variants = expand("enlance")
    assert "enlanceit" in variants
    assert "enlancehq" in variants
    assert "getenlance" in variants
    assert "myenlance" in variants


def test_expand_has_no_duplicates():
    variants = expand("enlance")
    assert len(variants) == len(set(variants))
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_variants.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'catch_domain.variants'`

- [ ] **Step 4: Write minimal implementation**

`catch_domain/variants.py`:
```python
"""Name normalization and lookalike-variant expansion (Stage 0)."""
import re

from catch_domain import config


def normalize(raw: str) -> str:
    """Lowercase and strip everything except ASCII letters and digits."""
    return re.sub(r"[^a-z0-9]", "", raw.strip().lower())


def expand(name: str) -> list[str]:
    """Return the base name followed by its collision variants, deduped."""
    candidates = [name]
    candidates += [name + s for s in config.SUFFIXES]
    candidates += [p + name for p in config.PREFIXES]
    return list(dict.fromkeys(candidates))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_variants.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .gitignore catch_domain tests
git commit -m "feat: scaffolding, config, and variant expansion"
```

---

### Task 2: JSON disk cache

**Files:**
- Create: `catch_domain/cache.py`
- Test: `tests/test_cache.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `class Cache` with `__init__(self, path: Path, refresh: bool = False)`, `get(self, key: str) -> Any | None`, `set(self, key: str, value: Any) -> None`, `save(self) -> None`. Values must be JSON-serializable. Keys follow `"<check_type>:<target>"` (e.g. `"domain:enlance.com"`, `"ct:enlance"`, `"search:enlanceit"`).

- [ ] **Step 1: Write the failing test**

`tests/test_cache.py`:
```python
from catch_domain.cache import Cache


def test_roundtrip_via_disk(tmp_path):
    path = tmp_path / "cache.json"
    c1 = Cache(path)
    c1.set("domain:enlance.com", "live")
    c1.save()
    c2 = Cache(path)
    assert c2.get("domain:enlance.com") == "live"


def test_missing_key_returns_none(tmp_path):
    c = Cache(tmp_path / "cache.json")
    assert c.get("domain:nope.com") is None


def test_refresh_ignores_existing_file(tmp_path):
    path = tmp_path / "cache.json"
    c1 = Cache(path)
    c1.set("domain:enlance.com", "live")
    c1.save()
    c2 = Cache(path, refresh=True)
    assert c2.get("domain:enlance.com") is None


def test_stores_json_values(tmp_path):
    path = tmp_path / "cache.json"
    c1 = Cache(path)
    c1.set("ct:enlance", {"domains": ["enlanceit.com"], "status": "done"})
    c1.save()
    c2 = Cache(path)
    assert c2.get("ct:enlance") == {"domains": ["enlanceit.com"], "status": "done"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cache.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'catch_domain.cache'`

- [ ] **Step 3: Write minimal implementation**

`catch_domain/cache.py`:
```python
"""JSON-file cache so reruns only perform checks that are new."""
import json
import time
from pathlib import Path
from typing import Any


class Cache:
    """Keyed '<check_type>:<target>'; each entry stores the value and a timestamp."""

    def __init__(self, path: Path, refresh: bool = False):
        self.path = Path(path)
        self._data: dict[str, dict] = {}
        if not refresh and self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        return entry["value"] if entry else None

    def set(self, key: str, value: Any) -> None:
        self._data[key] = {"value": value, "ts": time.time()}

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=1), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cache.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add catch_domain/cache.py tests/test_cache.py
git commit -m "feat: JSON disk cache"
```

---

### Task 3: DNS resolution check (Stage 1)

**Files:**
- Create: `catch_domain/dns_check.py`
- Test: `tests/test_dns_check.py`

**Interfaces:**
- Consumes: `config.DNS_TIMEOUT`.
- Produces: `dns_check.resolve_status(domain: str) -> str` returning `"resolves"`, `"no_resolve"`, or `"unknown"`.

- [ ] **Step 1: Write the failing test**

`tests/test_dns_check.py`:
```python
import dns.resolver

from catch_domain import dns_check


def test_resolving_domain(monkeypatch):
    monkeypatch.setattr(dns.resolver, "resolve", lambda *a, **k: ["93.184.216.34"])
    assert dns_check.resolve_status("example.com") == "resolves"


def test_nxdomain_means_no_resolve(monkeypatch):
    def raise_nx(*a, **k):
        raise dns.resolver.NXDOMAIN
    monkeypatch.setattr(dns.resolver, "resolve", raise_nx)
    assert dns_check.resolve_status("no-such-name-xyz.com") == "no_resolve"


def test_no_answer_falls_back_to_ns(monkeypatch):
    calls = []

    def fake_resolve(domain, rtype, lifetime=None):
        calls.append(rtype)
        if rtype == "A":
            raise dns.resolver.NoAnswer
        return ["ns1.example.com"]

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)
    assert dns_check.resolve_status("nsonly.com") == "resolves"
    assert calls == ["A", "NS"]


def test_timeout_is_unknown(monkeypatch):
    def raise_timeout(*a, **k):
        raise dns.resolver.LifetimeTimeout
    monkeypatch.setattr(dns.resolver, "resolve", raise_timeout)
    assert dns_check.resolve_status("slow.com") == "unknown"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dns_check.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'catch_domain.dns_check'`

- [ ] **Step 3: Write minimal implementation**

`catch_domain/dns_check.py`:
```python
"""Stage 1: DNS resolution check (free, unlimited)."""
import dns.exception
import dns.resolver

from catch_domain import config


def resolve_status(domain: str) -> str:
    """'resolves' if A or NS records exist, 'no_resolve' if NXDOMAIN, else 'unknown'."""
    saw_error = False
    for rtype in ("A", "NS"):
        try:
            dns.resolver.resolve(domain, rtype, lifetime=config.DNS_TIMEOUT)
            return "resolves"
        except dns.resolver.NXDOMAIN:
            return "no_resolve"
        except dns.resolver.NoAnswer:
            continue
        except dns.exception.DNSException:
            saw_error = True
    return "unknown" if saw_error else "no_resolve"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dns_check.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add catch_domain/dns_check.py tests/test_dns_check.py
git commit -m "feat: DNS resolution check"
```

---

### Task 4: RDAP registration check (Stage 2)

**Files:**
- Create: `catch_domain/rdap_check.py`
- Test: `tests/test_rdap_check.py`

**Interfaces:**
- Consumes: `config.HTTP_TIMEOUT`, `config.USER_AGENT`.
- Produces: `rdap_check.registration_status(domain: str) -> str` returning `"registered"`, `"unregistered"`, or `"unknown"`.

- [ ] **Step 1: Write the failing test**

`tests/test_rdap_check.py`:
```python
import requests

from catch_domain import rdap_check


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_200_means_registered(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(200))
    assert rdap_check.registration_status("enlance.com") == "registered"


def test_404_means_unregistered(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(404))
    assert rdap_check.registration_status("zetavolve.com") == "unregistered"


def test_other_status_is_unknown(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(503))
    assert rdap_check.registration_status("enlance.com") == "unknown"


def test_network_error_is_unknown(monkeypatch):
    def raise_err(*a, **k):
        raise requests.ConnectionError()
    monkeypatch.setattr(requests, "get", raise_err)
    assert rdap_check.registration_status("enlance.com") == "unknown"


def test_queries_rdap_org_bootstrap(monkeypatch):
    seen = {}

    def fake_get(url, **kwargs):
        seen["url"] = url
        return FakeResponse(404)

    monkeypatch.setattr(requests, "get", fake_get)
    rdap_check.registration_status("enlance.com")
    assert seen["url"] == "https://rdap.org/domain/enlance.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rdap_check.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'catch_domain.rdap_check'`

- [ ] **Step 3: Write minimal implementation**

`catch_domain/rdap_check.py`:
```python
"""Stage 2: registration check via the rdap.org bootstrap (official, no key)."""
import requests

from catch_domain import config


def registration_status(domain: str) -> str:
    """HTTP 200 -> 'registered', 404 -> 'unregistered', anything else -> 'unknown'."""
    try:
        resp = requests.get(
            f"https://rdap.org/domain/{domain}",
            timeout=config.HTTP_TIMEOUT,
            headers={"User-Agent": config.USER_AGENT},
            allow_redirects=True,
        )
    except requests.RequestException:
        return "unknown"
    if resp.status_code == 200:
        return "registered"
    if resp.status_code == 404:
        return "unregistered"
    return "unknown"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_rdap_check.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add catch_domain/rdap_check.py tests/test_rdap_check.py
git commit -m "feat: RDAP registration check"
```

---

### Task 5: Liveness probe (Stage 2b)

**Files:**
- Create: `catch_domain/liveness.py`
- Test: `tests/test_liveness.py`

**Interfaces:**
- Consumes: `config.HTTP_TIMEOUT`, `config.USER_AGENT`.
- Produces: `liveness.liveness(domain: str) -> str` returning `"live"` or `"not_live"`.

- [ ] **Step 1: Write the failing test**

`tests/test_liveness.py`:
```python
import requests

from catch_domain import liveness


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    def close(self):
        pass


def test_2xx_is_live(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(200))
    assert liveness.liveness("enlance.com") == "live"


def test_https_fails_but_http_works(monkeypatch):
    def fake_get(url, **kwargs):
        if url.startswith("https"):
            raise requests.SSLError()
        return FakeResponse(200)

    monkeypatch.setattr(requests, "get", fake_get)
    assert liveness.liveness("enlance.com") == "live"


def test_error_status_is_not_live(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(500))
    assert liveness.liveness("enlance.com") == "not_live"


def test_all_connections_fail_is_not_live(monkeypatch):
    def raise_err(*a, **k):
        raise requests.ConnectionError()
    monkeypatch.setattr(requests, "get", raise_err)
    assert liveness.liveness("enlance.com") == "not_live"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_liveness.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'catch_domain.liveness'`

- [ ] **Step 3: Write minimal implementation**

`catch_domain/liveness.py`:
```python
"""Stage 2b: does a resolving domain actually serve a website?"""
import requests

from catch_domain import config


def liveness(domain: str) -> str:
    """'live' if https:// or http:// answers with a non-error status, else 'not_live'."""
    for scheme in ("https", "http"):
        try:
            resp = requests.get(
                f"{scheme}://{domain}",
                timeout=config.HTTP_TIMEOUT,
                headers={"User-Agent": config.USER_AGENT},
                allow_redirects=True,
                stream=True,
            )
            resp.close()
            if resp.status_code < 400:
                return "live"
        except requests.RequestException:
            continue
    return "not_live"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_liveness.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add catch_domain/liveness.py tests/test_liveness.py
git commit -m "feat: website liveness probe"
```

---

### Task 6: Certificate Transparency lookalike discovery (Stage 1.5)

**Files:**
- Create: `catch_domain/ct_check.py`
- Test: `tests/test_ct_check.py`

**Interfaces:**
- Consumes: `config.MIN_CT_NAME_LEN`, `config.CT_TIMEOUT`, `config.USER_AGENT`, `config.TLDS`.
- Produces: `ct_check.lookalikes(name: str) -> tuple[list[str], str]` — (sorted distinct registrable lookalike domains, status `"done"`/`"skipped_short"`/`"unknown"`). Excludes exact `<name>.<tld>` matches for the configured TLDs (those are covered by Stages 1–2).

- [ ] **Step 1: Write the failing test**

`tests/test_ct_check.py`:
```python
import requests

from catch_domain import ct_check


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


CT_PAYLOAD = [
    {"name_value": "*.enlanceit.com\nenlanceit.com"},
    {"name_value": "www.techenlance.in"},
    {"name_value": "enlance.com"},          # exact match -> excluded
    {"name_value": "unrelated.org"},        # no substring -> excluded
]


def test_finds_and_dedupes_lookalikes(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(200, CT_PAYLOAD))
    domains, status = ct_check.lookalikes("enlance")
    assert status == "done"
    assert domains == ["enlanceit.com", "techenlance.in"]


def test_short_names_are_skipped(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network must not be called for short names")
    monkeypatch.setattr(requests, "get", boom)
    domains, status = ct_check.lookalikes("zap")
    assert domains == []
    assert status == "skipped_short"


def test_failure_after_retry_is_unknown(monkeypatch):
    calls = []

    def raise_err(*a, **k):
        calls.append(1)
        raise requests.Timeout()

    monkeypatch.setattr(requests, "get", raise_err)
    domains, status = ct_check.lookalikes("enlance")
    assert (domains, status) == ([], "unknown")
    assert len(calls) == 2  # one retry


def test_uses_wildcard_query(monkeypatch):
    seen = {}

    def fake_get(url, **kwargs):
        seen["url"] = url
        return FakeResponse(200, [])

    monkeypatch.setattr(requests, "get", fake_get)
    ct_check.lookalikes("enlance")
    assert seen["url"] == "https://crt.sh/?q=%25enlance%25&output=json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ct_check.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'catch_domain.ct_check'`

- [ ] **Step 3: Write minimal implementation**

`catch_domain/ct_check.py`:
```python
"""Stage 1.5: lookalike discovery via Certificate Transparency logs (crt.sh).

crt.sh supports SQL-LIKE '%' wildcards, so one query finds real existing
lookalike domains instead of only guessed variants. CT only sees domains
that ever had an HTTPS cert, so Stages 1-2 still cover cert-less domains.
"""
import requests

from catch_domain import config


def lookalikes(name: str) -> tuple[list[str], str]:
    """Return (sorted distinct registrable lookalike domains, status)."""
    if len(name) < config.MIN_CT_NAME_LEN:
        return [], "skipped_short"

    url = f"https://crt.sh/?q=%25{name}%25&output=json"
    entries = None
    for _ in range(2):  # one retry; crt.sh is free and often slow
        try:
            resp = requests.get(url, timeout=config.CT_TIMEOUT,
                                headers={"User-Agent": config.USER_AGENT})
            if resp.status_code == 200:
                entries = resp.json()
                break
        except (requests.RequestException, ValueError):
            continue
    if entries is None:
        return [], "unknown"

    exact = {f"{name}.{tld}" for tld in config.TLDS}
    found: set[str] = set()
    for entry in entries:
        for host in entry.get("name_value", "").split("\n"):
            host = host.strip().lower().lstrip("*.")
            if name not in host:
                continue
            registrable = ".".join(host.split(".")[-2:])
            if name in registrable and registrable not in exact:
                found.add(registrable)
    return sorted(found), "done"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ct_check.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add catch_domain/ct_check.py tests/test_ct_check.py
git commit -m "feat: crt.sh wildcard lookalike discovery"
```

---

### Task 7: DuckDuckGo web presence check (Stage 3)

**Files:**
- Create: `catch_domain/search_check.py`
- Test: `tests/test_search_check.py`

**Interfaces:**
- Consumes: nothing from other modules (ddgs library only).
- Produces: `search_check.search_presence(name: str) -> tuple[list[dict], str]` — (hits, status). Each hit is `{"title": str, "url": str}` where the name token appears in the lowercased title or URL. Status: `"done"` or `"pending"` (throttled/errored).

- [ ] **Step 1: Write the failing test**

`tests/test_search_check.py`:
```python
from catch_domain import search_check


class FakeDDGS:
    results = []
    raise_error = False

    def text(self, query, max_results=10):
        if FakeDDGS.raise_error:
            raise RuntimeError("ratelimit")
        return FakeDDGS.results


def setup_function():
    FakeDDGS.results = []
    FakeDDGS.raise_error = False


def test_matching_hits_are_returned(monkeypatch):
    FakeDDGS.results = [
        {"title": "Enlanceit - IT Services", "href": "https://enlanceit.com"},
        {"title": "Unrelated page", "href": "https://other.org"},
    ]
    monkeypatch.setattr(search_check, "DDGS", FakeDDGS)
    hits, status = search_check.search_presence("enlanceit")
    assert status == "done"
    assert hits == [{"title": "Enlanceit - IT Services", "url": "https://enlanceit.com"}]


def test_no_results_is_done_with_empty_hits(monkeypatch):
    monkeypatch.setattr(search_check, "DDGS", FakeDDGS)
    assert search_check.search_presence("zetavolve") == ([], "done")


def test_error_means_pending(monkeypatch):
    FakeDDGS.raise_error = True
    monkeypatch.setattr(search_check, "DDGS", FakeDDGS)
    assert search_check.search_presence("enlance") == ([], "pending")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_search_check.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'catch_domain.search_check'`

- [ ] **Step 3: Write minimal implementation**

`catch_domain/search_check.py`:
```python
"""Stage 3: exact-match web presence via DuckDuckGo (ddgs, unofficial)."""
from ddgs import DDGS


def search_presence(name: str) -> tuple[list[dict], str]:
    """Search DuckDuckGo for '"<name>"'; keep hits mentioning the name.

    ddgs raises library-specific errors on throttling; any failure means
    'pending' (retry on a later run) rather than crashing the pipeline.
    """
    try:
        raw = DDGS().text(f'"{name}"', max_results=10)
    except Exception:
        return [], "pending"
    hits = []
    for item in raw or []:
        title = item.get("title", "")
        url = item.get("href", "")
        if name in title.lower() or name in url.lower():
            hits.append({"title": title, "url": url})
    return hits, "done"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_search_check.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add catch_domain/search_check.py tests/test_search_check.py
git commit -m "feat: DuckDuckGo web presence check"
```

---

### Task 8: Result models, scoring, and verdicts

**Files:**
- Create: `catch_domain/models.py`, `catch_domain/scoring.py`
- Test: `tests/test_scoring.py`

**Interfaces:**
- Consumes: `config.WEIGHTS`, `config.PRIMARY_TLDS`, `config.VERDICT_TAKEN_AT`, `config.VERDICT_RISKY_AT`.
- Produces:
  - `models.DomainStatus(domain: str, tld: str, is_base: bool, status: str)` — frozen dataclass; status is a domain-status token.
  - `models.NameResult(name, domains: list[DomainStatus], lookalikes: list[str], ct_status: str, search_hits: list[dict], search_status: str, score: int, verdict: str)` — dataclass with defaults (empty lists, `ct_status="done"`, `search_status="skipped"`, `score=0`, `verdict=""`). Each search hit dict: `{"title", "url", "is_base": bool}`.
  - `scoring.score_name(result: NameResult) -> tuple[int, str]` — pure function; does not mutate.

- [ ] **Step 1: Write models**

`catch_domain/models.py`:
```python
"""Shared result records passed between pipeline stages."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DomainStatus:
    domain: str    # e.g. "enlanceit.com"
    tld: str       # e.g. "com"
    is_base: bool  # True for the base name, False for a generated variant
    status: str    # "live" | "registered" | "unregistered" | "unknown"


@dataclass
class NameResult:
    name: str
    domains: list[DomainStatus] = field(default_factory=list)
    lookalikes: list[str] = field(default_factory=list)
    ct_status: str = "done"           # "done" | "skipped_short" | "unknown"
    search_hits: list[dict] = field(default_factory=list)  # {"title","url","is_base"}
    search_status: str = "skipped"    # "done" | "pending" | "skipped"
    score: int = 0
    verdict: str = ""                 # "CLEAN" | "RISKY" | "TAKEN"
```

- [ ] **Step 2: Write the failing test**

`tests/test_scoring.py`:
```python
from catch_domain.models import DomainStatus, NameResult
from catch_domain.scoring import score_name


def d(domain, tld, is_base, status):
    return DomainStatus(domain=domain, tld=tld, is_base=is_base, status=status)


def test_nothing_found_is_clean():
    result = NameResult(name="zetavolve",
                        domains=[d("zetavolve.com", "com", True, "unregistered")])
    assert score_name(result) == (0, "CLEAN")


def test_live_base_com_is_hard_taken():
    result = NameResult(name="enlance",
                        domains=[d("enlance.com", "com", True, "live")])
    score, verdict = score_name(result)
    assert score == 50
    assert verdict == "TAKEN"


def test_mixed_signals_are_risky():
    # base registered on .io (8) + variant registered on .com (6) + 1 lookalike (3) = 17
    result = NameResult(
        name="flintlogic",
        domains=[
            d("flintlogic.io", "io", True, "registered"),
            d("flintlogicit.com", "com", False, "registered"),
        ],
        lookalikes=["flintlogics.com"],
    )
    assert score_name(result) == (17, "RISKY")


def test_lookalike_score_is_capped():
    result = NameResult(name="enlance",
                        lookalikes=[f"enlance{i}.com" for i in range(10)])
    score, verdict = score_name(result)
    assert score == 15  # 10 * 3 capped at 15
    assert verdict == "RISKY"


def test_search_hits_scored_by_base_vs_variant_with_caps():
    result = NameResult(
        name="enlance",
        search_hits=(
            [{"title": "t", "url": "u", "is_base": True} for _ in range(10)]
            + [{"title": "t", "url": "u", "is_base": False} for _ in range(10)]
        ),
    )
    score, verdict = score_name(result)
    assert score == 40  # base capped at 30 + variant capped at 10
    assert verdict == "RISKY"


def test_unknown_checks_add_caution_points():
    result = NameResult(
        name="enlance",
        domains=[d("enlance.com", "com", True, "unknown")],
        ct_status="unknown",
    )
    assert score_name(result) == (4, "CLEAN")


def test_score_at_taken_threshold_is_taken():
    # base registered .com (25) + base registered .in (25) = 50
    result = NameResult(
        name="enlance",
        domains=[
            d("enlance.com", "com", True, "registered"),
            d("enlance.in", "in", True, "registered"),
        ],
    )
    assert score_name(result) == (50, "TAKEN")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'catch_domain.scoring'`

- [ ] **Step 4: Write minimal implementation**

`catch_domain/scoring.py`:
```python
"""Risk score and verdict from collected evidence. Ranking, not binary rejection."""
from catch_domain import config
from catch_domain.models import DomainStatus, NameResult

W = config.WEIGHTS


def _domain_points(d: DomainStatus) -> int:
    if d.status == "unknown":
        return W["unknown"]
    if d.status == "unregistered":
        return 0
    primary = d.tld in config.PRIMARY_TLDS
    if d.is_base:
        if d.status == "live":
            return W["base_live_primary"] if primary else W["base_live_other"]
        return W["base_registered_primary"] if primary else W["base_registered_other"]
    if d.status == "live":
        return W["variant_live"]
    return W["variant_registered_com"] if d.tld == "com" else W["variant_registered_other"]


def score_name(result: NameResult) -> tuple[int, str]:
    score = sum(_domain_points(d) for d in result.domains)
    score += min(len(result.lookalikes) * W["ct_lookalike"], W["ct_cap"])
    if result.ct_status == "unknown":
        score += W["unknown"]
    base_hits = sum(1 for h in result.search_hits if h.get("is_base"))
    variant_hits = len(result.search_hits) - base_hits
    score += min(base_hits * W["search_hit_base"], W["search_cap_base"])
    score += min(variant_hits * W["search_hit_variant"], W["search_cap_variant"])

    live_base_com = any(
        d.is_base and d.tld == "com" and d.status == "live" for d in result.domains
    )
    if live_base_com or score >= config.VERDICT_TAKEN_AT:
        verdict = "TAKEN"
    elif score >= config.VERDICT_RISKY_AT:
        verdict = "RISKY"
    else:
        verdict = "CLEAN"
    return score, verdict
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_scoring.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add catch_domain/models.py catch_domain/scoring.py tests/test_scoring.py
git commit -m "feat: result models, risk scoring, and verdicts"
```

---

### Task 9: Report — console table, CSV, manual checklist

**Files:**
- Create: `catch_domain/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `models.NameResult`, `models.DomainStatus`.
- Produces: `report.console_table(results: list[NameResult]) -> str` (sorted safest-first); `report.write_csv(results: list[NameResult], path: Path) -> None`; `report.MANUAL_CHECKLIST` (str constant).

- [ ] **Step 1: Write the failing test**

`tests/test_report.py`:
```python
import csv

from catch_domain import report
from catch_domain.models import DomainStatus, NameResult


def make_results():
    clean = NameResult(name="zetavolve", score=0, verdict="CLEAN",
                       domains=[DomainStatus("zetavolve.com", "com", True, "unregistered")])
    taken = NameResult(
        name="enlance", score=53, verdict="TAKEN",
        domains=[DomainStatus("enlance.com", "com", True, "live")],
        lookalikes=["enlanceit.com"],
        search_hits=[{"title": "Enlance", "url": "https://enlance.com", "is_base": True}],
        search_status="done",
    )
    pending = NameResult(name="flintlogic", score=8, verdict="CLEAN",
                         search_status="pending")
    return [taken, clean, pending]


def test_console_table_sorted_safest_first():
    table = report.console_table(make_results())
    lines = table.splitlines()
    assert "NAME" in lines[0] and "VERDICT" in lines[0]
    assert lines[1].startswith("zetavolve")
    assert lines[3].startswith("enlance")


def test_console_table_flags_pending_search():
    table = report.console_table(make_results())
    flintlogic_line = [l for l in table.splitlines() if l.startswith("flintlogic")][0]
    assert "search pending" in flintlogic_line


def test_csv_contains_evidence_rows(tmp_path):
    path = tmp_path / "report.csv"
    report.write_csv(make_results(), path)
    rows = list(csv.reader(path.open(encoding="utf-8")))
    assert rows[0] == ["name", "verdict", "score", "check", "target", "result", "detail"]
    enlance_rows = [r for r in rows if r[0] == "enlance"]
    checks = {r[3] for r in enlance_rows}
    assert checks == {"domain", "ct_lookalike", "search"}


def test_manual_checklist_mentions_trademark_and_socials():
    text = report.MANUAL_CHECKLIST.lower()
    assert "trademark" in text
    assert "github" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'catch_domain.report'`

- [ ] **Step 3: Write minimal implementation**

`catch_domain/report.py`:
```python
"""Output: ranked console table, CSV audit trail, manual next-steps checklist."""
import csv
from pathlib import Path

from catch_domain.models import NameResult

MANUAL_CHECKLIST = """\
Manual final checks for your shortlist (no reliable free API exists for these):
  1. Trademark search:
       IP India:  https://tmrsearch.ipindia.gov.in/tmrpublicsearch/
       USPTO (if targeting the US): https://tmsearch.uspto.gov/
  2. Social handles (open each in a browser):
       github.com/<name>   linkedin.com/company/<name>
       instagram.com/<name>   x.com/<name>
"""


def _summarize(result: NameResult) -> str:
    parts = []
    taken = [d.domain for d in result.domains if d.status in ("live", "registered")]
    if taken:
        parts.append(f"{len(taken)} domain(s) taken: {', '.join(taken[:3])}")
    if result.lookalikes:
        parts.append(f"{len(result.lookalikes)} lookalike(s)")
    if result.search_hits:
        parts.append(f"{len(result.search_hits)} search hit(s)")
    if result.search_status == "pending":
        parts.append("search pending")
    return "; ".join(parts) or "nothing found"


def console_table(results: list[NameResult]) -> str:
    rows = sorted(results, key=lambda r: r.score)
    width = max([len(r.name) for r in rows] + [len("NAME")])
    lines = [f"{'NAME':<{width}}  {'VERDICT':<7}  {'SCORE':>5}  EVIDENCE"]
    for r in rows:
        lines.append(f"{r.name:<{width}}  {r.verdict:<7}  {r.score:>5}  {_summarize(r)}")
    return "\n".join(lines)


def write_csv(results: list[NameResult], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "verdict", "score", "check", "target", "result", "detail"])
        for r in sorted(results, key=lambda x: x.score):
            for d in r.domains:
                writer.writerow([r.name, r.verdict, r.score, "domain", d.domain,
                                 d.status, "base" if d.is_base else "variant"])
            for domain in r.lookalikes:
                writer.writerow([r.name, r.verdict, r.score, "ct_lookalike",
                                 domain, "found", ""])
            for h in r.search_hits:
                writer.writerow([r.name, r.verdict, r.score, "search",
                                 h["url"], "hit", h["title"]])
            if r.search_status != "done":
                writer.writerow([r.name, r.verdict, r.score, "search",
                                 r.name, r.search_status, ""])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_report.py -v`
Expected: 4 passed

Note for the `test_console_table_sorted_safest_first` assertion: sorted by score the order is zetavolve (0), flintlogic (8), enlance (53) — so line 1 is zetavolve and line 3 is enlance.

- [ ] **Step 5: Commit**

```bash
git add catch_domain/report.py tests/test_report.py
git commit -m "feat: console table, CSV report, manual checklist"
```

---

### Task 10: Pipeline orchestration

**Files:**
- Create: `catch_domain/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: everything above — `variants.expand`, `dns_check.resolve_status`, `liveness.liveness`, `rdap_check.registration_status`, `ct_check.lookalikes`, `search_check.search_presence`, `scoring.score_name`, `Cache`, `models`.
- Produces: `pipeline.check_name(name: str, cache: Cache, do_search: bool = True) -> NameResult` (fully scored, verdict set). Cache keys: `"domain:<domain>"` (stores domain-status token), `"ct:<name>"` (stores `{"domains": [...], "status": ...}`), `"search:<query>"` (stores hit list). Never caches `"unknown"`/`"pending"`.

- [ ] **Step 1: Write the failing test**

`tests/test_pipeline.py`:
```python
from catch_domain import config, pipeline
from catch_domain.cache import Cache


def install_fakes(monkeypatch, dns_calls=None):
    """All checks faked: enlance.com live, everything else unregistered."""

    def fake_dns(domain):
        if dns_calls is not None:
            dns_calls.append(domain)
        return "resolves" if domain == "enlance.com" else "no_resolve"

    monkeypatch.setattr(pipeline.dns_check, "resolve_status", fake_dns)
    monkeypatch.setattr(pipeline.liveness, "liveness", lambda domain: "live")
    monkeypatch.setattr(pipeline.rdap_check, "registration_status",
                        lambda domain: "unregistered")
    monkeypatch.setattr(pipeline.ct_check, "lookalikes",
                        lambda name: (["enlanceit.com"], "done"))
    monkeypatch.setattr(pipeline.search_check, "search_presence",
                        lambda name: ([{"title": "T", "url": "https://x.com"}], "done"))
    monkeypatch.setattr(pipeline.time, "sleep", lambda s: None)


def test_taken_name_skips_search(monkeypatch, tmp_path):
    install_fakes(monkeypatch)
    cache = Cache(tmp_path / "cache.json")
    result = pipeline.check_name("enlance", cache, do_search=True)
    assert result.verdict == "TAKEN"          # live base .com -> hard rule
    assert result.search_status == "skipped"  # search never ran
    assert result.lookalikes == ["enlanceit.com"]
    assert len(result.domains) == len(config.TLDS) * (
        1 + len(config.SUFFIXES) + len(config.PREFIXES))


def test_clean_name_gets_searched_with_variants(monkeypatch, tmp_path):
    install_fakes(monkeypatch)
    monkeypatch.setattr(pipeline.dns_check, "resolve_status",
                        lambda domain: "no_resolve")
    monkeypatch.setattr(pipeline.ct_check, "lookalikes", lambda name: ([], "done"))
    queries = []

    def fake_search(name):
        queries.append(name)
        return [], "done"

    monkeypatch.setattr(pipeline.search_check, "search_presence", fake_search)
    cache = Cache(tmp_path / "cache.json")
    result = pipeline.check_name("zetavolve", cache, do_search=True)
    assert result.verdict == "CLEAN"
    assert result.search_status == "done"
    assert queries == ["zetavolve", "zetavolveit", "zetavolvehq"]


def test_domain_results_are_cached(monkeypatch, tmp_path):
    dns_calls = []
    install_fakes(monkeypatch, dns_calls=dns_calls)
    cache = Cache(tmp_path / "cache.json")
    pipeline.check_name("enlance", cache, do_search=False)
    first = len(dns_calls)
    pipeline.check_name("enlance", cache, do_search=False)
    assert len(dns_calls) == first  # second run fully served by cache


def test_unknown_status_is_not_cached(monkeypatch, tmp_path):
    install_fakes(monkeypatch)
    monkeypatch.setattr(pipeline.dns_check, "resolve_status", lambda d: "unknown")
    cache = Cache(tmp_path / "cache.json")
    pipeline.check_name("enlance", cache, do_search=False)
    assert cache.get("domain:enlance.com") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'catch_domain.pipeline'`

- [ ] **Step 3: Write minimal implementation**

`catch_domain/pipeline.py`:
```python
"""Orchestrates all check stages for one candidate name (cheap checks first)."""
import time

from catch_domain import (config, ct_check, dns_check, liveness, rdap_check,
                          scoring, search_check)
from catch_domain.cache import Cache
from catch_domain.models import DomainStatus, NameResult
from catch_domain.variants import expand


def _probe_domain(domain: str) -> str:
    """Combine DNS + liveness + RDAP into one domain-status token."""
    dns_result = dns_check.resolve_status(domain)
    if dns_result == "resolves":
        return "live" if liveness.liveness(domain) == "live" else "registered"
    if dns_result == "unknown":
        return "unknown"
    time.sleep(config.RDAP_DELAY)
    return rdap_check.registration_status(domain)


def _domain_status(cache: Cache, domain: str) -> str:
    cached = cache.get(f"domain:{domain}")
    if cached is not None:
        return cached
    status = _probe_domain(domain)
    if status != "unknown":
        cache.set(f"domain:{domain}", status)
    return status


def _ct_lookalikes(cache: Cache, name: str) -> tuple[list[str], str]:
    cached = cache.get(f"ct:{name}")
    if cached is not None:
        return cached["domains"], cached["status"]
    domains, status = ct_check.lookalikes(name)
    if status != "unknown":
        cache.set(f"ct:{name}", {"domains": domains, "status": status})
    return domains, status


def _search(cache: Cache, query: str) -> tuple[list[dict], str]:
    cached = cache.get(f"search:{query}")
    if cached is not None:
        return cached, "done"
    hits, status = search_check.search_presence(query)
    if status != "pending":
        cache.set(f"search:{query}", hits)
    time.sleep(config.SEARCH_DELAY)
    return hits, status


def check_name(name: str, cache: Cache, do_search: bool = True) -> NameResult:
    result = NameResult(name=name)

    for label in expand(name):
        is_base = label == name
        for tld in config.TLDS:
            domain = f"{label}.{tld}"
            result.domains.append(
                DomainStatus(domain, tld, is_base, _domain_status(cache, domain)))

    result.lookalikes, result.ct_status = _ct_lookalikes(cache, name)

    # Provisional verdict decides whether the expensive search stage runs at all.
    _, provisional = scoring.score_name(result)
    if do_search and provisional != "TAKEN":
        result.search_status = "done"
        queries = [name] + [name + s
                            for s in config.SUFFIXES[:config.SEARCH_VARIANT_COUNT]]
        for query in queries:
            hits, status = _search(cache, query)
            if status == "pending":
                result.search_status = "pending"
            for hit in hits:
                result.search_hits.append({**hit, "is_base": query == name})

    result.score, result.verdict = scoring.score_name(result)
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: 4 passed

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest -v`
Expected: all tests pass (approximately 35)

- [ ] **Step 6: Commit**

```bash
git add catch_domain/pipeline.py tests/test_pipeline.py
git commit -m "feat: pipeline orchestration with caching and search funnel"
```

---

### Task 11: CLI entry point, example input, end-to-end smoke run

**Files:**
- Create: `catch_domain/__main__.py`, `names.txt`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `pipeline.check_name`, `Cache`, `report.*`, `variants.normalize`, `config.TLDS`.
- Produces: `python -m catch_domain <names_file> [--tlds com,in] [--no-search] [--refresh] [--cache PATH] [--report PATH]`; `__main__.read_names(path: Path) -> list[str]`; `__main__.main(argv: list[str] | None = None) -> None`.

- [ ] **Step 1: Write the failing test**

`tests/test_main.py`:
```python
import pytest

from catch_domain import __main__ as cli
from catch_domain.models import NameResult


def test_read_names_normalizes_dedupes_and_skips_comments(tmp_path):
    f = tmp_path / "names.txt"
    f.write_text(
        "# candidates\n"
        "Enlance\n"
        "enlance   # duplicate after normalize\n"
        "\n"
        "Zeta-Volve\n",
        encoding="utf-8",
    )
    assert cli.read_names(f) == ["enlance", "zetavolve"]


def test_read_names_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit):
        cli.read_names(tmp_path / "nope.txt")


def test_read_names_empty_file_exits(tmp_path):
    f = tmp_path / "names.txt"
    f.write_text("# only comments\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        cli.read_names(f)


def test_main_end_to_end_with_faked_pipeline(tmp_path, monkeypatch, capsys):
    f = tmp_path / "names.txt"
    f.write_text("zetavolve\n", encoding="utf-8")

    def fake_check_name(name, cache, do_search=True):
        return NameResult(name=name, score=0, verdict="CLEAN")

    monkeypatch.setattr(cli, "check_name", fake_check_name)
    cli.main([str(f), "--cache", str(tmp_path / "c.json"),
              "--report", str(tmp_path / "r.csv"), "--no-search"])
    out = capsys.readouterr().out
    assert "zetavolve" in out
    assert "CLEAN" in out
    assert (tmp_path / "r.csv").exists()


def test_tlds_flag_overrides_config(tmp_path, monkeypatch):
    from catch_domain import config
    f = tmp_path / "names.txt"
    f.write_text("zetavolve\n", encoding="utf-8")
    monkeypatch.setattr(cli, "check_name",
                        lambda name, cache, do_search=True: NameResult(name=name))
    original = list(config.TLDS)
    try:
        cli.main([str(f), "--tlds", "com,.in", "--cache", str(tmp_path / "c.json"),
                  "--report", str(tmp_path / "r.csv")])
        assert config.TLDS == ["com", "in"]
    finally:
        config.TLDS[:] = original
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL — `AttributeError` / `ImportError` (no `read_names`/`main` in `catch_domain.__main__`)

- [ ] **Step 3: Write minimal implementation**

`catch_domain/__main__.py`:
```python
"""CLI entry point: python -m catch_domain names.txt"""
import argparse
import sys
from pathlib import Path

from catch_domain import config, report
from catch_domain.cache import Cache
from catch_domain.pipeline import check_name
from catch_domain.variants import normalize


def read_names(path: Path) -> list[str]:
    if not path.exists():
        sys.exit(f"error: input file not found: {path}")
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned = normalize(line.split("#", 1)[0])
        if cleaned:
            names.append(cleaned)
    if not names:
        sys.exit(f"error: no names found in {path}")
    return list(dict.fromkeys(names))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="catch_domain",
        description="Filter brand-name candidates by real internet presence.")
    parser.add_argument("names_file", type=Path,
                        help="text file, one candidate name per line, # comments")
    parser.add_argument("--tlds", help="comma-separated TLD list, e.g. com,in,io")
    parser.add_argument("--no-search", action="store_true",
                        help="skip the DuckDuckGo web-presence stage")
    parser.add_argument("--refresh", action="store_true",
                        help="ignore cached results and re-check everything")
    parser.add_argument("--cache", type=Path, default=Path("cache.json"))
    parser.add_argument("--report", type=Path, default=Path("report.csv"))
    args = parser.parse_args(argv)

    if args.tlds:
        config.TLDS[:] = [t.strip().lstrip(".")
                          for t in args.tlds.split(",") if t.strip()]

    names = read_names(args.names_file)
    cache = Cache(args.cache, refresh=args.refresh)
    results = []
    for i, name in enumerate(names, 1):
        print(f"[{i}/{len(names)}] checking {name} ...", flush=True)
        results.append(check_name(name, cache, do_search=not args.no_search))
        cache.save()  # save as we go so an interrupt loses nothing

    print()
    print(report.console_table(results))
    report.write_csv(results, args.report)
    print(f"\nFull evidence written to {args.report}")
    print()
    print(report.MANUAL_CHECKLIST)


if __name__ == "__main__":
    main()
```

`names.txt`:
```
# catch-domain candidate list — one name per line, '#' starts a comment.
# Replace these examples with your own candidates.
zetavolve
flintlogic
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_main.py -v`
Expected: 5 passed

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest -v`
Expected: all tests pass (approximately 40)

- [ ] **Step 6: Real-world smoke run (network, ~1 minute)**

Run: `python -m catch_domain names.txt --no-search`
Expected: progress lines for the 2 example names, then a ranked table with
verdicts and a `report.csv` in the repo root, ending with the manual checklist.
(`--no-search` keeps the smoke run fast and off DuckDuckGo; DNS/RDAP/crt.sh are hit
for real. `unknown` results are acceptable here — the run must not crash.)

- [ ] **Step 7: Commit**

```bash
git add catch_domain/__main__.py names.txt tests/test_main.py
git commit -m "feat: CLI entry point and example input"
```

---

## Self-Review Notes

- Spec coverage: Stage 0 (Task 1), Stage 1 (Task 3), Stage 1.5 (Task 6), Stage 2 (Task 4), Stage 2b (Task 5), Stage 3 + `--no-search` (Tasks 7, 10, 11), scoring table + hard rule + thresholds (Task 8), caching + `--refresh` + never-cache-unknown (Tasks 2, 10), console table + CSV + manual checklist (Task 9), CLI flags + input normalization + empty-file error (Task 11), politeness delays (Task 10 via `config.RDAP_DELAY`/`SEARCH_DELAY`).
- Deviation from spec file list: added `models.py` and `pipeline.py`; orchestration lives in `pipeline.py` rather than `__main__.py` for testability. `Evidence`-style records are represented as `DomainStatus`/hit dicts.
- Type consistency: status tokens are pinned in Global Constraints; `check_name(name, cache, do_search)` signature identical in Tasks 10 and 11; cache keys identical in Tasks 2 and 10.
