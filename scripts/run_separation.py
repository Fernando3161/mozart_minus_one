"""Run only the source separation stage."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mozart_minus_one.pipeline import load_config
from mozart_minus_one.separate import separate_audio


def main() -> None:
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


if __name__ == "__main__":
    main()
