import csv

from catch_domain import report
from catch_domain.models import DomainStatus, NameResult


def make_results():
    clean = NameResult(name="zetavolve", score=0, verdict="CLEAN",
                       domains=[DomainStatus("zetavolve.com", "com", True, "unregistered")])
    taken = NameResult(
        name="enlance", score=53, verdict="TAKEN",
        domains=[DomainStatus("enlance.com", "com", True, "live")],
        lookalikes=["enlanceit.com"],
        search_hits=[{"title": "Enlance", "url": "https://enlance.com", "is_base": True}],
        search_status="done",
    )
    pending = NameResult(name="flintlogic", score=8, verdict="CLEAN",
                         search_status="pending")
    return [taken, clean, pending]


def test_console_table_sorted_safest_first():
    table = report.console_table(make_results())
    lines = table.splitlines()
    assert "NAME" in lines[0] and "VERDICT" in lines[0]
    assert lines[1].startswith("zetavolve")
    assert lines[3].startswith("enlance")


def test_console_table_flags_pending_search():
    table = report.console_table(make_results())
    flintlogic_line = [l for l in table.splitlines() if l.startswith("flintlogic")][0]
    assert "search pending" in flintlogic_line


def test_csv_contains_evidence_rows(tmp_path):
    path = tmp_path / "report.csv"
    report.write_csv(make_results(), path)
    rows = list(csv.reader(path.open(encoding="utf-8")))
    assert rows[0] == ["name", "verdict", "score", "check", "target", "result", "detail"]
    enlance_rows = [r for r in rows if r[0] == "enlance"]
    checks = {r[3] for r in enlance_rows}
    assert checks == {"domain", "ct_lookalike", "search"}


def test_manual_checklist_mentions_trademark_and_socials():
    text = report.MANUAL_CHECKLIST.lower()
    assert "trademark" in text
    assert "github" in text
