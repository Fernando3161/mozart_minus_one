# Mozart Minus One

A local Python pipeline that takes an audio recording of a Mozart piano concerto,
removes or reduces the piano part using source separation, and exports pitch-preserved
practice versions at 100%, 95%, 90%, and 85% speed.

Intended for **private practice only**. Do not redistribute processed commercial recordings.

---

## Project layout

```
data/raw/           – place your source recording here
data/separated/     – Demucs stem output (piano.wav, no_piano.wav)
data/exports/       – final practice files
src/mozart_minus_one/
  separate.py       – Demucs subprocess wrapper
  mute_piano.py     – no-piano stem selection
  tempo.py          – pitch-preserving time-stretch
  pipeline.py       – full orchestration
scripts/
  run_separation.py
  export_practice_versions.py
  full_pipeline.py
configs/
  default.yaml      – all tunable settings
tests/              – pytest suite
outputs/logs/       – per-run log files
```

---

## External dependencies

These tools must be installed separately and accessible on your system PATH.

| Tool | Purpose | Install |
|---|---|---|
| **FFmpeg** | Audio decoding (MP3, FLAC, M4A) | [ffmpeg.org](https://ffmpeg.org/) |
| **Rubber Band** | High-quality pitch-preserving time-stretch | [breakfastquay.com/rubberband](https://breakfastquay.com/rubberband/) |

`pyrubberband` (the Python wrapper for Rubber Band) is already listed in
`requirements.txt`. The `rubberband-cli` binary must be on PATH for it to work.
If it is absent the pipeline falls back automatically to `librosa.effects.time_stretch`.

---

## Environment setup

```bash
# Create the virtual environment (only once)
python -m venv .env

# Activate it
# Windows:
.env\Scripts\activate
# macOS / Linux:
source .env/bin/activate

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Install the project in editable mode
python -m pip install -e .
```

---

## Place your recording

Copy your input file into `data/raw/`:

```bash
# Example
cp ~/Downloads/mozart_k488_mov1.mp3  data/raw/
```

Then update `configs/default.yaml`:

```yaml
input_file: data/raw/mozart_k488_mov1.mp3
```

---

## Dry-run (no audio files written)

Validates configuration and prints planned actions without running separation
or writing any audio:

```bash
python scripts/full_pipeline.py --config configs/default.yaml --dry-run
```

---

## Full pipeline

```bash
python scripts/full_pipeline.py --config configs/default.yaml
```

---

## Individual stages

Run only source separation:

```bash
python scripts/run_separation.py --config configs/default.yaml
```

Export tempo variants from an existing no-piano file:

```bash
python scripts/export_practice_versions.py --config configs/default.yaml
```

---

## Expected outputs

After a successful run you will find four practice files in `data/exports/`:

```
<track_name>_no_piano_100.wav   – original speed, no piano
<track_name>_no_piano_95.wav    – 95% speed, pitch preserved
<track_name>_no_piano_90.wav    – 90% speed, pitch preserved
<track_name>_no_piano_85.wav    – 85% speed, pitch preserved
```

A log file is written to `outputs/logs/<track_name>.log` for every full run.

---

## Running tests

```bash
pytest
```

The test suite verifies path handling, output filename generation, configuration
loading, dry-run behavior, and tempo export using a synthetic WAV file. It does
not require Demucs or a real recording.

---

## Legal notice

This tool is intended exclusively for private study and practice. Processed
derivatives of commercial recordings must not be redistributed.
