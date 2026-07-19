"""CLI entry point: python -m catch_domain names.txt"""
import argparse
import sys
from pathlib import Path

from catch_domain import config, report
from catch_domain.cache import Cache
from catch_domain.pipeline import check_name
from catch_domain.variants import normalize


def read_names(path: Path) -> list[str]:
    if not path.exists():
        sys.exit(f"error: input file not found: {path}")
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned = normalize(line.split("#", 1)[0])
        if cleaned:
            names.append(cleaned)
    if not names:
        sys.exit(f"error: no names found in {path}")
    return list(dict.fromkeys(names))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="catch_domain",
        description="Filter brand-name candidates by real internet presence.")
    parser.add_argument("names_file", type=Path,
                        help="text file, one candidate name per line, # comments")
    parser.add_argument("--tlds", help="comma-separated TLD list, e.g. com,in,io")
    parser.add_argument("--no-search", action="store_true",
                        help="skip the DuckDuckGo web-presence stage")
    parser.add_argument("--refresh", action="store_true",
                        help="ignore cached results and re-check everything")
    parser.add_argument("--cache", type=Path, default=Path("cache.json"))
    parser.add_argument("--report", type=Path, default=Path("report.csv"))
    args = parser.parse_args(argv)

    if args.tlds:
        config.TLDS[:] = [t.strip().lstrip(".")
                          for t in args.tlds.split(",") if t.strip()]

    names = read_names(args.names_file)
    cache = Cache(args.cache, refresh=args.refresh)
    results = []
    for i, name in enumerate(names, 1):
        print(f"[{i}/{len(names)}] checking {name} ...", flush=True)
        results.append(check_name(name, cache, do_search=not args.no_search))
        cache.save()  # save as we go so an interrupt loses nothing
    print()
    print(report.console_table(results))
    report.write_csv(results, args.report)
    print(f"\nFull evidence written to {args.report}")
    print()
    print(report.MANUAL_CHECKLIST)


if __name__ == "__main__":
    main()
