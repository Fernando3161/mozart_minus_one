"""Tests for tempo adjustment, pitch shifting, and MP3 export utilities."""

import math

import numpy as np
import pytest
import soundfile as sf

from mozart_minus_one.tempo import (
    export_tempo_variants,
    frequency_to_semitones,
    output_filename,
    pitch_shift_audio,
    stretch_audio,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav(path, duration_s=1.0, sample_rate=22050, channels=1):
    n = int(duration_s * sample_rate)
    t = np.linspace(0, duration_s, n, endpoint=False)
    tone = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
    data = np.stack([tone, tone], axis=1) if channels == 2 else tone
    sf.write(str(path), data, sample_rate, subtype="PCM_16")
    return path


# ---------------------------------------------------------------------------
# Output filename
# ---------------------------------------------------------------------------

def test_output_filename_all_speeds():
    factors = [1.00, 0.95, 0.90, 0.85]
    expected = [
        "track_no_piano_100.mp3",
        "track_no_piano_95.mp3",
        "track_no_piano_90.mp3",
        "track_no_piano_85.mp3",
    ]
    for f, e in zip(factors, expected):
        assert output_filename("track", f) == e


def test_output_filename_solo_level_zero():
    assert output_filename("t", 1.0, solo_level=0) == "t_no_piano_100.mp3"


def test_output_filename_solo_level_nonzero():
    assert output_filename("t", 0.90, solo_level=20) == "t_piano20pct_90.mp3"
    assert output_filename("t", 1.00, solo_level=100) == "t_piano100pct_100.mp3"


def test_output_filename_wav_format():
    assert output_filename("track", 0.90, fmt="wav") == "track_no_piano_90.wav"


# ---------------------------------------------------------------------------
# Frequency / semitone conversion
# ---------------------------------------------------------------------------

def test_frequency_to_semitones_identity():
    assert frequency_to_semitones(440.0, 440.0) == pytest.approx(0.0)


def test_frequency_to_semitones_octave():
    assert frequency_to_semitones(440.0, 880.0) == pytest.approx(12.0, abs=1e-6)
    assert frequency_to_semitones(880.0, 440.0) == pytest.approx(-12.0, abs=1e-6)


def test_frequency_to_semitones_a440_to_a448():
    n = frequency_to_semitones(448.0, 440.0)
    assert n < 0
    assert abs(n) < 1.0


def test_frequency_to_semitones_eb_example():
    n = frequency_to_semitones(314.0, 311.13)
    assert n == pytest.approx(12.0 * math.log2(311.13 / 314.0), rel=1e-6)
    assert n < 0


def test_frequency_to_semitones_rejects_zero():
    with pytest.raises(ValueError):
        frequency_to_semitones(0.0, 440.0)
    with pytest.raises(ValueError):
        frequency_to_semitones(440.0, 0.0)


# ---------------------------------------------------------------------------
# Pitch shifting
# ---------------------------------------------------------------------------

def test_pitch_shift_returns_array(tmp_path):
    data = np.sin(np.linspace(0, 2 * math.pi * 440, 4410)).astype(np.float32)
    result = pitch_shift_audio(data, 22050, 448.0, 440.0)
    assert isinstance(result, np.ndarray)
    assert result.shape[0] > 0


def test_pitch_shift_negligible_skip(tmp_path):
    data = np.ones(1000, dtype=np.float32)
    result = pitch_shift_audio(data, 22050, 440.0, 440.001)
    assert result is data


def test_pitch_shift_rejects_non_positive():
    data = np.zeros(100, dtype=np.float32)
    with pytest.raises(ValueError):
        pitch_shift_audio(data, 22050, 0.0, 440.0)


# ---------------------------------------------------------------------------
# Stretch
# ---------------------------------------------------------------------------

def test_stretch_audio_invalid_factor():
    data = np.zeros(1000, dtype=np.float32)
    with pytest.raises(ValueError, match="tempo_factor"):
        stretch_audio(data, 22050, 0.0)


def test_stretch_audio_no_change_at_unity():
    data = np.ones(1000, dtype=np.float32)
    result = stretch_audio(data, 22050, 1.0)
    assert result.shape == data.shape


# ---------------------------------------------------------------------------
# export_tempo_variants – WAV round-trip tests
# ---------------------------------------------------------------------------

def test_export_tempo_variants_creates_mp3_files(tmp_path):
    source = tmp_path / "backing.wav"
    _make_wav(source, duration_s=0.5)

    created = export_tempo_variants(
        source,
        tmp_path / "exports",
        "test_track",
        [1.00, 0.90],
        export_format="mp3",
        overwrite=True,
    )

    assert len(created) == 2
    for p in created:
        assert p.suffix == ".mp3"
        assert p.exists()
        assert p.stat().st_size > 0


def test_export_tempo_variants_creates_wav_files(tmp_path):
    source = tmp_path / "backing.wav"
    _make_wav(source, duration_s=0.5)

    created = export_tempo_variants(
        source,
        tmp_path / "exports",
        "test_track",
        [1.00, 0.90],
        export_format="wav",
        overwrite=True,
    )

    assert len(created) == 2
    for p in created:
        assert p.suffix == ".wav"
        assert p.exists()
        assert p.stat().st_size > 0


def test_export_tempo_variants_stereo_wav(tmp_path):
    source = tmp_path / "stereo.wav"
    _make_wav(source, duration_s=0.5, channels=2)

    created = export_tempo_variants(
        source,
        tmp_path / "exports",
        "stereo_track",
        [0.90],
        export_format="wav",
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
        export_format="wav",
        overwrite=True,
    )

    out_data, sr = sf.read(str(created[0]))
    actual_dur = len(out_data) / sr
    expected_dur = duration_s / factor
    assert abs(actual_dur - expected_dur) / expected_dur < 0.05


def test_export_no_overwrite_skips_existing(tmp_path):
    source = tmp_path / "backing.wav"
    _make_wav(source)

    export_dir = tmp_path / "exports"
    export_tempo_variants(
        source, export_dir, "t", [1.0], export_format="wav", overwrite=True
    )

    created = export_tempo_variants(
        source, export_dir, "t", [1.0], export_format="wav", overwrite=False
    )
    assert created == []


def test_export_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        export_tempo_variants(
            tmp_path / "nonexistent.wav",
            tmp_path / "out",
            "t",
            [1.0],
        )


# ---------------------------------------------------------------------------
# export_tempo_variants – solo_level filenames
# ---------------------------------------------------------------------------

def test_export_solo_level_zero_filename(tmp_path):
    source = tmp_path / "backing.wav"
    _make_wav(source, duration_s=0.3)

    created = export_tempo_variants(
        source,
        tmp_path / "out",
        "track",
        [1.0],
        export_format="mp3",
        solo_level=0,
        overwrite=True,
    )
    assert created[0].name == "track_no_piano_100.mp3"


def test_export_solo_level_nonzero_filename(tmp_path):
    source = tmp_path / "backing.wav"
    _make_wav(source, duration_s=0.3)

    created = export_tempo_variants(
        source,
        tmp_path / "out",
        "track",
        [1.0],
        export_format="mp3",
        solo_level=20,
        overwrite=True,
    )
    assert created[0].name == "track_piano20pct_100.mp3"


# ---------------------------------------------------------------------------
# export_tempo_variants – pitch shift integration
# ---------------------------------------------------------------------------

def test_export_with_pitch_shift_produces_file(tmp_path):
    source = tmp_path / "backing.wav"
    _make_wav(source, duration_s=0.5, sample_rate=22050)

    created = export_tempo_variants(
        source,
        tmp_path / "out",
        "track",
        [1.0],
        export_format="wav",
        original_freq=448.0,
        target_freq=440.0,
        overwrite=True,
    )

    assert len(created) == 1
    assert created[0].exists()
    assert created[0].stat().st_size > 0


def test_export_no_pitch_shift_when_freqs_equal(tmp_path):
    source = tmp_path / "backing.wav"
    _make_wav(source, duration_s=0.3)

    created = export_tempo_variants(
        source,
        tmp_path / "out",
        "track",
        [1.0],
        export_format="wav",
        original_freq=440.0,
        target_freq=440.0,
        overwrite=True,
    )

    assert len(created) == 1
