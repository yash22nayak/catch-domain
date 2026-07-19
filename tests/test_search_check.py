from catch_domain import search_check


class FakeDDGS:
    results = []
    raise_error = False

    def text(self, query, max_results=10):
        if FakeDDGS.raise_error:
            raise RuntimeError("ratelimit")
        return FakeDDGS.results


def setup_function():
    FakeDDGS.results = []
    FakeDDGS.raise_error = False


def test_matching_hits_are_returned(monkeypatch):
    FakeDDGS.results = [
        {"title": "Enlanceit - IT Services", "href": "https://enlanceit.com"},
        {"title": "Unrelated page", "href": "https://other.org"},
    ]
    monkeypatch.setattr(search_check, "DDGS", FakeDDGS)
    hits, status = search_check.search_presence("enlanceit")
    assert status == "done"
    assert hits == [{"title": "Enlanceit - IT Services", "url": "https://enlanceit.com"}]


def test_no_results_is_done_with_empty_hits(monkeypatch):
    monkeypatch.setattr(search_check, "DDGS", FakeDDGS)
    assert search_check.search_presence("zetavolve") == ([], "done")


def test_error_means_pending(monkeypatch):
    FakeDDGS.raise_error = True
    monkeypatch.setattr(search_check, "DDGS", FakeDDGS)
    assert search_check.search_presence("enlance") == ([], "pending")
