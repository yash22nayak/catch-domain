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
