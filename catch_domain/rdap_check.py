"""Stage 2: registration check against each TLD's authoritative RDAP server.

The IANA bootstrap file maps every TLD to its registry's RDAP base URL. Asking
that registry directly is one round trip; the rdap.org proxy adds a redirect
hop and becomes a single point of congestion, so it is only a fallback for
TLDs the bootstrap file does not cover.
"""
import threading
import time

import requests

from catch_domain import config

IANA_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
FALLBACK_BASE = "https://rdap.org"

_endpoints: dict[str, str] | None = None
_endpoints_lock = threading.Lock()
_local = threading.local()


def _session() -> requests.Session:
    """One connection-pooling session per thread (Session is not thread-safe)."""
    session = getattr(_local, "session", None)
    if session is None:
        session = _local.session = requests.Session()
    return session


def _get(url: str, timeout: float | None = None) -> requests.Response:
    return _session().get(
        url,
        timeout=timeout or config.HTTP_TIMEOUT,
        headers={"User-Agent": config.USER_AGENT},
        allow_redirects=True,
    )


def reset_endpoints() -> None:
    """Drop the cached bootstrap table (used by tests)."""
    global _endpoints
    with _endpoints_lock:
        _endpoints = None


def _load_endpoints() -> dict[str, str]:
    """TLD -> registry RDAP base URL, fetched once per process."""
    global _endpoints
    with _endpoints_lock:
        if _endpoints is None:
            mapping: dict[str, str] = {}
            try:
                services = _get(IANA_BOOTSTRAP_URL).json().get("services", [])
                for tlds, urls in services:
                    base = next((u for u in urls if u.startswith("https")), None)
                    if base:
                        for tld in tlds:
                            mapping[tld.lower()] = base.rstrip("/")
            except (requests.RequestException, ValueError, TypeError, KeyError):
                mapping = {}  # every lookup falls back to the proxy
            _endpoints = mapping
        return _endpoints


def _url_for(domain: str) -> str:
    tld = domain.rsplit(".", 1)[-1].lower()
    base = (_load_endpoints().get(tld)
            or config.RDAP_OVERRIDES.get(tld)
            or FALLBACK_BASE)
    return f"{base.rstrip('/')}/domain/{domain}"


def registration_status(domain: str) -> str:
    """HTTP 200 -> 'registered', 404 -> 'unregistered', anything else -> 'unknown'."""
    url = _url_for(domain)
    for attempt in range(config.RDAP_RETRIES + 1):
        try:
            resp = _get(url)
        except requests.RequestException:
            return "unknown"
        if resp.status_code == 200:
            return "registered"
        if resp.status_code == 404:
            return "unregistered"
        if resp.status_code != 429 or attempt == config.RDAP_RETRIES:
            return "unknown"
        time.sleep(config.RDAP_BACKOFF * (attempt + 1))
    return "unknown"
