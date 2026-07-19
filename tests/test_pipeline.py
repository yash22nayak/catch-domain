import threading

from catch_domain import config, pipeline
from catch_domain.cache import Cache


def block(seconds):
    """Sleep that survives install_fakes(), which no-ops the global time.sleep."""
    threading.Event().wait(seconds)


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


def test_domain_probes_run_concurrently(monkeypatch, tmp_path):
    """The 70+ probes per name must overlap, not run one blocking call at a time."""
    install_fakes(monkeypatch)
    lock = threading.Lock()
    state = {"in_flight": 0, "peak": 0}

    def slow_dns(domain):
        with lock:
            state["in_flight"] += 1
            state["peak"] = max(state["peak"], state["in_flight"])
        block(0.05)
        with lock:
            state["in_flight"] -= 1
        return "no_resolve"

    monkeypatch.setattr(pipeline.dns_check, "resolve_status", slow_dns)
    pipeline.check_name("zetavolve", Cache(tmp_path / "cache.json"), do_search=False)
    assert state["peak"] > 1


def test_ct_lookup_overlaps_domain_probes(monkeypatch, tmp_path):
    """crt.sh is slow and independent, so it must not block the domain probes."""
    install_fakes(monkeypatch)
    ct_running = threading.Event()
    saw_overlap = threading.Event()

    def slow_ct(name):
        ct_running.set()
        block(0.2)
        ct_running.clear()
        return [], "done"

    def dns_watching_ct(domain):
        if ct_running.is_set():
            saw_overlap.set()
        block(0.01)
        return "no_resolve"

    monkeypatch.setattr(pipeline.ct_check, "lookalikes", slow_ct)
    monkeypatch.setattr(pipeline.dns_check, "resolve_status", dns_watching_ct)
    pipeline.check_name("zetavolve", Cache(tmp_path / "cache.json"), do_search=False)
    assert saw_overlap.is_set()


def test_domain_order_is_deterministic(monkeypatch, tmp_path):
    """Concurrency must not reorder rows, or the report output churns per run."""
    install_fakes(monkeypatch)
    cache_a, cache_b = Cache(tmp_path / "a.json"), Cache(tmp_path / "b.json")
    first = [d.domain for d in pipeline.check_name("zetavolve", cache_a,
                                                   do_search=False).domains]
    second = [d.domain for d in pipeline.check_name("zetavolve", cache_b,
                                                    do_search=False).domains]
    expected = [f"{label}.{tld}"
                for label in pipeline.expand("zetavolve") for tld in config.TLDS]
    assert first == second == expected


def test_unknown_status_is_not_cached(monkeypatch, tmp_path):
    install_fakes(monkeypatch)
    monkeypatch.setattr(pipeline.dns_check, "resolve_status", lambda d: "unknown")
    cache = Cache(tmp_path / "cache.json")
    pipeline.check_name("enlance", cache, do_search=False)
    assert cache.get("domain:enlance.com") is None
