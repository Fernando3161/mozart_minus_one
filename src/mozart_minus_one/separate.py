"""Audio stem separation via Demucs Python API."""

import logging
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}


def validate_input(audio_path: Path) -> Path:
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(
            f"Input file does not exist: {audio_path}"
        )
    if not audio_path.is_file():
        raise ValueError(f"Input path is not a file: {audio_path}")
    if audio_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio format '{audio_path.suffix}'. "
            f"Supported formats: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    return audio_path


def _load_audio_for_demucs(audio_path: Path, target_sr: int) -> "np.ndarray":
    """
    Load audio as a float32 stereo numpy array at target_sr.

    Uses librosa so that MP3, FLAC, and WAV all load without needing
    torchaudio to save (torchaudio ≥ 2.10 requires torchcodec for saving,
    but loading still works via its ffmpeg/soundfile path).
    """
    import librosa

    data, sr = librosa.load(str(audio_path), sr=None, mono=False)

    if data.ndim == 1:
        data = np.stack([data, data], axis=0)
    elif data.shape[0] > 2:
        data = data[:2]

    if sr != target_sr:
        log.info("Resampling from %d Hz to %d Hz", sr, target_sr)
        data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)

    return data.astype(np.float32)


def run_demucs(
    audio_path: Path,
    output_dir: Path,
    model: str = "htdemucs_6s",
    two_stems: str = "piano",
) -> None:
    """
    Run Demucs source separation using the Python API.

    Saves stems with soundfile instead of torchaudio.save so that
    the torchcodec / full-shared FFmpeg dependency is not required.
    """
    try:
        import torch
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
    except ImportError as exc:
        raise RuntimeError(
            f"Demucs is not installed or could not be imported: {exc}. "
            "Run: pip install demucs"
        ) from exc

    stem_dir = Path(output_dir) / model / Path(audio_path).stem
    stem_dir.mkdir(parents=True, exist_ok=True)

    log.info("Loading Demucs model: %s", model)
    demucs_model = get_model(model)
    demucs_model.eval()

    target_sr: int = demucs_model.samplerate
    log.info("Model sample rate: %d Hz", target_sr)

    log.info("Loading audio: %s", audio_path)
    audio_data = _load_audio_for_demucs(audio_path, target_sr)

    mix = torch.tensor(audio_data, dtype=torch.float32).unsqueeze(0)

    log.info("Running separation (this may take several minutes)...")
    with torch.no_grad():
        sources = apply_model(demucs_model, mix, progress=True)[0]

    stem_idx = demucs_model.sources.index(two_stems)

    piano_tensor = sources[stem_idx]
    other_indices = [i for i in range(len(demucs_model.sources)) if i != stem_idx]
    no_piano_tensor = sum(sources[i] for i in other_indices)

    piano_path = stem_dir / f"{two_stems}.wav"
    no_piano_path = stem_dir / f"no_{two_stems}.wav"

    sf.write(str(piano_path), piano_tensor.numpy().T, target_sr, subtype="PCM_24")
    log.info("Saved piano stem: %s", piano_path)

    sf.write(str(no_piano_path), no_piano_tensor.numpy().T, target_sr, subtype="PCM_24")
    log.info("Saved no-piano stem: %s", no_piano_path)


def locate_stems(
    audio_path: Path,
    output_dir: Path,
    model: str = "htdemucs_6s",
) -> dict[str, Path]:
    """
    Locate the piano and no_piano stems produced by separation.

    Stems live at:
        <output_dir>/<model>/<track_name>/piano.wav
        <output_dir>/<model>/<track_name>/no_piano.wav
    """
    track_name = Path(audio_path).stem
    stem_dir = Path(output_dir) / model / track_name

    piano_path = stem_dir / "piano.wav"
    no_piano_path = stem_dir / "no_piano.wav"

    missing = []
    if not piano_path.exists():
        missing.append(str(piano_path))
    if not no_piano_path.exists():
        missing.append(str(no_piano_path))

    if missing:
        raise FileNotFoundError(
            "Expected stems not found after separation:\n  "
            + "\n  ".join(missing)
        )

    log.info("Piano stem: %s", piano_path)
    log.info("No-piano stem: %s", no_piano_path)

    return {"piano": piano_path, "no_piano": no_piano_path}


def separate_audio(
    audio_path: Path,
    output_dir: Path,
    model: str = "htdemucs_6s",
    target_stem: str = "piano",
) -> dict[str, Path]:
    """Validate input, run Demucs, and return stem paths."""
    audio_path = validate_input(Path(audio_path))
    run_demucs(audio_path, output_dir, model=model, two_stems=target_stem)
    return locate_stems(audio_path, output_dir, model=model)
