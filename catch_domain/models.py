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
