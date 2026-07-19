"""Stage 2b: does a resolving domain actually serve a website?"""
import requests

from catch_domain import config


def liveness(domain: str) -> str:
    """'live' if https:// or http:// answers with a non-error status, else 'not_live'."""
    for scheme in ("https", "http"):
        try:
            resp = requests.get(
                f"{scheme}://{domain}",
                timeout=config.HTTP_TIMEOUT,
                headers={"User-Agent": config.USER_AGENT},
                allow_redirects=True,
                stream=True,
            )
            resp.close()
            if resp.status_code < 400:
                return "live"
        except requests.RequestException:
            continue
    return "not_live"
