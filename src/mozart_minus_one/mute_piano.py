"""Select or create the no-piano accompaniment file."""

import logging
import shutil
from pathlib import Path

log = logging.getLogger(__name__)


def select_no_piano_stem(
    stems: dict[str, Path],
    export_path: Path,
    overwrite: bool = False,
) -> Path:
    """
    Copy the no_piano stem into the project export workflow.

    Parameters
    ----------
    stems:
        Dictionary with at least a ``no_piano`` key pointing to the
        stem file produced by separation.
    export_path:
        Destination path for the copied accompaniment file.
    overwrite:
        If False and the destination already exists, raise an error.
    """
    if "no_piano" not in stems:
        raise KeyError(
            "No 'no_piano' stem found in separation results. "
            "Available keys: " + str(list(stems.keys()))
        )

    source = Path(stems["no_piano"])
    if not source.exists():
        raise FileNotFoundError(
            f"No-piano stem file does not exist: {source}"
        )

    export_path = Path(export_path)
    export_path.parent.mkdir(parents=True, exist_ok=True)

    if export_path.exists() and not overwrite:
        raise FileExistsError(
            f"Accompaniment file already exists and overwrite=False: {export_path}"
        )

    shutil.copy2(source, export_path)
    log.info("Accompaniment file written: %s", export_path)
    return export_path


def get_accompaniment_path(
    stems: dict[str, Path],
    separated_dir: Path,
    track_name: str,
    overwrite: bool = False,
) -> Path:
    """
    Return a stable path for the no-piano accompaniment inside the
    project's separated directory.
    """
    dest = Path(separated_dir) / f"{track_name}_no_piano.wav"
    return select_no_piano_stem(stems, dest, overwrite=overwrite)
