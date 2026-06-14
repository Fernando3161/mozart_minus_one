"""Tempo adjustment utilities – pitch-preserving time-stretch."""

import logging
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf

log = logging.getLogger(__name__)


def _load_audio(path: Path) -> tuple[np.ndarray, int]:
    """Load audio from a WAV file, preserving channel layout."""
    data, sample_rate = sf.read(str(path), always_2d=False)
    return data, sample_rate


def _save_audio(path: Path, data: np.ndarray, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), data, sample_rate, subtype="PCM_16")


def _stretch_pyrubberband(
    data: np.ndarray, sample_rate: int, tempo_factor: float
) -> np.ndarray:
    import pyrubberband

    if data.ndim == 1:
        return pyrubberband.time_stretch(data, sample_rate, tempo_factor)
    channels = []
    for ch in range(data.shape[1]):
        channels.append(
            pyrubberband.time_stretch(data[:, ch], sample_rate, tempo_factor)
        )
    return np.stack(channels, axis=1)


def _stretch_librosa(
    data: np.ndarray, sample_rate: int, tempo_factor: float
) -> np.ndarray:
    import librosa

    rate = tempo_factor  # librosa rate < 1 → slower, same convention as tempo_factor

    if data.ndim == 1:
        mono = data.astype(np.float32)
        stretched = librosa.effects.time_stretch(mono, rate=rate)
        return stretched

    channels = []
    for ch in range(data.shape[1]):
        mono = data[:, ch].astype(np.float32)
        channels.append(librosa.effects.time_stretch(mono, rate=rate))
    return np.stack(channels, axis=1)


def stretch_audio(
    data: np.ndarray,
    sample_rate: int,
    tempo_factor: float,
) -> np.ndarray:
    """
    Time-stretch *data* by *tempo_factor* while preserving pitch.

    A factor of 0.9 makes the audio play at 90 % speed (slower).
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
            "pyrubberband unavailable (%s); falling back to librosa.",
            pyrb_err,
        )

    return _stretch_librosa(data, sample_rate, tempo_factor)


def export_tempo_variants(
    source_path: Path,
    export_dir: Path,
    track_name: str,
    tempo_factors: list[float],
    export_format: str = "wav",
    overwrite: bool = False,
) -> list[Path]:
    """
    Create tempo-adjusted copies of *source_path*.

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
    created: list[Path] = []

    for factor in tempo_factors:
        label = int(round(factor * 100))
        filename = f"{track_name}_no_piano_{label}.{export_format}"
        dest = export_dir / filename

        if dest.exists() and not overwrite:
            log.warning("Skipping existing file (overwrite=False): %s", dest)
            continue

        if abs(factor - 1.0) < 1e-6:
            stretched = data
        else:
            stretched = stretch_audio(data, sample_rate, factor)

        _save_audio(dest, stretched, sample_rate)
        log.info("Exported %s", dest)
        created.append(dest)

    return created


def output_filename(track_name: str, factor: float, fmt: str = "wav") -> str:
    """Return the deterministic output filename for a given tempo factor."""
    label = int(round(factor * 100))
    return f"{track_name}_no_piano_{label}.{fmt}"


def bpm_to_seconds_per_beat(bpm: float) -> float:
    """Convert beats per minute to seconds per beat."""
    if bpm <= 0:
        raise ValueError("bpm must be positive")
    return 60.0 / bpm
