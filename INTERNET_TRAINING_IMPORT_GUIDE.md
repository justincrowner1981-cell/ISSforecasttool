# Internet Training Import Guide

This package adds an automated no-paid internet import for the model quality panel.

## What it imports

- NYISO public MIS Day-Ahead LBMP history using configurable public zip CSV patterns.
- EIA Henry Hub gas history using a free EIA API key.
- NWS forecast remains live/current.
- NOAA/NCEI historical weather can be added later with a free token and station mapping.

## How to run it

1. Upload this website folder to GitHub.
2. Add repository secret:

```text
EIA_API_KEY
```

Optional later:

```text
NCEI_TOKEN
```

3. Go to:

```text
Actions → Import Internet Training Data → Run workflow
```

4. The workflow creates:

```text
data/live/internet_training_rows.json
data/live/internet_training_summary.json
data/live/internet_training_nyiso_log.json
data/history/internet_training_rows.csv
```

5. Open the website and click:

```text
Historical Training → Import Internet Training File
```

## Why it may still show 0 rows

Usually one of these:

- The NYISO endpoint pattern needs adjustment.
- The exact generator PTID/bus/zone is not mapped yet.
- GitHub Action has not run.
- `EIA_API_KEY` is missing.
- Browser is loading an old cached page.

## How to improve model quality fastest

- Run 90 to 365 days of NYISO backfill.
- Add the correct NYISO PTID/generator bus filter.
- Add actual delivered gas/basis CSV.
- Add actual plant run history.
- Add historical weather through NOAA/NCEI once station mapping is confirmed.


## NCEI weather backfill is now active

After adding `NCEI_TOKEN` as a GitHub secret, the import script will auto-search for nearby GHCND stations using the plant latitude/longitude in `config/free-data-config.json`.

If the station selected is not ideal, set:

```json
"ncei": {
  "station_id": "GHCND:YOUR_STATION_ID"
}
```

Then rerun the workflow.
