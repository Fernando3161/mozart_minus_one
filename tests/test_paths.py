"""Tests for path handling, project structure, and output filename generation."""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from mozart_minus_one.separate import validate_input, SUPPORTED_EXTENSIONS
from mozart_minus_one.tempo import output_filename
from mozart_minus_one.mute_piano import create_accompaniment, get_accompaniment_path


# ---------------------------------------------------------------------------
# Project structure
# ---------------------------------------------------------------------------

def test_project_dirs_exist():
    for folder in [
        "data/raw",
        "data/separated",
        "data/exports",
        "outputs/logs",
        "outputs/reports",
    ]:
        assert Path(folder).exists(), f"Expected directory missing: {folder}"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_validate_input_raises_for_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="does not exist"):
        validate_input(tmp_path / "ghost.wav")


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


# ---------------------------------------------------------------------------
# Output filename – default MP3 format
# ---------------------------------------------------------------------------

def test_output_filename_deterministic():
    assert output_filename("track", 0.90) == output_filename("track", 0.90)


def test_output_filename_default_mp3():
    assert output_filename("mozart_k488", 1.00) == "mozart_k488_no_piano_100.mp3"
    assert output_filename("mozart_k488", 0.95) == "mozart_k488_no_piano_95.mp3"
    assert output_filename("mozart_k488", 0.90) == "mozart_k488_no_piano_90.mp3"
    assert output_filename("mozart_k488", 0.85) == "mozart_k488_no_piano_85.mp3"


def test_output_filename_explicit_wav():
    assert output_filename("track", 0.90, fmt="wav") == "track_no_piano_90.wav"


def test_output_filename_solo_level_zero():
    assert output_filename("track", 1.0, solo_level=0) == "track_no_piano_100.mp3"


def test_output_filename_solo_level_20():
    assert output_filename("track", 1.0, solo_level=20) == "track_piano20pct_100.mp3"


def test_output_filename_solo_level_100():
    assert output_filename("track", 0.90, solo_level=100) == "track_piano100pct_90.mp3"


# ---------------------------------------------------------------------------
# Mute piano – create_accompaniment
# ---------------------------------------------------------------------------

def _make_stem(path: Path, value: float = 0.5, sr: int = 22050, seconds: float = 0.5):
    n = int(sr * seconds)
    data = np.full((n, 2), value, dtype=np.float32)
    sf.write(str(path), data, sr, subtype="PCM_16")


def test_create_accompaniment_solo_level_zero(tmp_path):
    no_piano = tmp_path / "no_piano.wav"
    piano = tmp_path / "piano.wav"
    _make_stem(no_piano, value=0.3)
    _make_stem(piano, value=0.7)

    dest = tmp_path / "out.wav"
    result = create_accompaniment(
        {"no_piano": no_piano, "piano": piano},
        dest,
        solo_level=0,
    )

    assert result == dest
    assert dest.exists()
    data, _ = sf.read(str(dest))
    assert np.allclose(data, 0.3, atol=0.01)


def test_create_accompaniment_solo_level_100(tmp_path):
    no_piano = tmp_path / "no_piano.wav"
    piano = tmp_path / "piano.wav"
    _make_stem(no_piano, value=0.3)
    _make_stem(piano, value=0.5)

    dest = tmp_path / "out.wav"
    create_accompaniment(
        {"no_piano": no_piano, "piano": piano},
        dest,
        solo_level=100,
    )

    data, _ = sf.read(str(dest))
    expected = np.clip(0.3 + 0.5 * 1.0, -1, 1)
    assert np.allclose(data, expected, atol=0.01)


def test_create_accompaniment_partial_mix(tmp_path):
    no_piano = tmp_path / "no_piano.wav"
    piano = tmp_path / "piano.wav"
    _make_stem(no_piano, value=0.2)
    _make_stem(piano, value=0.4)

    dest = tmp_path / "out.wav"
    create_accompaniment(
        {"no_piano": no_piano, "piano": piano},
        dest,
        solo_level=50,
    )

    data, _ = sf.read(str(dest))
    expected = np.clip(0.2 + 0.4 * 0.5, -1, 1)
    assert np.allclose(data, expected, atol=0.02)


def test_create_accompaniment_no_overwrite_raises(tmp_path):
    no_piano = tmp_path / "no_piano.wav"
    _make_stem(no_piano)

    dest = tmp_path / "out.wav"
    create_accompaniment({"no_piano": no_piano}, dest, solo_level=0)

    with pytest.raises(FileExistsError):
        create_accompaniment({"no_piano": no_piano}, dest, solo_level=0, overwrite=False)


def test_create_accompaniment_missing_no_piano_key(tmp_path):
    with pytest.raises(KeyError, match="no_piano"):
        create_accompaniment({}, tmp_path / "out.wav")


def test_create_accompaniment_solo_level_out_of_range(tmp_path):
    with pytest.raises(ValueError, match="solo_level"):
        create_accompaniment({}, tmp_path / "out.wav", solo_level=150)


def test_get_accompaniment_path_filename_solo_zero(tmp_path):
    no_piano = tmp_path / "no_piano.wav"
    _make_stem(no_piano)

    result = get_accompaniment_path(
        {"no_piano": no_piano},
        tmp_path,
        "mytrack",
        solo_level=0,
    )
    assert result.name == "mytrack_no_piano.wav"


def test_get_accompaniment_path_filename_solo_nonzero(tmp_path):
    no_piano = tmp_path / "no_piano.wav"
    piano = tmp_path / "piano.wav"
    _make_stem(no_piano)
    _make_stem(piano)

    result = get_accompaniment_path(
        {"no_piano": no_piano, "piano": piano},
        tmp_path,
        "mytrack",
        solo_level=20,
    )
    assert result.name == "mytrack_piano20pct.wav"
