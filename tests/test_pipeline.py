"""Tests for pipeline configuration loading and dry-run behavior."""

from pathlib import Path

import pytest
import yaml

from mozart_minus_one.pipeline import _resolve_paths, load_config, run_pipeline


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
    "export_format": "mp3",
    "mp3_bitrate": 192,
    "solo_level": 0,
    "original_freq": 0.0,
    "target_freq": 0.0,
    "reference_note": "",
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


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

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


def test_load_config_reads_new_params(tmp_path):
    cfg = dict(MINIMAL_CFG)
    cfg["solo_level"] = 20
    cfg["original_freq"] = 314.0
    cfg["target_freq"] = 311.13
    cfg["reference_note"] = "e_b"
    cfg_path = tmp_path / "config.yaml"
    _write_config(cfg_path, cfg)

    loaded = load_config(cfg_path)
    assert loaded["solo_level"] == 20
    assert loaded["original_freq"] == pytest.approx(314.0)
    assert loaded["target_freq"] == pytest.approx(311.13)
    assert loaded["reference_note"] == "e_b"


def test_load_config_reads_mp3_format(tmp_path):
    cfg = dict(MINIMAL_CFG)
    cfg["export_format"] = "mp3"
    cfg["mp3_bitrate"] = 128
    cfg_path = tmp_path / "config.yaml"
    _write_config(cfg_path, cfg)

    loaded = load_config(cfg_path)
    assert loaded["export_format"] == "mp3"
    assert loaded["mp3_bitrate"] == 128


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def test_resolve_paths_uses_defaults(tmp_path):
    cfg = dict(MINIMAL_CFG)
    paths = _resolve_paths(cfg)
    assert paths["input_file"] == Path("data/raw/nonexistent.wav")
    assert paths["exports_dir"] == Path("data/exports")
    assert paths["logs_dir"] == Path("outputs/logs")


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------

def _dry_run_config(tmp_path, extra=None):
    input_wav = tmp_path / "data" / "raw" / "concerto.wav"
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
    if extra:
        cfg.update(extra)

    cfg_path = tmp_path / "config.yaml"
    _write_config(cfg_path, cfg)
    return cfg_path


def test_dry_run_does_not_write_audio(tmp_path):
    cfg_path = _dry_run_config(tmp_path)
    summary = run_pipeline(cfg_path, dry_run=True)

    assert summary["dry_run"] is True
    assert summary["created_files"] == []

    exports_dir = Path(MINIMAL_CFG["paths"]["exports"]) if False else (
        tmp_path / "data" / "exports"
    )
    wav_files = list(exports_dir.glob("*")) if exports_dir.exists() else []
    audio_files = [f for f in wav_files if f.suffix in (".wav", ".mp3")]
    assert audio_files == []


def test_dry_run_reports_mp3_expected_files(tmp_path):
    cfg_path = _dry_run_config(tmp_path, extra={"tempo_factors": [1.0, 0.90]})
    summary = run_pipeline(cfg_path, dry_run=True)

    names = [p.name for p in summary["expected_files"]]
    assert "concerto_no_piano_100.mp3" in names
    assert "concerto_no_piano_90.mp3" in names


def test_dry_run_with_solo_level_uses_correct_filename(tmp_path):
    cfg_path = _dry_run_config(
        tmp_path,
        extra={"tempo_factors": [1.0], "solo_level": 20},
    )
    summary = run_pipeline(cfg_path, dry_run=True)
    names = [p.name for p in summary["expected_files"]]
    assert "concerto_piano20pct_100.mp3" in names


def test_dry_run_with_pitch_params_does_not_crash(tmp_path):
    cfg_path = _dry_run_config(
        tmp_path,
        extra={
            "original_freq": 314.0,
            "target_freq": 311.13,
            "reference_note": "e_b",
        },
    )
    summary = run_pipeline(cfg_path, dry_run=True)
    assert summary["dry_run"] is True


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Miscellaneous
# ---------------------------------------------------------------------------

def test_tempo_factor_interpretation():
    factors = [1.00, 0.95, 0.90, 0.85]
    labels = [int(round(f * 100)) for f in factors]
    assert labels == [100, 95, 90, 85]


def test_solo_level_range():
    from mozart_minus_one.mute_piano import create_accompaniment

    with pytest.raises(ValueError, match="solo_level"):
        create_accompaniment({}, Path("x.wav"), solo_level=101)

    with pytest.raises(ValueError, match="solo_level"):
        create_accompaniment({}, Path("x.wav"), solo_level=-1)
