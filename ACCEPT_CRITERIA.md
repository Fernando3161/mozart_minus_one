# ACCEPT_CRITERIA.md

## Acceptance Criteria

This document defines the minimum conditions that must be met for the `mozart-minus-one` project to be considered functional.

The project is accepted when it can generate pitch-preserved, pitch-corrected, and slowed no-piano or mixed-piano practice files from an input recording, exported as MP3, through a reproducible local Python workflow.

## AC-001: Project Structure Exists

The repository shall contain the following files:

```text
AGENT.md
SPECS.md
ACCEPT_CRITERIA.md
README.md
pyproject.toml
requirements.txt
```

The repository shall contain the following folders:

```text
data/raw/
data/separated/
data/exports/
src/mozart_minus_one/
scripts/
configs/
tests/
outputs/logs/
outputs/reports/
```

## AC-002: Configuration File Exists

The project shall contain:

```text
configs/default.yaml
```

The configuration file shall define at least:

```yaml
input_file:
separation_model:
target_stem:
tempo_factors:
export_format: mp3
mp3_bitrate:
solo_level:
reference_note:
original_freq:
target_freq:
overwrite:
```

Acceptance check:

```bash
python scripts/full_pipeline.py --config configs/default.yaml --dry-run
```

Expected result:

- The command runs without crashing.
- The command prints the planned input file, tempo variants, format, solo level, and pitch parameters.
- The command does not create audio files.

## AC-003: Input Validation Works

When the configured input file does not exist, the pipeline shall stop with a clear error.

Expected result:

- The command fails.
- The error message mentions that the input file does not exist.
- No output audio file is created.

## AC-004: Separation Command Can Run

Given a valid audio file in `data/raw/`, the separation script shall run without Python import errors.

Expected result:

- The script starts source separation.
- The selected model is printed or logged.
- Intermediate files are created in `data/separated/`.
- If Demucs is missing, the error message clearly identifies the missing dependency.

## AC-005: No-Piano Stem Is Found or Created

After source separation, the pipeline shall locate or create an accompaniment file based on `solo_level`.

Expected valid result:

```text
<track_name>_no_piano.wav          (solo_level=0)
<track_name>_piano<N>pct.wav       (solo_level>0)
```

Failure condition:

- The system silently continues without a valid accompaniment file.

## AC-006: MP3 Export at 100% Speed Exists

The pipeline shall export a baseline no-piano (or mixed) file at original speed as MP3.

Expected file pattern:

```text
data/exports/<track_name>_no_piano_100.mp3
```

Acceptance check:

```bash
python scripts/full_pipeline.py --config configs/default.yaml
```

Expected result:

- The file exists and is a valid MP3.
- The file has the same pitch and approximate duration as the source accompaniment.

## AC-007: MP3 Export at 95% Speed Exists

Expected file: `data/exports/<track_name>_no_piano_95.mp3`

Expected result:

- The file exists and is a valid MP3.
- Pitch is preserved.
- Duration is approximately `original_duration / 0.95` (±2%).

## AC-008: MP3 Export at 90% Speed Exists

Expected file: `data/exports/<track_name>_no_piano_90.mp3`

Expected result:

- The file exists and is a valid MP3.
- Pitch is preserved.
- Duration is approximately `original_duration / 0.90` (±2%).

## AC-009: MP3 Export at 85% Speed Exists

Expected file: `data/exports/<track_name>_no_piano_85.mp3`

Expected result:

- The file exists and is a valid MP3.
- Pitch is preserved.
- Duration is approximately `original_duration / 0.85` (±2%).

## AC-010: Output Naming Is Deterministic

Given the same input filename and configuration, the same output filenames shall be produced every time.

Acceptance check:

1. Run dry-run twice.
2. Compare the listed expected output files.

Expected result: the expected output filenames are identical.

## AC-011: No Silent Overwrite

If an output file already exists and `overwrite: false`, the pipeline shall not overwrite it.

Expected result:

- Existing files are preserved.
- The system prints or logs a clear warning.

## AC-012: Explicit Overwrite Works

If `overwrite: true`, the pipeline may overwrite existing generated files.

Expected result:

- The second run completes and logs that existing files were replaced.

## AC-013: Log File Is Created

Each full pipeline run shall create a log file in `outputs/logs/`.

Expected log content: input file, model, tempo factors, format, solo level, pitch parameters, created files, and any errors.

## AC-014: Tests Can Run

```bash
pytest
```

Expected result:

- Tests execute without import errors.
- Path handling tests pass.
- Tempo factor and MP3 export tests pass.
- Pitch shift tests pass.
- Solo level mixing tests pass.
- Pipeline dry-run tests pass.

## AC-015: Tempo Function Is Testable Without Demucs

The tempo export functionality shall be testable independently from source separation using a synthetic short WAV file.

## AC-016: Missing External Dependency Gives Clear Error

If an external dependency is missing (demucs, ffmpeg), the error shall identify the dependency and the failed stage.

## AC-017: Final Summary Is Printed

After a successful full pipeline run, the system shall print:

```text
Pipeline completed.

Input:
  data/raw/example.mp3

Created:
  data/exports/example_no_piano_100.mp3
  data/exports/example_no_piano_95.mp3
  data/exports/example_no_piano_90.mp3
  data/exports/example_no_piano_85.mp3

Log:
  outputs/logs/example.log
```

## AC-018: Practical Audio Review

The result is accepted for practice if:

- The piano part is clearly reduced (or mixed to the configured level).
- The orchestra remains recognizable.
- The slowed versions keep the same pitch.
- Any pitch correction shifts the tuning cleanly without audible artifacts.
- The tempo change is stable.

## AC-019: Private Practice Constraint

The documentation states that processed commercial recordings shall not be redistributed.

## AC-020: MP3 Is the Required Output Format

All exported practice files shall be in MP3 format.

Acceptance check:

- Run the full pipeline.
- Confirm all files in `data/exports/` end in `.mp3`.
- Confirm each file is non-empty and playable.

Expected result:

- `data/exports/<track_name>_no_piano_100.mp3` (or `_piano<N>pct_100.mp3`) exists.
- Files are readable as MP3 audio.

## AC-021: Pitch Correction Is Applied When Configured

When `original_freq` and `target_freq` are set and differ, the pipeline shall apply a pitch shift so that the reference note sounds at the target frequency.

Acceptance check:

1. Set `reference_note: e_b`, `original_freq: 314.0`, `target_freq: 311.13`.
2. Run the full pipeline.

Expected result:

- The exported files have their tuning shifted by `12 * log2(311.13 / 314.0)` semitones.
- Tempo is unchanged.
- Duration is unchanged.

Acceptance check (no shift):

- Set `original_freq: 0.0` and `target_freq: 0.0` (or identical values).
- Confirm no pitch processing is applied and files are created as usual.

## AC-022: Solo Level Controls Piano Volume

The `solo_level` parameter shall blend the piano back into the accompaniment.

| solo_level | Behavior |
|---|---|
| 0 | Piano completely removed (standard practice track) |
| 20 | Piano at 20% volume |
| 100 | Piano at original volume |

Acceptance check:

1. Set `solo_level: 0` – output filename contains `_no_piano_`.
2. Set `solo_level: 20` – output filename contains `_piano20pct_`.
3. Confirm that the accompaniment file in `data/separated/` changes accordingly.

Expected result:

- Filename encodes the solo level deterministically.
- The audio mix reflects the configured piano level.

## Minimum Done Definition

The project reaches minimum done status when:

1. A valid input recording can be processed.
2. An accompaniment file is exported at the configured solo level.
3. Pitch correction is applied when `original_freq` and `target_freq` are configured.
4. Tempo versions at 100, 95, 90, and 85 percent are created as MP3 files.
5. The pitch is preserved across all tempo variants.
6. All files are saved in `data/exports/`.
7. A log file is created in `outputs/logs/`.
8. `pytest` runs without import errors.
9. The result is usable for practice, even if imperfect.
