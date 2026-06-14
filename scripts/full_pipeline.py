"""Run the complete mozart-minus-one pipeline."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mozart_minus_one.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full mozart-minus-one pipeline from raw audio to practice exports."
    )
    parser.add_argument(
        "--config",
        default="configs/default.yaml",
        help="Path to YAML configuration file (default: configs/default.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate paths and print planned actions without running separation or writing audio.",
    )
    args = parser.parse_args()

    try:
        run_pipeline(Path(args.config), dry_run=args.dry_run)
    except (FileNotFoundError, FileExistsError, ValueError, RuntimeError) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
