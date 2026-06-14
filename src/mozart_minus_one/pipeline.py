"""Full pipeline orchestration."""

import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

from mozart_minus_one.separate import separate_audio, validate_input
from mozart_minus_one.mute_piano import get_accompaniment_path
from mozart_minus_one.tempo import export_tempo_variants

DEFAULT_CONFIG = Path("configs/default.yaml")


def load_config(config_path: Path) -> dict:
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )
    with open(config_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        raise ValueError(f"Configuration file is empty: {config_path}")
    return data


def _resolve_paths(cfg: dict) -> dict:
    paths = cfg.get("paths", {})
    outputs = cfg.get("outputs", {})
    return {
        "input_file": Path(cfg["input_file"]),
        "raw_dir": Path(paths.get("raw", "data/raw")),
        "separated_dir": Path(paths.get("separated", "data/separated")),
        "exports_dir": Path(paths.get("exports", "data/exports")),
        "logs_dir": Path(outputs.get("logs", "outputs/logs")),
        "reports_dir": Path(outputs.get("reports", "outputs/reports")),
    }


def _setup_logging(logs_dir: Path, track_name: str, level: str) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{track_name}.log"

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(numeric_level)

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        root.addHandler(sh)

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    return log_path


def _ensure_dirs(paths: dict) -> None:
    for key in ("separated_dir", "exports_dir", "logs_dir", "reports_dir"):
        paths[key].mkdir(parents=True, exist_ok=True)


def run_pipeline(
    config_path: Path = DEFAULT_CONFIG,
    dry_run: bool = False,
) -> dict:
    """
    Execute the full mozart-minus-one pipeline.

    Returns a summary dict with keys:
        input_file, created_files, log_path, dry_run
    """
    cfg = load_config(config_path)
    paths = _resolve_paths(cfg)

    input_file: Path = paths["input_file"]
    track_name: str = input_file.stem
    model: str = cfg.get("separation_model", "htdemucs_6s")
    target_stem: str = cfg.get("target_stem", "piano")
    tempo_factors: list[float] = cfg.get("tempo_factors", [1.0, 0.95, 0.90, 0.85])
    export_format: str = cfg.get("export_format", "wav")
    overwrite: bool = cfg.get("overwrite", False)
    log_level: str = cfg.get("logging_level", "INFO")

    log_path = _setup_logging(paths["logs_dir"], track_name, log_level)
    log = logging.getLogger(__name__)

    log.info("=== mozart-minus-one pipeline started ===")
    log.info("Config: %s", config_path)
    log.info("Input file: %s", input_file)
    log.info("Model: %s", model)
    log.info("Target stem: %s", target_stem)
    log.info("Tempo factors: %s", tempo_factors)
    log.info("Overwrite: %s", overwrite)
    log.info("Dry run: %s", dry_run)

    validate_input(input_file)

    label_list = [int(round(f * 100)) for f in tempo_factors]
    expected_outputs = [
        paths["exports_dir"] / f"{track_name}_no_piano_{label}.{export_format}"
        for label in label_list
    ]

    if dry_run:
        print("\n[Dry run] Pipeline would process:")
        print(f"  Input:  {input_file}")
        print(f"  Model:  {model}")
        print(f"  Speeds: {label_list}")
        print("\n[Dry run] Expected output files:")
        for p in expected_outputs:
            print(f"  {p}")
        print(f"\n[Dry run] Log: {log_path}")
        log.info("Dry run complete – no files written.")
        return {
            "input_file": input_file,
            "created_files": [],
            "expected_files": expected_outputs,
            "log_path": log_path,
            "dry_run": True,
        }

    _ensure_dirs(paths)

    log.info("Running source separation...")
    stems = separate_audio(
        input_file,
        paths["separated_dir"],
        model=model,
        target_stem=target_stem,
    )

    log.info("Selecting no-piano accompaniment...")
    accompaniment = get_accompaniment_path(
        stems,
        paths["separated_dir"],
        track_name,
        overwrite=overwrite,
    )

    log.info("Exporting tempo variants...")
    created = export_tempo_variants(
        accompaniment,
        paths["exports_dir"],
        track_name,
        tempo_factors,
        export_format=export_format,
        overwrite=overwrite,
    )

    log.info("Pipeline finished. Files created: %d", len(created))

    summary = {
        "input_file": input_file,
        "created_files": created,
        "log_path": log_path,
        "dry_run": False,
    }

    _print_summary(summary)
    return summary


def _print_summary(summary: dict) -> None:
    print("\nPipeline completed.\n")
    print(f"Input:\n  {summary['input_file']}\n")
    if summary["created_files"]:
        print("Created:")
        for p in summary["created_files"]:
            print(f"  {p}")
    else:
        print("Created:\n  (none – all files may have been skipped)")
    print(f"\nLog:\n  {summary['log_path']}\n")
