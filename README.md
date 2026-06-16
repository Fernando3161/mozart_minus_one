# Mozart Minus One

A local Python pipeline that takes an audio recording of a Mozart piano concerto,
removes or reduces the piano part using source separation, and exports pitch-preserved
practice versions at multiple speeds.

Intended for **private practice only**. Do not redistribute processed commercial recordings.

> **Note on piano separation quality:** `htdemucs_6s` is the only Demucs variant
> with a dedicated piano stem, but piano is empirically its weakest stem. Expect
> some bleed, especially in tutti passages where orchestra and soloist overlap.

---

## Pipeline

```
┌──────────────────────────┐
│   Raw Audio (MP3 / WAV)  │
└──────────────────────────┘
              │
              ▼
┌──────────────────────────┐
│    Source Separation     │  ← Demucs  (htdemucs_6s)
└──────────────────────────┘
         │          │
         ▼          ▼
     [piano]    [no_piano]
       stem        stem
         │          │
         └────┬─────┘
              │  no_piano + piano × (solo_level / 100)
              ▼
┌──────────────────────────┐
│    Accompaniment Mix     │
└──────────────────────────┘
              │
              │  (optional — if original_freq ≠ target_freq)
              ▼
┌──────────────────────────┐
│    Pitch Correction      │  ← original_freq → target_freq
└──────────────────────────┘
              │
              ▼
┌──────────────────────────┐
│     Tempo Variants       │  ← one file per factor in tempo_factors
└──────────────────────────┘
      │     │     │     │
      ▼     ▼     ▼     ▼
    100%   95%   90%   85%

         Practice Files
         (MP3 or WAV)
```

Interactive version: [docs/pipeline_flow.drawio](docs/pipeline_flow.drawio)

---

## Project layout

```
data/raw/               – place your source recording here
data/separated/         – Demucs stem output (piano.wav, no_piano.wav, …)
data/exports/           – final practice files
src/mozart_minus_one/
  separate.py           – Demucs subprocess wrapper
  mute_piano.py         – accompaniment blending (solo_level)
  tempo.py              – pitch-preserving time-stretch and MP3 export
  pipeline.py           – full orchestration
  cli.py                – console entry points
scripts/                – standalone stage scripts (require pip install -e .)
configs/
  default.yaml          – all tunable settings
docs/
  pipeline_flow.drawio  – editable pipeline diagram
tests/                  – pytest suite
outputs/logs/           – per-run log files
```

---

## External dependencies

These tools must be installed separately and accessible on your system PATH.

| Tool | Purpose | Install |
|---|---|---|
| **FFmpeg** | Audio decoding (MP3, FLAC, M4A) | [ffmpeg.org](https://ffmpeg.org/) |
| **Rubber Band** | High-quality pitch-preserving time-stretch | [breakfastquay.com/rubberband](https://breakfastquay.com/rubberband/) |

`pyrubberband` (the Python wrapper for Rubber Band) is listed as a dependency and
installed automatically. The `rubberband-cli` binary must be on PATH for it to work.
If it is absent the pipeline falls back automatically to `librosa.effects.time_stretch`.

---

## Environment setup

```bash
# Create the virtual environment (only once)
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install the package and all runtime dependencies
pip install -e .

# Install dev tools (pytest, ruff) as well
pip install -e ".[dev]"
```

---

## Place your recording

Copy your input file into `data/raw/`:

```bash
cp ~/Downloads/mozart_k488_mov1.mp3  data/raw/
```

Then update `configs/default.yaml`:

```yaml
input_file: data/raw/mozart_k488_mov1.mp3
```

---

## Running the pipeline

**Dry run** — validate config and print planned actions without writing any audio:

```bash
mozart-minus-one --dry-run
```

**Full pipeline** — separation → mix → tempo exports:

```bash
mozart-minus-one
```

**Individual stages:**

```bash
mozart-separate   # source separation only
mozart-export     # tempo exports from an existing separated file
```

All three commands accept `--config <path>` (default: `configs/default.yaml`).

---

## Configuration

Key settings in `configs/default.yaml`:

| Key | Default | Description |
|---|---|---|
| `input_file` | — | Path to the source recording |
| `separation_model` | `htdemucs_6s` | Demucs model |
| `solo_level` | `30` | Piano volume in the mix (0 = removed, 100 = full) |
| `tempo_factors` | `[1.0, 0.95, 0.90, 0.85]` | Speed variants to export |
| `export_format` | `mp3` | Output format (`mp3` or `wav`) |
| `mp3_bitrate` | `192` | MP3 bitrate in kbps |
| `original_freq` | `0.0` | Reference pitch of the recording (Hz); 0 skips pitch shift |
| `target_freq` | `0.0` | Target pitch (Hz) |
| `overwrite` | `true` | Overwrite existing output files |

---

## Expected outputs

With `solo_level: 30` (default) and `export_format: mp3`, a successful run produces:

```
data/exports/<track>_piano30pct_100.mp3   – original speed, piano at 30 %
data/exports/<track>_piano30pct_95.mp3    – 95 % speed, pitch preserved
data/exports/<track>_piano30pct_90.mp3    – 90 % speed, pitch preserved
data/exports/<track>_piano30pct_85.mp3    – 85 % speed, pitch preserved
```

With `solo_level: 0` the stem label changes to `_no_piano_`.

A log is written to `outputs/logs/<track>.log` for every full run.

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

This tool is intended exclusively for private study and practice. The source code is
released under the [MIT License](LICENSE). The license covers the code only — it grants
no rights to any audio recordings or musical compositions used as input. Users are
solely responsible for ensuring they have the appropriate rights to any material
they process.
