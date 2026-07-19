import pytest

from catch_domain import __main__ as cli
from catch_domain.models import NameResult


def test_read_names_normalizes_dedupes_and_skips_comments(tmp_path):
    f = tmp_path / "names.txt"
    f.write_text(
        "# candidates\n"
        "Enlance\n"
        "enlance   # duplicate after normalize\n"
        "\n"
        "Zeta-Volve\n",
        encoding="utf-8",
    )
    assert cli.read_names(f) == ["enlance", "zetavolve"]


def test_read_names_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit):
        cli.read_names(tmp_path / "nope.txt")


def test_read_names_empty_file_exits(tmp_path):
    f = tmp_path / "names.txt"
    f.write_text("# only comments\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        cli.read_names(f)


def test_main_end_to_end_with_faked_pipeline(tmp_path, monkeypatch, capsys):
    f = tmp_path / "names.txt"
    f.write_text("zetavolve\n", encoding="utf-8")

    def fake_check_name(name, cache, do_search=True):
        return NameResult(name=name, score=0, verdict="CLEAN")

    monkeypatch.setattr(cli, "check_name", fake_check_name)
    cli.main([str(f), "--cache", str(tmp_path / "c.json"),
              "--report", str(tmp_path / "r.csv"), "--no-search"])
    out = capsys.readouterr().out
    assert "zetavolve" in out
    assert "CLEAN" in out
    assert (tmp_path / "r.csv").exists()


def test_tlds_flag_overrides_config(tmp_path, monkeypatch):
    from catch_domain import config
    f = tmp_path / "names.txt"
    f.write_text("zetavolve\n", encoding="utf-8")
    monkeypatch.setattr(cli, "check_name",
                        lambda name, cache, do_search=True: NameResult(name=name))
    original = list(config.TLDS)
    try:
        cli.main([str(f), "--tlds", "com,.in", "--cache", str(tmp_path / "c.json"),
                  "--report", str(tmp_path / "r.csv")])
        assert config.TLDS == ["com", "in"]
    finally:
        config.TLDS[:] = original
