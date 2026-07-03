"""PulseFlow entry point — invoked by the daily cron and by hand.

Usage:
    uv run python scripts/run_hunt.py            # full pipeline (Phase 2+)
    uv run python scripts/run_hunt.py --dry-run  # fetch/filter/score only, no DB/Slack (Phase 1+)
"""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the PulseFlow job hunt pipeline.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="fetch, filter, and score without touching Supabase or Slack",
    )
    args = parser.parse_args()

    mode = "dry-run" if args.dry_run else "full"
    print(f"pulseflow: {mode} pipeline not implemented yet (Phase 1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
