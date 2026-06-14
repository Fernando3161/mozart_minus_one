# ACCEPT_CRITERIA.md

## Acceptance Criteria

This document defines the minimum conditions that must be met for the `mozart-minus-one` project to be considered functional.

The project is accepted when it can generate pitch-preserved, slowed no-piano practice files from an input recording through a reproducible local Python workflow.

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

Acceptance check:

```bash
python -c "from pathlib import Path; required=['AGENT.md','SPECS.md','ACEPT_CRITERIA.md','data/raw','data/separated','data/exports','src/mozart_minus_one','scripts','configs','tests','outputs/logs','outputs/reports']; missing=[p for p in required if not Path(p).exists()]; assert not missing, missing"
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
export_format:
overwrite:
```

Acceptance check:

```bash
python scripts/full_pipeline.py --config configs/default.yaml --dry-run
```

Expected result:

- The command runs without crashing.
- The command prints the planned input file.
- The command prints the planned tempo variants.
- The command does not create audio files.

## AC-003: Input Validation Works

When the configured input file does not exist, the pipeline shall stop with a clear error.

Acceptance check:

1. Set `input_file` to a non-existing file.
2. Run:

```bash
python scripts/full_pipeline.py --config configs/default.yaml
```

Expected result:

- The command fails.
- The error message mentions that the input file does not exist.
- No output audio file is created.

## AC-004: Separation Command Can Run

Given a valid audio file in:

```text
data/raw/
```

the separation script shall run without Python import errors.

Acceptance check:

```bash
python scripts/run_separation.py --config configs/default.yaml
```

Expected result:

- The script starts source separation.
- The selected model is printed or logged.
- Intermediate files are created in `data/separated/` or in the configured separation folder.
- If Demucs or FFmpeg is missing, the error message clearly says which dependency is missing.

## AC-005: No-Piano Stem Is Found or Created

After source separation, the pipeline shall locate or create a no-piano accompaniment file.

Expected valid result:

```text
no_piano.wav
```

or a normalized project output equivalent.

Acceptance check:

- Run the separation stage.
- Confirm that the pipeline identifies a valid no-piano file.
- Confirm that the file path is printed or logged.

Failure condition:

- The system silently continues without a valid no-piano file.

## AC-006: 100 Percent Export Exists

The pipeline shall export a baseline no-piano file at original speed.

Expected file pattern:

```text
data/exports/<track_name>_no_piano_100.wav
```

Acceptance check:

```bash
python scripts/full_pipeline.py --config configs/default.yaml
```

Expected result:

- The file exists.
- The file is readable as audio.
- The file has the same pitch and approximate duration as the no-piano intermediate file.

## AC-007: 95 Percent Export Exists

The pipeline shall export a no-piano practice file at 95 percent speed.

Expected file pattern:

```text
data/exports/<track_name>_no_piano_95.wav
```

Expected result:

- The file exists.
- The file is readable as audio.
- The pitch is preserved.
- The duration is approximately `original_duration / 0.95`.

Tolerance:

```text
± 2 percent
```

## AC-008: 90 Percent Export Exists

The pipeline shall export a no-piano practice file at 90 percent speed.

Expected file pattern:

```text
data/exports/<track_name>_no_piano_90.wav
```

Expected result:

- The file exists.
- The file is readable as audio.
- The pitch is preserved.
- The duration is approximately `original_duration / 0.90`.

Tolerance:

```text
± 2 percent
```

## AC-009: 85 Percent Export Exists

The pipeline shall export a no-piano practice file at 85 percent speed.

Expected file pattern:

```text
data/exports/<track_name>_no_piano_85.wav
```

Expected result:

- The file exists.
- The file is readable as audio.
- The pitch is preserved.
- The duration is approximately `original_duration / 0.85`.

Tolerance:

```text
± 2 percent
```

## AC-010: Output Naming Is Deterministic

Given the same input filename and configuration, the same output filenames shall be produced every time.

Acceptance check:

1. Run dry-run twice.
2. Compare the listed expected output files.

Expected result:

- The expected output filenames are identical.

## AC-011: No Silent Overwrite

If an output file already exists and `overwrite: false`, the pipeline shall not overwrite it.

Acceptance check:

1. Run the pipeline once.
2. Run the pipeline again with the same configuration and `overwrite: false`.

Expected result:

- Existing files are preserved.
- The system prints or logs a clear warning or error.

## AC-012: Explicit Overwrite Works

If `overwrite: true`, the pipeline may overwrite existing generated files.

Acceptance check:

1. Set `overwrite: true`.
2. Run the pipeline twice.

Expected result:

- The second run completes.
- The logs clearly indicate that existing files were overwritten or replaced.

## AC-013: Log File Is Created

Each full pipeline run shall create a log file in:

```text
outputs/logs/
```

Expected log content:

- Input file.
- Separation model.
- Tempo factors.
- Export folder.
- Created files.
- Errors or warnings, if any.

Acceptance check:

```bash
ls outputs/logs
```

Expected result:

- At least one log file exists after a full pipeline run.

## AC-014: Tests Can Run

The test suite shall run with:

```bash
pytest
```

Expected result:

- Tests execute without import errors.
- Path handling tests pass.
- Tempo factor tests pass.
- Pipeline dry-run tests pass.

## AC-015: Tempo Function Is Testable Without Demucs

The tempo export functionality shall be testable independently from source separation.

Acceptance check:

1. Place any small valid `.wav` file in a temporary test folder.
2. Run the tempo export function or script.
3. Confirm that tempo variants are created.

Expected result:

- Tempo tests do not require Demucs.
- Tempo tests do not require a Mozart recording.
- Tempo tests can run using a synthetic or short sample file.

## AC-016: Missing External Dependency Gives Clear Error

If an external dependency is missing, the error shall be understandable.

Relevant dependencies:

```text
ffmpeg
demucs
rubberband
```

Expected result:

- The error message identifies the missing dependency.
- The error message suggests the failed processing stage.
- The system does not continue as if the step succeeded.

## AC-017: Final Summary Is Printed

After a successful full pipeline run, the system shall print a final summary.

The summary shall include:

- Input file.
- Exported files.
- Log file path.

Expected format:

```text
Pipeline completed.

Input:
  data/raw/example.mp3

Created:
  data/exports/example_no_piano_100.wav
  data/exports/example_no_piano_95.wav
  data/exports/example_no_piano_90.wav
  data/exports/example_no_piano_85.wav

Log:
  outputs/logs/example.log
```

## AC-018: Practical Audio Review

The final files shall be manually reviewed by listening.

The result is accepted for practice if:

- The original piano part is clearly reduced.
- The orchestra remains recognizable.
- The slowed versions keep the same pitch.
- The tempo change is stable.
- The file is usable for playing along.

The result is not accepted if:

- The original piano still dominates.
- The orchestra is destroyed or heavily distorted.
- The slowed versions sound pitch-shifted.
- The output has clicks, dropouts, or severe warping.

## AC-019: Private Practice Constraint

The generated files shall be treated as private practice files.

Acceptance condition:

- The documentation states that processed commercial recordings should not be redistributed.

## Minimum Done Definition

The project reaches minimum done status when:

1. A valid input recording can be processed.
2. A no-piano accompaniment file is exported.
3. Tempo versions at 100, 95, 90, and 85 percent are created.
4. The pitch is preserved.
5. The files are saved in `data/exports/`.
6. A log file is created.
7. `pytest` runs without import errors.
8. The result is usable for practice, even if imperfect.
