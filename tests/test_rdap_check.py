import requests

from catch_domain import rdap_check


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_200_means_registered(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(200))
    assert rdap_check.registration_status("enlance.com") == "registered"


def test_404_means_unregistered(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(404))
    assert rdap_check.registration_status("zetavolve.com") == "unregistered"


def test_other_status_is_unknown(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(503))
    assert rdap_check.registration_status("enlance.com") == "unknown"


def test_network_error_is_unknown(monkeypatch):
    def raise_err(*a, **k):
        raise requests.ConnectionError()
    monkeypatch.setattr(requests, "get", raise_err)
    assert rdap_check.registration_status("enlance.com") == "unknown"


def test_queries_rdap_org_bootstrap(monkeypatch):
    seen = {}

    def fake_get(url, **kwargs):
        seen["url"] = url
        return FakeResponse(404)

    monkeypatch.setattr(requests, "get", fake_get)
    rdap_check.registration_status("enlance.com")
    assert seen["url"] == "https://rdap.org/domain/enlance.com"
