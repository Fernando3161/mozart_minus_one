# SPECS.md

## Project Name

`mozart-minus-one`

## Project Objective

Create a local Python-based tool that generates practice accompaniment files from an audio recording of a Mozart piano concerto by:

1. Removing or blending the piano part to a configurable level.
2. Optionally correcting the tuning to a target reference frequency.
3. Exporting multiple tempo versions as MP3 files while preserving pitch.

The system is designed for private piano practice.

## Input

The system shall accept one audio file as input.

Supported baseline formats: `.wav`, `.mp3`, `.flac`, `.m4a`.

The input file shall be placed in:

```text
data/raw/
```

## Output

The system shall produce practice audio files in MP3 format in:

```text
data/exports/
```

Required output files when `solo_level=0`:

```text
<track_name>_no_piano_100.mp3
<track_name>_no_piano_95.mp3
<track_name>_no_piano_90.mp3
<track_name>_no_piano_85.mp3
```

Required output files when `solo_level>0` (example `solo_level=20`):

```text
<track_name>_piano20pct_100.mp3
<track_name>_piano20pct_95.mp3
<track_name>_piano20pct_90.mp3
<track_name>_piano20pct_85.mp3
```

## Intermediate Output

Separated stems and accompaniment WAV files shall be saved in:

```text
data/separated/
```

Expected intermediate files:

```text
data/separated/htdemucs_6s/<track>/piano.wav
data/separated/htdemucs_6s/<track>/no_piano.wav
data/separated/<track>_no_piano.wav          (solo_level=0)
data/separated/<track>_piano<N>pct.wav       (solo_level>0)
```

## Required Tempo Variants

| Label | Factor | Meaning |
|---|---:|---|
| 100 | 1.00 | Original speed |
| 95 | 0.95 | 95% speed |
| 90 | 0.90 | 90% speed |
| 85 | 0.85 | 85% speed |

Pitch shall remain unchanged across all variants.

## Functional Requirements

### FR-001: Input File Validation

The system shall check whether the selected input file exists before processing. If the file does not exist, the system shall stop with a clear error message.

### FR-002: Source Separation

The system shall run source separation using the Demucs Python API.

Baseline model: `htdemucs_6s`  
Target stem: `piano`

Stems are saved with soundfile to avoid the torchaudio/torchcodec dependency on Windows.

### FR-003: Accompaniment Creation

The system shall create an accompaniment file mixing the no-piano and piano stems:

```
accompaniment = no_piano + piano * (solo_level / 100)
```

| solo_level | Output |
|---|---|
| 0 | Piano completely removed |
| 1–99 | Piano blended at that percentage |
| 100 | Piano at full original volume |

The filename encodes the level:

- `solo_level=0` → `<track>_no_piano.wav`
- `solo_level=N` → `<track>_piano<N>pct.wav`

### FR-004: Pitch Correction

The system shall apply a pitch shift when `original_freq` and `target_freq` are configured and differ.

The shift in semitones is:

```
n_steps = 12 × log₂(target_freq / original_freq)
```

Preferred backend: `pyrubberband`  
Allowed fallback: `librosa.effects.pitch_shift`

Pitch correction is applied once before tempo processing. Tempo is not affected.

Example configuration:

```yaml
reference_note: e_b
original_freq: 314.0
target_freq: 311.13
```

Other examples:

```yaml
reference_note: a
original_freq: 448.0
target_freq: 440.0
```

```yaml
reference_note: d_s
original_freq: 314.0
target_freq: 311.0
```

Setting `original_freq: 0.0` or `target_freq: 0.0` disables pitch correction.

### FR-005: Tempo Adjustment

The system shall create pitch-preserving tempo-adjusted versions of the accompaniment.

Preferred backend: `pyrubberband`  
Allowed fallback: `librosa.effects.time_stretch`

### FR-006: MP3 Export

All final practice files shall be exported as MP3.

MP3 encoding uses `lameenc`. Bitrate is configurable (`mp3_bitrate`, default 192 kbps).

WAV intermediate files remain available for inspection.

### FR-007: Output Naming

Output filenames are deterministic:

```
<track_name>_no_piano_<speed>.mp3          (solo_level=0)
<track_name>_piano<N>pct_<speed>.mp3       (solo_level>0)
```

### FR-008: Output Folder Creation

The system shall create output folders automatically if they do not exist.

### FR-009: Logging

The system shall write a log file for each full pipeline run in `outputs/logs/`.

Log content: start time, input file, model, tempo variants, export format, bitrate, solo level, pitch parameters, created files, warnings, errors.

### FR-010: Configuration File

```text
configs/default.yaml
```

Required fields:

```yaml
input_file: data/raw/example.mp3
separation_model: htdemucs_6s
target_stem: piano
tempo_factors:
  - 1.00
  - 0.95
  - 0.90
  - 0.85
export_format: mp3
mp3_bitrate: 192
solo_level: 0
reference_note: e_b
original_freq: 314.0
target_freq: 311.13
overwrite: false
```

### FR-011: Command-Line Execution

```bash
python scripts/run_separation.py --config configs/default.yaml
python scripts/export_practice_versions.py --config configs/default.yaml
python scripts/full_pipeline.py --config configs/default.yaml
python scripts/full_pipeline.py --config configs/default.yaml --dry-run
```

### FR-012: Dry Run

Dry-run mode shall validate paths, print planned actions (including pitch correction and solo level), print expected MP3 output files, and write no audio files.

## Non-Functional Requirements

### NFR-001: Local Execution

No cloud service shall be required.

### NFR-002: Reproducibility

Same input file + same configuration → same output filenames and folder structure.

### NFR-003: Inspectability

Intermediate WAV files remain available for manual inspection.

### NFR-004: Practical Runtime

May take several minutes per track. Runtime optimization is secondary to correctness.

### NFR-005: Audio Quality

The project aims for practice usability, not professional production quality.

Acceptable issues: light piano ghosting, mild separation artifacts, slight reverb inconsistency.

Unacceptable issues: strong remaining piano dominating the accompaniment, broken orchestral continuity, severe distortion, pitch change in slowed versions, audible pitch correction artifacts, tempo instability.

### NFR-006: File Safety

The system shall not overwrite existing files unless `overwrite: true`.

### NFR-007: Git Hygiene

Large audio files and generated outputs shall not be committed by default.

## Proposed Project Structure

```text
mozart-minus-one/
├── AGENT.md
├── SPECS.md
├── ACCEPT_CRITERIA.md
├── README.md
├── pyproject.toml
├── requirements.txt
├── data/
│   ├── raw/
│   ├── separated/
│   └── exports/
├── src/
│   └── mozart_minus_one/
│       ├── __init__.py
│       ├── separate.py
│       ├── mute_piano.py
│       ├── tempo.py
│       └── pipeline.py
├── scripts/
│   ├── run_separation.py
│   ├── export_practice_versions.py
│   └── full_pipeline.py
├── configs/
│   └── default.yaml
├── tests/
│   ├── test_paths.py
│   ├── test_tempo.py
│   └── test_pipeline.py
└── outputs/
    ├── logs/
    └── reports/
```

## Expected Final Console Summary

```text
Pipeline completed.

Input:
  data/raw/mozart_pc_22_mov1.mp3

Created:
  data/exports/mozart_pc_22_mov1_no_piano_100.mp3
  data/exports/mozart_pc_22_mov1_no_piano_95.mp3
  data/exports/mozart_pc_22_mov1_no_piano_90.mp3
  data/exports/mozart_pc_22_mov1_no_piano_85.mp3

Log:
  outputs/logs/mozart_pc_22_mov1.log
```

## Legal and Usage Constraint

The tool is intended for private study and practice. Processed commercial recordings must not be redistributed.

## Future Extensions

- Batch processing.
- Manual stem quality rating.
- Section-based exports.
- Click-track generation.
- GUI or simple web interface.
