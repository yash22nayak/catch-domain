import pytest
import requests

from catch_domain import config, rdap_check


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


BOOTSTRAP = {
    "services": [
        [["com", "net"], ["https://rdap.verisign.com/com/v1/"]],
        [["in"], ["http://rdap.example-insecure.in/", "https://rdap.registry.in/"]],
    ]
}


@pytest.fixture(autouse=True)
def fresh_endpoints():
    """Each test starts with an unresolved bootstrap table."""
    rdap_check.reset_endpoints()
    yield
    rdap_check.reset_endpoints()


def install(monkeypatch, domain_response, bootstrap=BOOTSTRAP):
    """Serve the IANA bootstrap doc, and domain_response for domain queries."""
    seen = []

    def fake_get(url, **kwargs):
        seen.append(url)
        if url == rdap_check.IANA_BOOTSTRAP_URL:
            return FakeResponse(200, bootstrap)
        if callable(domain_response):
            return domain_response(url)
        return domain_response

    monkeypatch.setattr(rdap_check, "_get", fake_get)
    return seen


def test_200_means_registered(monkeypatch):
    install(monkeypatch, FakeResponse(200))
    assert rdap_check.registration_status("enlance.com") == "registered"


def test_404_means_unregistered(monkeypatch):
    install(monkeypatch, FakeResponse(404))
    assert rdap_check.registration_status("zetavolve.com") == "unregistered"


def test_other_status_is_unknown(monkeypatch):
    install(monkeypatch, FakeResponse(503))
    assert rdap_check.registration_status("enlance.com") == "unknown"


def test_network_error_is_unknown(monkeypatch):
    def raise_err(url, **kwargs):
        raise requests.ConnectionError()

    monkeypatch.setattr(rdap_check, "_get", raise_err)
    assert rdap_check.registration_status("enlance.com") == "unknown"


def test_queries_authoritative_registry_not_the_bootstrap_proxy(monkeypatch):
    seen = install(monkeypatch, FakeResponse(404))
    rdap_check.registration_status("enlance.com")
    assert seen[-1] == "https://rdap.verisign.com/com/v1/domain/enlance.com"


def test_prefers_https_endpoint(monkeypatch):
    seen = install(monkeypatch, FakeResponse(404))
    rdap_check.registration_status("enlance.in")
    assert seen[-1] == "https://rdap.registry.in/domain/enlance.in"


def test_bootstrap_is_fetched_once_and_reused(monkeypatch):
    seen = install(monkeypatch, FakeResponse(404))
    for domain in ("a.com", "b.com", "c.com"):
        rdap_check.registration_status(domain)
    assert seen.count(rdap_check.IANA_BOOTSTRAP_URL) == 1


def test_unknown_tld_falls_back_to_rdap_org(monkeypatch):
    seen = install(monkeypatch, FakeResponse(404))
    rdap_check.registration_status("enlance.tech")
    assert seen[-1] == "https://rdap.org/domain/enlance.tech"


def test_configured_override_fills_gaps_in_the_bootstrap(monkeypatch):
    """.io is absent from IANA's file; rdap.org rate-limits, so use the registry."""
    monkeypatch.setitem(config.RDAP_OVERRIDES, "tech", "https://rdap.example.test")
    seen = install(monkeypatch, FakeResponse(404))
    rdap_check.registration_status("enlance.tech")
    assert seen[-1] == "https://rdap.example.test/domain/enlance.tech"


def test_bootstrap_wins_over_override(monkeypatch):
    monkeypatch.setitem(config.RDAP_OVERRIDES, "com", "https://rdap.example.test")
    seen = install(monkeypatch, FakeResponse(404))
    rdap_check.registration_status("enlance.com")
    assert seen[-1] == "https://rdap.verisign.com/com/v1/domain/enlance.com"


def test_rate_limited_request_is_retried(monkeypatch):
    """429 means 'ask again', not 'unknown' - one retry keeps the answer real."""
    calls = []

    def responses(url):
        calls.append(url)
        return FakeResponse(429 if len(calls) == 1 else 404)

    install(monkeypatch, responses)
    monkeypatch.setattr(rdap_check.time, "sleep", lambda s: None)
    assert rdap_check.registration_status("enlance.com") == "unregistered"
    assert len(calls) == 2


def test_persistent_rate_limit_is_unknown(monkeypatch):
    install(monkeypatch, FakeResponse(429))
    monkeypatch.setattr(rdap_check.time, "sleep", lambda s: None)
    assert rdap_check.registration_status("enlance.com") == "unknown"


def test_unreachable_bootstrap_falls_back_to_rdap_org(monkeypatch):
    def fake_get(url, **kwargs):
        if url == rdap_check.IANA_BOOTSTRAP_URL:
            raise requests.ConnectionError()
        return FakeResponse(404)

    monkeypatch.setattr(rdap_check, "_get", fake_get)
    assert rdap_check.registration_status("enlance.com") == "unregistered"
