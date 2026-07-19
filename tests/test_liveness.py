import requests

from catch_domain import liveness


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    def close(self):
        pass


def test_2xx_is_live(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(200))
    assert liveness.liveness("enlance.com") == "live"


def test_https_fails_but_http_works(monkeypatch):
    def fake_get(url, **kwargs):
        if url.startswith("https"):
            raise requests.exceptions.SSLError()
        return FakeResponse(200)

    monkeypatch.setattr(requests, "get", fake_get)
    assert liveness.liveness("enlance.com") == "live"


def test_error_status_is_not_live(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(500))
    assert liveness.liveness("enlance.com") == "not_live"


def test_all_connections_fail_is_not_live(monkeypatch):
    def raise_err(*a, **k):
        raise requests.ConnectionError()
    monkeypatch.setattr(requests, "get", raise_err)
    assert liveness.liveness("enlance.com") == "not_live"
