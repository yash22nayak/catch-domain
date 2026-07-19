import dns.resolver

from catch_domain import dns_check


def test_resolving_domain(monkeypatch):
    monkeypatch.setattr(dns.resolver, "resolve", lambda *a, **k: ["93.184.216.34"])
    assert dns_check.resolve_status("example.com") == "resolves"


def test_nxdomain_means_no_resolve(monkeypatch):
    def raise_nx(*a, **k):
        raise dns.resolver.NXDOMAIN
    monkeypatch.setattr(dns.resolver, "resolve", raise_nx)
    assert dns_check.resolve_status("no-such-name-xyz.com") == "no_resolve"


def test_no_answer_falls_back_to_ns(monkeypatch):
    calls = []

    def fake_resolve(domain, rtype, lifetime=None):
        calls.append(rtype)
        if rtype == "A":
            raise dns.resolver.NoAnswer
        return ["ns1.example.com"]

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)
    assert dns_check.resolve_status("nsonly.com") == "resolves"
    assert calls == ["A", "NS"]


def test_timeout_is_unknown(monkeypatch):
    def raise_timeout(*a, **k):
        raise dns.resolver.LifetimeTimeout
    monkeypatch.setattr(dns.resolver, "resolve", raise_timeout)
    assert dns_check.resolve_status("slow.com") == "unknown"
