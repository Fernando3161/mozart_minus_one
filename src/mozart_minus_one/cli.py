"""Console entry points for the mozart-minus-one package."""

import argparse
import sys
from pathlib import Path

from mozart_minus_one.pipeline import load_config, run_pipeline
from mozart_minus_one.separate import separate_audio
from mozart_minus_one.tempo import export_tempo_variants


def main() -> None:
    """Full pipeline: separation → accompaniment mix → tempo exports."""
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


def separate_main() -> None:
    """Run only the Demucs source-separation stage."""
    parser = argparse.ArgumentParser(
        description="Run Demucs source separation on the configured input file."
    )
    parser.add_argument(
        "--config",
        default="configs/default.yaml",
        help="Path to YAML configuration file (default: configs/default.yaml)",
    )
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    input_file = Path(cfg["input_file"])
    separated_dir = Path(cfg.get("paths", {}).get("separated", "data/separated"))
    model = cfg.get("separation_model", "htdemucs_6s")
    target_stem = cfg.get("target_stem", "piano")

    print(f"Input:  {input_file}")
    print(f"Model:  {model}")
    print(f"Output: {separated_dir}")

    stems = separate_audio(input_file, separated_dir, model=model, target_stem=target_stem)

    print("\nSeparation complete.")
    for name, path in stems.items():
        print(f"  {name}: {path}")


def export_main() -> None:
    """Create tempo-adjusted exports from an existing no-piano file."""
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
    export_format = cfg.get("export_format", "mp3")
    mp3_bitrate = cfg.get("mp3_bitrate", 192)
    overwrite = cfg.get("overwrite", False)
    solo_level = int(cfg.get("solo_level", 0))
    original_freq = float(cfg.get("original_freq", 0.0))
    target_freq = float(cfg.get("target_freq", 0.0))

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
            "Run the separation stage first: mozart-separate --config ...",
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
        solo_level=solo_level,
        original_freq=original_freq,
        target_freq=target_freq,
        mp3_bitrate=mp3_bitrate,
    )

    print("\nExported files:")
    for p in created:
        print(f"  {p}")
