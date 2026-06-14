"""Tests for path handling and project structure."""

from pathlib import Path

import pytest

from mozart_minus_one.separate import validate_input, SUPPORTED_EXTENSIONS
from mozart_minus_one.tempo import output_filename


def test_project_dirs_exist():
    for folder in [
        "data/raw",
        "data/separated",
        "data/exports",
        "outputs/logs",
        "outputs/reports",
    ]:
        assert Path(folder).exists(), f"Expected directory missing: {folder}"


def test_validate_input_raises_for_missing_file(tmp_path):
    missing = tmp_path / "ghost.wav"
    with pytest.raises(FileNotFoundError, match="does not exist"):
        validate_input(missing)


def test_validate_input_raises_for_unsupported_format(tmp_path):
    bad_file = tmp_path / "audio.xyz"
    bad_file.write_bytes(b"not audio")
    with pytest.raises(ValueError, match="Unsupported audio format"):
        validate_input(bad_file)


def test_validate_input_raises_for_directory(tmp_path):
    with pytest.raises(ValueError, match="not a file"):
        validate_input(tmp_path)


def test_validate_input_accepts_supported_formats(tmp_path):
    for ext in SUPPORTED_EXTENSIONS:
        f = tmp_path / f"track{ext}"
        f.write_bytes(b"dummy")
        result = validate_input(f)
        assert result == f


def test_output_filename_deterministic():
    name1 = output_filename("track", 0.90)
    name2 = output_filename("track", 0.90)
    assert name1 == name2


def test_output_filename_format():
    assert output_filename("mozart_k488", 1.00) == "mozart_k488_no_piano_100.wav"
    assert output_filename("mozart_k488", 0.95) == "mozart_k488_no_piano_95.wav"
    assert output_filename("mozart_k488", 0.90) == "mozart_k488_no_piano_90.wav"
    assert output_filename("mozart_k488", 0.85) == "mozart_k488_no_piano_85.wav"


def test_output_filename_custom_format():
    assert output_filename("track", 0.90, "mp3") == "track_no_piano_90.mp3"
