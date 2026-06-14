"""Tempo adjustment, pitch shifting, and MP3 export utilities."""

import logging
import math
from pathlib import Path

import numpy as np
import soundfile as sf

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Audio I/O
# ---------------------------------------------------------------------------

def _load_audio(path: Path) -> tuple[np.ndarray, int]:
    data, sample_rate = sf.read(str(path), always_2d=False)
    return data, sample_rate


def _save_mp3(path: Path, data: np.ndarray, sample_rate: int, bitrate: int = 192) -> None:
    import lameenc

    data_clipped = np.clip(data, -1.0, 1.0)
    data_i16 = (data_clipped * 32767).astype(np.int16)

    if data_i16.ndim == 1:
        channels = 1
    else:
        channels = data_i16.shape[1]

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(bitrate)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(channels)
    encoder.set_quality(2)

    mp3_bytes = encoder.encode(np.ascontiguousarray(data_i16).tobytes())
    mp3_bytes += encoder.flush()

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "wb") as fh:
        fh.write(mp3_bytes)


def _save_audio(path: Path, data: np.ndarray, sample_rate: int, bitrate: int = 192) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".mp3":
        _save_mp3(path, data, sample_rate, bitrate=bitrate)
    else:
        sf.write(str(path), data, sample_rate, subtype="PCM_16")


# ---------------------------------------------------------------------------
# Time stretching
# ---------------------------------------------------------------------------

def _stretch_pyrubberband(
    data: np.ndarray, sample_rate: int, tempo_factor: float
) -> np.ndarray:
    import pyrubberband
    if data.ndim == 1:
        return pyrubberband.time_stretch(data, sample_rate, tempo_factor)
    channels = [
        pyrubberband.time_stretch(data[:, ch], sample_rate, tempo_factor)
        for ch in range(data.shape[1])
    ]
    return np.stack(channels, axis=1)


def _stretch_librosa(
    data: np.ndarray, sample_rate: int, tempo_factor: float
) -> np.ndarray:
    import librosa
    rate = tempo_factor  # librosa rate < 1 -> slower
    if data.ndim == 1:
        return librosa.effects.time_stretch(data.astype(np.float32), rate=rate)
    channels = [
        librosa.effects.time_stretch(data[:, ch].astype(np.float32), rate=rate)
        for ch in range(data.shape[1])
    ]
    return np.stack(channels, axis=1)


def stretch_audio(
    data: np.ndarray, sample_rate: int, tempo_factor: float
) -> np.ndarray:
    """
    Time-stretch *data* by *tempo_factor* while preserving pitch.

    A factor of 0.9 plays at 90% speed (slower, longer output).
    Tries pyrubberband first; falls back to librosa.
    """
    if not (0.1 <= tempo_factor <= 2.0):
        raise ValueError(
            f"tempo_factor must be between 0.1 and 2.0, got {tempo_factor}"
        )

    try:
        result = _stretch_pyrubberband(data, sample_rate, tempo_factor)
        log.debug("Time-stretch via pyrubberband (factor=%s)", tempo_factor)
        return result
    except Exception as pyrb_err:
        log.warning(
            "pyrubberband unavailable (%s); falling back to librosa.", pyrb_err
        )

    return _stretch_librosa(data, sample_rate, tempo_factor)


# ---------------------------------------------------------------------------
# Pitch shifting
# ---------------------------------------------------------------------------

def frequency_to_semitones(original_freq: float, target_freq: float) -> float:
    """
    Convert a frequency ratio to a semitone offset.

    Example: 448 Hz -> 440 Hz gives ≈ −0.31 semitones.
    """
    if original_freq <= 0 or target_freq <= 0:
        raise ValueError(
            f"Frequencies must be positive, got {original_freq} and {target_freq}"
        )
    return 12.0 * math.log2(target_freq / original_freq)


def _shift_pyrubberband(
    data: np.ndarray, sample_rate: int, n_steps: float
) -> np.ndarray:
    import pyrubberband
    if data.ndim == 1:
        return pyrubberband.pitch_shift(data, sample_rate, n_steps)
    channels = [
        pyrubberband.pitch_shift(data[:, ch], sample_rate, n_steps)
        for ch in range(data.shape[1])
    ]
    return np.stack(channels, axis=1)


def _shift_librosa(
    data: np.ndarray, sample_rate: int, n_steps: float
) -> np.ndarray:
    import librosa
    if data.ndim == 1:
        return librosa.effects.pitch_shift(
            data.astype(np.float32), sr=sample_rate, n_steps=n_steps
        )
    channels = [
        librosa.effects.pitch_shift(
            data[:, ch].astype(np.float32), sr=sample_rate, n_steps=n_steps
        )
        for ch in range(data.shape[1])
    ]
    return np.stack(channels, axis=1)


def pitch_shift_audio(
    data: np.ndarray,
    sample_rate: int,
    original_freq: float,
    target_freq: float,
) -> np.ndarray:
    """
    Shift pitch so that a note sounding at *original_freq* plays at *target_freq*.

    Tempo is unchanged. Tries pyrubberband first, falls back to librosa.
    Returns *data* unmodified when the shift is negligible (< 0.001 semitones).
    """
    if original_freq <= 0 or target_freq <= 0:
        raise ValueError("Frequencies must be positive")

    n_steps = frequency_to_semitones(original_freq, target_freq)

    if abs(n_steps) < 0.001:
        log.debug("Pitch shift negligible (%.6f semitones), skipping.", n_steps)
        return data

    log.info(
        "Pitch shift: %.4f semitones (%.3f Hz -> %.3f Hz)",
        n_steps, original_freq, target_freq,
    )

    try:
        result = _shift_pyrubberband(data, sample_rate, n_steps)
        log.debug("Pitch shift via pyrubberband")
        return result
    except Exception as pyrb_err:
        log.warning(
            "pyrubberband unavailable (%s); falling back to librosa for pitch shift.",
            pyrb_err,
        )

    return _shift_librosa(data, sample_rate, n_steps)


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

def output_filename(
    track_name: str,
    factor: float,
    fmt: str = "mp3",
    solo_level: int = 0,
) -> str:
    """
    Return the deterministic output filename for a tempo factor and solo level.

    solo_level=0  -> ``<track>_no_piano_<speed>.mp3``
    solo_level>0  -> ``<track>_piano<N>pct_<speed>.mp3``
    """
    label = int(round(factor * 100))
    stem_part = "no_piano" if solo_level == 0 else f"piano{solo_level}pct"
    return f"{track_name}_{stem_part}_{label}.{fmt}"


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------

def export_tempo_variants(
    source_path: Path,
    export_dir: Path,
    track_name: str,
    tempo_factors: list[float],
    export_format: str = "mp3",
    overwrite: bool = False,
    solo_level: int = 0,
    original_freq: float = 0.0,
    target_freq: float = 0.0,
    mp3_bitrate: int = 192,
) -> list[Path]:
    """
    Create tempo-adjusted (and optionally pitch-shifted) exports of *source_path*.

    Pitch shift is applied once before tempo processing.
    Returns the list of written file paths.
    """
    source_path = Path(source_path)
    if not source_path.exists():
        raise FileNotFoundError(
            f"Source audio file does not exist: {source_path}"
        )

    export_dir = Path(export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)

    data, sample_rate = _load_audio(source_path)

    needs_pitch_shift = (
        original_freq > 0
        and target_freq > 0
        and abs(original_freq - target_freq) > 0.001
    )
    if needs_pitch_shift:
        data = pitch_shift_audio(data, sample_rate, original_freq, target_freq)

    created: list[Path] = []

    for factor in tempo_factors:
        filename = output_filename(
            track_name, factor, fmt=export_format, solo_level=solo_level
        )
        dest = export_dir / filename

        if dest.exists() and not overwrite:
            log.warning("Skipping existing file (overwrite=False): %s", dest)
            continue

        stretched = data if abs(factor - 1.0) < 1e-6 else stretch_audio(
            data, sample_rate, factor
        )

        _save_audio(dest, stretched, sample_rate, bitrate=mp3_bitrate)
        log.info("Exported %s", dest)
        created.append(dest)

    return created


# ---------------------------------------------------------------------------
# Utility kept for backwards compatibility
# ---------------------------------------------------------------------------

def bpm_to_seconds_per_beat(bpm: float) -> float:
    """Convert beats per minute to seconds per beat."""
    if bpm <= 0:
        raise ValueError("bpm must be positive")
    return 60.0 / bpm
