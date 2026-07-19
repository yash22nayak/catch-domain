"""Tunable settings for catch-domain. Edit lists/weights here, not in logic."""

TLDS = ["com", "in", "io", "tech", "dev", "agency"]
PRIMARY_TLDS = ["com", "in"]

SUFFIXES = ["it", "hq", "app", "tech", "labs", "io", "agency", "ly"]
PREFIXES = ["get", "my", "the"]

SEARCH_VARIANT_COUNT = 2   # how many suffix variants get their own DDG query
MIN_CT_NAME_LEN = 5        # skip crt.sh wildcard search for shorter names

DOMAIN_WORKERS = 12        # concurrent domain probes per name

# TLDs missing from IANA's RDAP bootstrap file, which would otherwise fall back
# to the rdap.org proxy and get rate-limited (HTTP 429) under concurrency.
RDAP_OVERRIDES = {
    "io": "https://rdap.identitydigital.services/rdap",
}
RDAP_RETRIES = 1           # extra attempts when a registry answers 429
RDAP_BACKOFF = 1.0         # seconds to wait before a retry

DNS_TIMEOUT = 5.0
HTTP_TIMEOUT = 8.0
CT_TIMEOUT = 20.0
RDAP_DELAY = 0.0           # extra pause per RDAP request; DOMAIN_WORKERS caps the rate
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
