"""Tests for tempo adjustment utilities."""

import numpy as np
import pytest
import soundfile as sf

from mozart_minus_one.tempo import (
    bpm_to_seconds_per_beat,
    export_tempo_variants,
    output_filename,
    stretch_audio,
)


def _make_wav(path, duration_s=1.0, sample_rate=22050, channels=1):
    """Write a short synthetic WAV file for testing."""
    n_samples = int(duration_s * sample_rate)
    t = np.linspace(0, duration_s, n_samples, endpoint=False)
    tone = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
    if channels == 2:
        data = np.stack([tone, tone], axis=1)
    else:
        data = tone
    sf.write(str(path), data, sample_rate, subtype="PCM_16")
    return path


def test_bpm_to_seconds_per_beat():
    assert bpm_to_seconds_per_beat(120) == pytest.approx(0.5)


def test_bpm_to_seconds_per_beat_requires_positive_bpm():
    with pytest.raises(ValueError, match="bpm must be positive"):
        bpm_to_seconds_per_beat(0)


def test_bpm_to_seconds_per_beat_negative():
    with pytest.raises(ValueError):
        bpm_to_seconds_per_beat(-10)


def test_output_filename_all_speeds():
    factors = [1.00, 0.95, 0.90, 0.85]
    expected = [
        "track_no_piano_100.wav",
        "track_no_piano_95.wav",
        "track_no_piano_90.wav",
        "track_no_piano_85.wav",
    ]
    for f, e in zip(factors, expected):
        assert output_filename("track", f) == e


def test_stretch_audio_invalid_factor(tmp_path):
    data = np.zeros(1000, dtype=np.float32)
    with pytest.raises(ValueError, match="tempo_factor"):
        stretch_audio(data, 22050, 0.0)


def test_stretch_audio_no_change_at_unity(tmp_path):
    data = np.ones(1000, dtype=np.float32)
    result = stretch_audio(data, 22050, 1.0)
    assert result.shape == data.shape


def test_export_tempo_variants_creates_files(tmp_path):
    source = tmp_path / "backing.wav"
    _make_wav(source, duration_s=0.5)

    created = export_tempo_variants(
        source,
        tmp_path / "exports",
        "test_track",
        [1.00, 0.90],
        overwrite=True,
    )

    assert len(created) == 2
    for p in created:
        assert p.exists()
        assert p.stat().st_size > 0


def test_export_tempo_variants_stereo(tmp_path):
    source = tmp_path / "stereo.wav"
    _make_wav(source, duration_s=0.5, channels=2)

    created = export_tempo_variants(
        source,
        tmp_path / "exports",
        "stereo_track",
        [0.90],
        overwrite=True,
    )

    assert len(created) == 1
    data, _ = sf.read(str(created[0]))
    assert data.ndim == 2
    assert data.shape[1] == 2


def test_export_tempo_variants_duration_approx(tmp_path):
    sample_rate = 22050
    duration_s = 1.0
    source = tmp_path / "input.wav"
    _make_wav(source, duration_s=duration_s, sample_rate=sample_rate)

    factor = 0.90
    created = export_tempo_variants(
        source,
        tmp_path / "exports",
        "dur_test",
        [factor],
        overwrite=True,
    )

    out_data, sr = sf.read(str(created[0]))
    actual_dur = len(out_data) / sr
    expected_dur = duration_s / factor
    assert abs(actual_dur - expected_dur) / expected_dur < 0.05


def test_export_no_overwrite_raises(tmp_path):
    source = tmp_path / "backing.wav"
    _make_wav(source)

    export_dir = tmp_path / "exports"
    export_tempo_variants(source, export_dir, "t", [1.0], overwrite=True)

    created = export_tempo_variants(source, export_dir, "t", [1.0], overwrite=False)
    assert created == []


def test_export_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        export_tempo_variants(
            tmp_path / "nonexistent.wav",
            tmp_path / "out",
            "t",
            [1.0],
        )
