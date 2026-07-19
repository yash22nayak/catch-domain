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
