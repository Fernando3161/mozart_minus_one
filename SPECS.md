# SPECS.md

## Project Name

`mozart-minus-one`

## Project Objective

Create a local Python-based tool that generates practice accompaniment files from an audio recording of a Mozart piano concerto by removing or reducing the piano part and exporting multiple tempo versions.

The system is designed for private piano practice.

## Problem Statement

Good MIDI files or clean orchestral backing tracks for Mozart piano concertos are not always available. The project explores an alternative workflow:

1. Use an existing recording.
2. Separate the piano from the orchestra.
3. Export a no-piano or reduced-piano version.
4. Generate slower versions for practice.

The result does not need to be perfect. It must be useful enough for practice.

## Input

The system shall accept one audio file as input.

Supported baseline formats:

- `.wav`
- `.mp3`
- `.flac`
- `.m4a`, if FFmpeg support is available

The input file shall be placed in:

```text
data/raw/
```

Example:

```text
data/raw/mozart_k488_movement_1.mp3
```

## Output

The system shall produce practice audio files in:

```text
data/exports/
```

Required output files:

```text
<track_name>_no_piano_100.wav
<track_name>_no_piano_95.wav
<track_name>_no_piano_90.wav
<track_name>_no_piano_85.wav
```

Optional later output:

```text
<track_name>_no_piano_100.mp3
<track_name>_no_piano_95.mp3
<track_name>_no_piano_90.mp3
<track_name>_no_piano_85.mp3
```

## Intermediate Output

Separated stems shall be saved in:

```text
data/separated/
```

Expected intermediate files may include:

```text
piano.wav
no_piano.wav
```

The exact folder structure may depend on the separation tool, but the project shall normalize the final paths internally.

## Required Tempo Variants

The default tempo variants are:

| Label | Tempo factor | Meaning |
|---|---:|---|
| 100 | 1.00 | Original speed |
| 95 | 0.95 | 95 percent speed |
| 90 | 0.90 | 90 percent speed |
| 85 | 0.85 | 85 percent speed |

Pitch shall remain unchanged.

## Functional Requirements

### FR-001: Input File Validation

The system shall check whether the selected input file exists before processing.

If the file does not exist, the system shall stop and provide a clear error message.

### FR-002: Source Separation

The system shall run a source separation process capable of extracting a piano stem.

The baseline separation backend shall be Demucs.

The baseline model shall be:

```text
htdemucs_6s
```

The baseline target stem shall be:

```text
piano
```

### FR-003: No-Piano Export

The system shall create or select a no-piano accompaniment file.

Preferred behavior:

1. Use the `no_piano.wav` file produced by the separation backend.
2. If not available, combine available non-piano stems when possible.
3. If no valid accompaniment can be created, fail with a clear error.

### FR-004: Tempo Adjustment

The system shall create tempo-adjusted versions of the no-piano file.

Tempo adjustment shall preserve pitch.

Preferred backend:

```text
pyrubberband
```

Allowed fallback:

```text
librosa.effects.time_stretch
```

### FR-005: Output Naming

The system shall use deterministic output names.

Example:

```text
mozart_k488_movement_1_no_piano_90.wav
```

### FR-006: Output Folder Creation

The system shall create output folders automatically if they do not exist.

### FR-007: Logging

The system shall write a log file for each full pipeline run.

Log files shall be saved in:

```text
outputs/logs/
```

The log shall include:

- Start time.
- Input file.
- Separation model.
- Tempo variants.
- Created files.
- Warnings.
- Errors.

### FR-008: Configuration File

The system shall read default settings from:

```text
configs/default.yaml
```

Required configuration fields:

```yaml
input_file: data/raw/example.mp3
separation_model: htdemucs_6s
target_stem: piano
tempo_factors:
  - 1.00
  - 0.95
  - 0.90
  - 0.85
export_format: wav
overwrite: false
```

### FR-009: Command-Line Execution

The system shall provide script-level execution through:

```bash
python scripts/run_separation.py
python scripts/export_practice_versions.py
python scripts/full_pipeline.py
```

At least the full pipeline shall accept a configuration file argument:

```bash
python scripts/full_pipeline.py --config configs/default.yaml
```

### FR-010: Dry Run

The full pipeline shall support a dry-run mode.

Dry-run mode shall:

- Validate paths.
- Print planned actions.
- Print expected output files.
- Not run source separation.
- Not write audio output files.

Example:

```bash
python scripts/full_pipeline.py --config configs/default.yaml --dry-run
```

## Non-Functional Requirements

### NFR-001: Local Execution

The project shall run locally.

No cloud service shall be required.

### NFR-002: Reproducibility

Given the same input file and configuration, the system shall create the same output filenames and folder structure.

### NFR-003: Inspectability

Intermediate files shall remain available for manual inspection.

### NFR-004: Practical Runtime

The project may take several minutes per track depending on hardware.

Runtime optimization is secondary to correctness and reproducibility.

### NFR-005: Audio Quality

The project shall aim for practice usability, not professional production quality.

Acceptable issues:

- Light piano ghosting.
- Mild separation artifacts.
- Slight reverb inconsistency.

Unacceptable issues:

- Strong remaining piano dominating the accompaniment.
- Broken orchestral continuity.
- Severe distortion.
- Pitch change in slowed versions.
- Tempo instability caused by processing.

### NFR-006: File Safety

The system shall not overwrite existing files unless `overwrite: true` is set in the configuration.

### NFR-007: Git Hygiene

Large audio files and generated outputs shall not be committed by default.

Recommended `.gitignore` entries:

```gitignore
data/raw/*
data/separated/*
data/exports/*
outputs/logs/*
outputs/reports/*
```

Optionally preserve folder structure using `.gitkeep` files.

## Proposed Project Structure

```text
mozart-minus-one/
├── AGENT.md
├── SPECS.md
├── ACEPT_CRITERIA.md
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

## Suggested Dependencies

Minimum Python dependencies:

```text
demucs
soundfile
numpy
pyyaml
pyrubberband
librosa
pytest
```

External system dependencies:

```text
ffmpeg
rubberband
```

`rubberband` is only required if `pyrubberband` is used.

## Main Pipeline Behavior

The full pipeline shall perform the following steps:

1. Load configuration.
2. Validate input file.
3. Create required folders.
4. Run source separation.
5. Locate piano and no-piano stems.
6. Export the 100 percent no-piano version.
7. Generate 95 percent version.
8. Generate 90 percent version.
9. Generate 85 percent version.
10. Save logs.
11. Print a final summary.

## Expected Final Console Summary

Example:

```text
Pipeline completed.

Input:
  data/raw/mozart_k488_movement_1.mp3

Created:
  data/exports/mozart_k488_movement_1_no_piano_100.wav
  data/exports/mozart_k488_movement_1_no_piano_95.wav
  data/exports/mozart_k488_movement_1_no_piano_90.wav
  data/exports/mozart_k488_movement_1_no_piano_85.wav

Log:
  outputs/logs/mozart_k488_movement_1.log
```

## Legal and Usage Constraint

The tool is intended for private study and practice.

The project shall not encourage redistribution of processed commercial recordings.

## Future Extensions

Possible later features:

- MP3 export.
- Batch processing.
- Manual stem quality rating.
- Graphical waveform comparison.
- Section-based exports.
- Click-track generation.
- Score-aligned practice markers.
- GUI or simple web interface.
