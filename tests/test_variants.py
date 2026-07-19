from catch_domain.variants import expand, normalize


def test_normalize_strips_case_spaces_punctuation():
    assert normalize("  En-Lance IT ") == "enlanceit"


def test_normalize_empty_and_junk_lines():
    assert normalize("   ") == ""
    assert normalize("###") == ""


def test_expand_starts_with_base(monkeypatch):
    variants = expand("enlance")
    assert variants[0] == "enlance"


def test_expand_adds_suffixes_and_prefixes():
    variants = expand("enlance")
    assert "enlanceit" in variants
    assert "enlancehq" in variants
    assert "getenlance" in variants
    assert "myenlance" in variants


def test_expand_has_no_duplicates():
    variants = expand("enlance")
    assert len(variants) == len(set(variants))
