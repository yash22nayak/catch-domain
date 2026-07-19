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
