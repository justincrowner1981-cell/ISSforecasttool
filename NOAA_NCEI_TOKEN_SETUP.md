# NOAA/NCEI Token Setup

Use the NOAA/NCEI token as a GitHub secret. Do not hard-code it into public website files.

## Add the token in GitHub

Go to:

```text
Repository → Settings → Secrets and variables → Actions → New repository secret
```

Create:

```text
Name: NCEI_TOKEN
Value: paste your NOAA/NCEI token
```

## Run the import

Go to:

```text
Actions → Import Internet Training Data → Run workflow
```

The workflow will now attempt to:
- Find a nearby GHCND weather station around the plant latitude/longitude.
- Pull daily historical weather for the selected backfill range.
- Merge daily weather with NYISO/EIA training rows.
- Write `data/live/ncei_weather_history_latest.json`.
- Update `data/live/internet_training_rows.json`.

## Security note

Do not paste the token into `config/free-data-config.json` if the repo is public. GitHub Secrets keeps it out of the codebase.
