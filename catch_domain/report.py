"""Output: ranked console table, CSV audit trail, manual next-steps checklist."""
import csv
from pathlib import Path

from catch_domain.models import NameResult

MANUAL_CHECKLIST = """\
Manual final checks for your shortlist (no reliable free API exists for these):
  1. Trademark search:
       IP India:  https://tmrsearch.ipindia.gov.in/tmrpublicsearch/
       USPTO (if targeting the US): https://tmsearch.uspto.gov/
  2. Social handles (open each in a browser):
       github.com/<name>   linkedin.com/company/<name>
       instagram.com/<name>   x.com/<name>
"""


def _summarize(result: NameResult) -> str:
    parts = []
    taken = [d.domain for d in result.domains if d.status in ("live", "registered")]
    if taken:
        parts.append(f"{len(taken)} domain(s) taken: {', '.join(taken[:3])}")
    if result.lookalikes:
        parts.append(f"{len(result.lookalikes)} lookalike(s)")
    if result.search_hits:
        parts.append(f"{len(result.search_hits)} search hit(s)")
    if result.search_status == "pending":
        parts.append("search pending")
    return "; ".join(parts) or "nothing found"


def console_table(results: list[NameResult]) -> str:
    rows = sorted(results, key=lambda r: r.score)
    width = max([len(r.name) for r in rows] + [len("NAME")])
    lines = [f"{'NAME':<{width}}  {'VERDICT':<7}  {'SCORE':>5}  EVIDENCE"]
    for r in rows:
        lines.append(f"{r.name:<{width}}  {r.verdict:<7}  {r.score:>5}  {_summarize(r)}")
    return "\n".join(lines)


def write_csv(results: list[NameResult], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "verdict", "score", "check", "target", "result", "detail"])
        for r in sorted(results, key=lambda x: x.score):
            for d in r.domains:
                writer.writerow([r.name, r.verdict, r.score, "domain", d.domain,
                                 d.status, "base" if d.is_base else "variant"])
            for domain in r.lookalikes:
                writer.writerow([r.name, r.verdict, r.score, "ct_lookalike",
                                 domain, "found", ""])
            for h in r.search_hits:
                writer.writerow([r.name, r.verdict, r.score, "search",
                                 h["url"], "hit", h["title"]])
            if r.search_status != "done":
                writer.writerow([r.name, r.verdict, r.score, "search",
                                 r.name, r.search_status, ""])
