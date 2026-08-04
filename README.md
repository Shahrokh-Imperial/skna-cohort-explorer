# SKNA Cohort Explorer

Version **1.0.0** — first public release.

A Streamlit application for interactive, per-recording exploration of processed ECG-derived SKNA cohorts. It visualises retained physiological channels, channel-specific and median SKNA, adaptive thresholds, phase-level burst occupancy, sequential replay, and exportable results.

## What this repository is for

Use this interface after recordings have been preprocessed and recording-specific thresholds have been generated. For raw preprocessing and threshold generation, use the companion `skna-event-driven-framework` repository.

## Installation

```bash
git clone https://github.com/Shahrokh-Imperial/skna-cohort-explorer.git
cd skna-cohort-explorer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pytest -q
```

## Run the app

```bash
bash app/run.sh
```

Open the local Streamlit address shown in the terminal.

## Test with the synthetic example

In the sidebar use:

- processed signal source: `examples/001_signals_ecg_skna.csv`
- INAP events CSV: `examples/example_events.csv`
- threshold summary CSV: `examples/example_thresholds.csv`

The example is synthetic and does not contain experimental data.

## Use your cohort

Processed recordings may be supplied as individual CSV files, directories, or ZIP archives. Recommended filenames follow `RECORDING_ID_signals_ecg_skna.csv`. The app needs:

1. processed recordings containing `time_s` and `skna_med`;
2. an event CSV containing recording ID, onset, and end;
3. a threshold summary containing recording ID and the selected threshold.

See `docs/INPUT_FORMAT.md`.

## Important behaviour

- The app does not modify source recordings.
- It reads the recording-specific thresholds supplied in the threshold table.
- Replay-control changes are exploratory and do not overwrite manuscript outputs.
- Retained raw/physiological channels are shown only when present in the processed file.

## Repository map

- `app/`: Streamlit application and launcher
- `src/skna_framework/`: synchronized read-only I/O and cohort-analysis helpers
- `examples/`: synthetic demonstration files
- `tools/check_data.py`: basic input checker
- `docs/`: user and input-format documentation
- `tests/`: import, discovery, and unit-conversion tests

## Companion repositories

- `skna-event-driven-framework`: preprocessing and scientific command-line workflow
- `skna-deployment-monitor`: raw-to-results, multi-event deployment-oriented interface

## Privacy and scope

Do not commit private recordings to this repository. This is research software, not a medical device. See `SECURITY.md`.

## Citation and licence

See `CITATION.cff`. Released under the MIT License.
