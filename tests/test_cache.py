from catch_domain.cache import Cache


def test_roundtrip_via_disk(tmp_path):
    path = tmp_path / "cache.json"
    c1 = Cache(path)
    c1.set("domain:enlance.com", "live")
    c1.save()
    c2 = Cache(path)
    assert c2.get("domain:enlance.com") == "live"


def test_missing_key_returns_none(tmp_path):
    c = Cache(tmp_path / "cache.json")
    assert c.get("domain:nope.com") is None


def test_refresh_ignores_existing_file(tmp_path):
    path = tmp_path / "cache.json"
    c1 = Cache(path)
    c1.set("domain:enlance.com", "live")
    c1.save()
    c2 = Cache(path, refresh=True)
    assert c2.get("domain:enlance.com") is None


def test_stores_json_values(tmp_path):
    path = tmp_path / "cache.json"
    c1 = Cache(path)
    c1.set("ct:enlance", {"domains": ["enlanceit.com"], "status": "done"})
    c1.save()
    c2 = Cache(path)
    assert c2.get("ct:enlance") == {"domains": ["enlanceit.com"], "status": "done"}
