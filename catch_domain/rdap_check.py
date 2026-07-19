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
