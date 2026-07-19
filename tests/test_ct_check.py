import requests

from catch_domain import ct_check


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


CT_PAYLOAD = [
    {"name_value": "*.enlanceit.com\nenlanceit.com"},
    {"name_value": "www.techenlance.in"},
    {"name_value": "enlance.com"},          # exact match -> excluded
    {"name_value": "unrelated.org"},        # no substring -> excluded
]


def test_finds_and_dedupes_lookalikes(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(200, CT_PAYLOAD))
    domains, status = ct_check.lookalikes("enlance")
    assert status == "done"
    assert domains == ["enlanceit.com", "techenlance.in"]


def test_short_names_are_skipped(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network must not be called for short names")
    monkeypatch.setattr(requests, "get", boom)
    domains, status = ct_check.lookalikes("zap")
    assert domains == []
    assert status == "skipped_short"


def test_failure_after_retry_is_unknown(monkeypatch):
    calls = []

    def raise_err(*a, **k):
        calls.append(1)
        raise requests.Timeout()

    monkeypatch.setattr(requests, "get", raise_err)
    domains, status = ct_check.lookalikes("enlance")
    assert (domains, status) == ([], "unknown")
    assert len(calls) == 2  # one retry


def test_uses_wildcard_query(monkeypatch):
    seen = {}

    def fake_get(url, **kwargs):
        seen["url"] = url
        return FakeResponse(200, [])

    monkeypatch.setattr(requests, "get", fake_get)
    ct_check.lookalikes("enlance")
    assert seen["url"] == "https://crt.sh/?q=%25enlance%25&output=json"
