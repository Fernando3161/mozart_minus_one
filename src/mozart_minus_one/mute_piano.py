"""Select or create the accompaniment file with configurable piano level."""

import logging
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf

log = logging.getLogger(__name__)


def create_accompaniment(
    stems: dict[str, Path],
    export_path: Path,
    solo_level: int = 0,
    overwrite: bool = False,
) -> Path:
    """
    Create the accompaniment file: ``no_piano + piano * (solo_level / 100)``.

    Parameters
    ----------
    stems:
        Dictionary with at least a ``no_piano`` key (and a ``piano`` key when
        *solo_level* > 0) pointing to the WAV files produced by separation.
    export_path:
        Destination path for the mixed accompaniment file.
    solo_level:
        Piano volume as a percentage of the original level.
        ``0`` = piano completely removed.
        ``100`` = piano at full original volume (separation bypassed).
        Values between 0 and 100 blend the piano back gradually.
    overwrite:
        If ``False`` and the destination already exists, raise ``FileExistsError``.
    """
    if not (0 <= solo_level <= 100):
        raise ValueError(
            f"solo_level must be between 0 and 100, got {solo_level}"
        )

    if "no_piano" not in stems:
        raise KeyError(
            "No 'no_piano' stem found in separation results. "
            "Available keys: " + str(list(stems.keys()))
        )

    no_piano_path = Path(stems["no_piano"])
    if not no_piano_path.exists():
        raise FileNotFoundError(
            f"No-piano stem file does not exist: {no_piano_path}"
        )

    export_path = Path(export_path)
    export_path.parent.mkdir(parents=True, exist_ok=True)

    if export_path.exists() and not overwrite:
        raise FileExistsError(
            f"Accompaniment file already exists and overwrite=False: {export_path}"
        )

    if solo_level == 0:
        shutil.copy2(no_piano_path, export_path)
    else:
        if "piano" not in stems:
            raise KeyError(
                "Piano stem required for solo_level > 0 but not found. "
                "Available keys: " + str(list(stems.keys()))
            )
        piano_path = Path(stems["piano"])
        if not piano_path.exists():
            raise FileNotFoundError(
                f"Piano stem file does not exist: {piano_path}"
            )

        no_piano_data, sr = sf.read(str(no_piano_path), always_2d=True)
        piano_data, sr_p = sf.read(str(piano_path), always_2d=True)

        if sr != sr_p:
            raise ValueError(
                f"Sample rate mismatch: no_piano={sr} Hz, piano={sr_p} Hz"
            )

        mix = no_piano_data + piano_data * (solo_level / 100.0)
        mix = np.clip(mix, -1.0, 1.0)
        sf.write(str(export_path), mix, sr, subtype="PCM_24")

    log.info(
        "Accompaniment written: %s  (solo_level=%d%%)", export_path, solo_level
    )
    return export_path


def get_accompaniment_path(
    stems: dict[str, Path],
    separated_dir: Path,
    track_name: str,
    solo_level: int = 0,
    overwrite: bool = False,
) -> Path:
    """
    Return a stable WAV path for the accompaniment inside the separated directory.

    The filename encodes the solo level so reruns with different levels
    do not collide:

    * ``solo_level=0``  -> ``<track>_no_piano.wav``
    * ``solo_level=20`` -> ``<track>_piano20pct.wav``
    """
    if solo_level == 0:
        filename = f"{track_name}_no_piano.wav"
    else:
        filename = f"{track_name}_piano{solo_level}pct.wav"

    dest = Path(separated_dir) / filename
    return create_accompaniment(
        stems, dest, solo_level=solo_level, overwrite=overwrite
    )
