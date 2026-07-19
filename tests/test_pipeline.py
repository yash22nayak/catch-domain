from catch_domain import config, pipeline
from catch_domain.cache import Cache


def install_fakes(monkeypatch, dns_calls=None):
    """All checks faked: enlance.com live, everything else unregistered."""

    def fake_dns(domain):
        if dns_calls is not None:
            dns_calls.append(domain)
        return "resolves" if domain == "enlance.com" else "no_resolve"

    monkeypatch.setattr(pipeline.dns_check, "resolve_status", fake_dns)
    monkeypatch.setattr(pipeline.liveness, "liveness", lambda domain: "live")
    monkeypatch.setattr(pipeline.rdap_check, "registration_status",
                        lambda domain: "unregistered")
    monkeypatch.setattr(pipeline.ct_check, "lookalikes",
                        lambda name: (["enlanceit.com"], "done"))
    monkeypatch.setattr(pipeline.search_check, "search_presence",
                        lambda name: ([{"title": "T", "url": "https://x.com"}], "done"))
    monkeypatch.setattr(pipeline.time, "sleep", lambda s: None)


def test_taken_name_skips_search(monkeypatch, tmp_path):
    install_fakes(monkeypatch)
    cache = Cache(tmp_path / "cache.json")
    result = pipeline.check_name("enlance", cache, do_search=True)
    assert result.verdict == "TAKEN"          # live base .com -> hard rule
    assert result.search_status == "skipped"  # search never ran
    assert result.lookalikes == ["enlanceit.com"]
    assert len(result.domains) == len(config.TLDS) * (
        1 + len(config.SUFFIXES) + len(config.PREFIXES))


def test_clean_name_gets_searched_with_variants(monkeypatch, tmp_path):
    install_fakes(monkeypatch)
    monkeypatch.setattr(pipeline.dns_check, "resolve_status",
                        lambda domain: "no_resolve")
    monkeypatch.setattr(pipeline.ct_check, "lookalikes", lambda name: ([], "done"))
    queries = []

    def fake_search(name):
        queries.append(name)
        return [], "done"

    monkeypatch.setattr(pipeline.search_check, "search_presence", fake_search)
    cache = Cache(tmp_path / "cache.json")
    result = pipeline.check_name("zetavolve", cache, do_search=True)
    assert result.verdict == "CLEAN"
    assert result.search_status == "done"
    assert queries == ["zetavolve", "zetavolveit", "zetavolvehq"]


def test_domain_results_are_cached(monkeypatch, tmp_path):
    dns_calls = []
    install_fakes(monkeypatch, dns_calls=dns_calls)
    cache = Cache(tmp_path / "cache.json")
    pipeline.check_name("enlance", cache, do_search=False)
    first = len(dns_calls)
    pipeline.check_name("enlance", cache, do_search=False)
    assert len(dns_calls) == first  # second run fully served by cache


def test_unknown_status_is_not_cached(monkeypatch, tmp_path):
    install_fakes(monkeypatch)
    monkeypatch.setattr(pipeline.dns_check, "resolve_status", lambda d: "unknown")
    cache = Cache(tmp_path / "cache.json")
    pipeline.check_name("enlance", cache, do_search=False)
    assert cache.get("domain:enlance.com") is None
