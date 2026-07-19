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
