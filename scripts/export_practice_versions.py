"""Export tempo variants from an existing no-piano file."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mozart_minus_one.pipeline import load_config
from mozart_minus_one.tempo import export_tempo_variants


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create tempo-adjusted practice versions from an existing "
            "no-piano accompaniment file."
        )
    )
    parser.add_argument(
        "--config",
        default="configs/default.yaml",
        help="Path to YAML configuration file (default: configs/default.yaml)",
    )
    parser.add_argument(
        "--input",
        help=(
            "Path to the no-piano WAV file. "
            "If omitted, the path is derived from config and track name."
        ),
    )
    args = parser.parse_args()

    cfg = load_config(Path(args.config))

    exports_dir = Path(cfg.get("paths", {}).get("exports", "data/exports"))
    tempo_factors = cfg.get("tempo_factors", [1.0, 0.95, 0.90, 0.85])
    export_format = cfg.get("export_format", "wav")
    overwrite = cfg.get("overwrite", False)

    if args.input:
        source = Path(args.input)
        track_name = source.stem.replace("_no_piano", "")
    else:
        input_file = Path(cfg["input_file"])
        track_name = input_file.stem
        separated_dir = Path(cfg.get("paths", {}).get("separated", "data/separated"))
        source = separated_dir / f"{track_name}_no_piano.wav"

    if not source.exists():
        print(f"Error: no-piano file not found: {source}", file=sys.stderr)
        print(
            "Run the separation stage first: python scripts/run_separation.py",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Source: {source}")
    print(f"Track:  {track_name}")
    print(f"Speeds: {[int(round(f * 100)) for f in tempo_factors]}")

    created = export_tempo_variants(
        source,
        exports_dir,
        track_name,
        tempo_factors,
        export_format=export_format,
        overwrite=overwrite,
    )

    print("\nExported files:")
    for p in created:
        print(f"  {p}")


if __name__ == "__main__":
    main()
