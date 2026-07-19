"""Orchestrates all check stages for one candidate name (cheap checks first)."""
import time
from concurrent.futures import ThreadPoolExecutor

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
    if config.RDAP_DELAY:
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

    targets = [(f"{label}.{tld}", tld, label == name)
               for label in expand(name) for tld in config.TLDS]

    # Every probe is a blocking network round trip, so they overlap; crt.sh is
    # independent of them and rides along. pool.map keeps the input order.
    with ThreadPoolExecutor(max_workers=config.DOMAIN_WORKERS) as pool:
        ct_future = pool.submit(_ct_lookalikes, cache, name)
        statuses = list(pool.map(lambda t: _domain_status(cache, t[0]), targets))
        result.lookalikes, result.ct_status = ct_future.result()

    result.domains = [DomainStatus(domain, tld, is_base, status)
                      for (domain, tld, is_base), status in zip(targets, statuses)]

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
