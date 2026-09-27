"""Refresh the fixed Yahoo ETF comparison cache for the daily Pages build.

Run: python -m scripts.refresh_comparison
or:  python scripts/refresh_comparison.py --output data/etf_comparison.json
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishing.comparison_data import DEFAULT_START, read_cache, refresh_dataset, write_atomic


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/etf_comparison.json")
    parser.add_argument("--start", default=DEFAULT_START, help=f"First requested date, YYYY-MM-DD (default: {DEFAULT_START})")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if no valid peer histories remain; stale validated cache is usable. Always persist status.")
    args = parser.parse_args(argv)
    try:
        dataset = refresh_dataset(read_cache(args.output), start=args.start)
    except ValueError as exc:
        parser.error(str(exc))
    write_atomic(args.output, dataset)
    print(f"ETF comparison refresh: {dataset['status']} ({dataset['last_attempt_at']})")
    for peer in dataset["series"]:
        print(f"  {peer['id']}: {peer['status']}; as of {peer['as_of'] or 'unavailable'}; {len(peer['observations'])} daily observations")
        if peer.get("error"):
            print(f"    {peer['error']}")
    return 1 if args.strict and dataset["status"] == "unavailable" else 0


if __name__ == "__main__":
    raise SystemExit(main())
