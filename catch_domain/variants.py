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
