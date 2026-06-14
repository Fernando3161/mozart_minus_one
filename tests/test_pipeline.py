"""Tests for pipeline configuration loading and dry-run behavior."""

import textwrap
from pathlib import Path

import pytest
import yaml

from mozart_minus_one.pipeline import load_config, run_pipeline, _resolve_paths


def _write_config(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh)
    return path


MINIMAL_CFG = {
    "input_file": "data/raw/nonexistent.wav",
    "separation_model": "htdemucs_6s",
    "target_stem": "piano",
    "tempo_factors": [1.0, 0.95, 0.90, 0.85],
    "export_format": "wav",
    "overwrite": False,
    "logging_level": "WARNING",
    "paths": {
        "raw": "data/raw",
        "separated": "data/separated",
        "exports": "data/exports",
    },
    "outputs": {
        "logs": "outputs/logs",
        "reports": "outputs/reports",
    },
}


def test_load_config_returns_dict(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    _write_config(cfg_path, MINIMAL_CFG)
    cfg = load_config(cfg_path)
    assert isinstance(cfg, dict)
    assert cfg["separation_model"] == "htdemucs_6s"


def test_load_config_raises_for_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "ghost.yaml")


def test_load_config_raises_for_empty_file(tmp_path):
    cfg_path = tmp_path / "empty.yaml"
    cfg_path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_config(cfg_path)


def test_resolve_paths_uses_defaults(tmp_path):
    cfg = dict(MINIMAL_CFG)
    paths = _resolve_paths(cfg)
    assert paths["input_file"] == Path("data/raw/nonexistent.wav")
    assert paths["exports_dir"] == Path("data/exports")
    assert paths["logs_dir"] == Path("outputs/logs")


def test_dry_run_does_not_write_audio(tmp_path):
    input_wav = tmp_path / "data" / "raw" / "sample.wav"
    input_wav.parent.mkdir(parents=True)
    input_wav.write_bytes(b"RIFF" + b"\x00" * 40)

    cfg = dict(MINIMAL_CFG)
    cfg["input_file"] = str(input_wav)
    cfg["paths"] = {
        "raw": str(tmp_path / "data" / "raw"),
        "separated": str(tmp_path / "data" / "separated"),
        "exports": str(tmp_path / "data" / "exports"),
    }
    cfg["outputs"] = {
        "logs": str(tmp_path / "outputs" / "logs"),
        "reports": str(tmp_path / "outputs" / "reports"),
    }

    cfg_path = tmp_path / "config.yaml"
    _write_config(cfg_path, cfg)

    summary = run_pipeline(cfg_path, dry_run=True)

    assert summary["dry_run"] is True
    assert summary["created_files"] == []

    exports_dir = Path(cfg["paths"]["exports"])
    wav_files = list(exports_dir.glob("*.wav")) if exports_dir.exists() else []
    assert wav_files == [], "Dry run must not write audio files"


def test_dry_run_reports_expected_files(tmp_path):
    input_wav = tmp_path / "data" / "raw" / "concerto.wav"
    input_wav.parent.mkdir(parents=True)
    input_wav.write_bytes(b"RIFF" + b"\x00" * 40)

    cfg = dict(MINIMAL_CFG)
    cfg["input_file"] = str(input_wav)
    cfg["tempo_factors"] = [1.0, 0.90]
    cfg["paths"] = {
        "raw": str(tmp_path / "data" / "raw"),
        "separated": str(tmp_path / "data" / "separated"),
        "exports": str(tmp_path / "data" / "exports"),
    }
    cfg["outputs"] = {
        "logs": str(tmp_path / "outputs" / "logs"),
        "reports": str(tmp_path / "outputs" / "reports"),
    }

    cfg_path = tmp_path / "config.yaml"
    _write_config(cfg_path, cfg)

    summary = run_pipeline(cfg_path, dry_run=True)

    names = [p.name for p in summary["expected_files"]]
    assert "concerto_no_piano_100.wav" in names
    assert "concerto_no_piano_90.wav" in names


def test_pipeline_fails_on_missing_input(tmp_path):
    cfg = dict(MINIMAL_CFG)
    cfg["input_file"] = str(tmp_path / "missing.wav")
    cfg["paths"] = {
        "raw": str(tmp_path),
        "separated": str(tmp_path / "sep"),
        "exports": str(tmp_path / "exp"),
    }
    cfg["outputs"] = {
        "logs": str(tmp_path / "logs"),
        "reports": str(tmp_path / "rep"),
    }

    cfg_path = tmp_path / "config.yaml"
    _write_config(cfg_path, cfg)

    with pytest.raises(FileNotFoundError, match="does not exist"):
        run_pipeline(cfg_path, dry_run=False)


def test_tempo_factor_interpretation():
    factors = [1.00, 0.95, 0.90, 0.85]
    labels = [int(round(f * 100)) for f in factors]
    assert labels == [100, 95, 90, 85]
