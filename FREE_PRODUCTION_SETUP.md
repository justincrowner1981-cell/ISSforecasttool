# Free Production Setup Guide

This version is ready for a free GitHub Pages + GitHub Actions deployment.

## What this adds

- Scheduled free data refresh workflow.
- NYISO zipped CSV download/extract script.
- EIA Henry Hub pull using a free EIA API key.
- NWS hourly forecast pull using free NWS API.
- Browser-friendly files in `data/live/`.
- GitHub Pages deployment workflow.

## Step 1: Create a GitHub repository

Create a new repository, for example:

```text
indeck-silver-springs-margin-site
```

Upload all files from this folder.

## Step 2: Enable GitHub Pages

In GitHub:

```text
Settings → Pages → Source → GitHub Actions
```

The included workflow `.github/workflows/deploy-pages.yml` will publish the website.

## Step 3: Add free API secrets

In GitHub:

```text
Settings → Secrets and variables → Actions → New repository secret
```

Add:

```text
EIA_API_KEY
NCEI_TOKEN
```

`NCEI_TOKEN` is optional until you add historical weather station pulls.

## Step 4: Run the data refresh manually first

Go to:

```text
Actions → Refresh Free Market Data → Run workflow
```

This will create or update:

```text
data/live/refresh_status.json
data/live/eia_henry_hub_latest.json
data/live/nws_hourly_forecast_latest.json
data/live/market_latest.json
data/history/*.csv
```

## Step 5: Confirm NYISO endpoint mapping

The script includes editable NYISO endpoint patterns in:

```text
config/free-data-config.json
```

You must confirm the exact NYISO dataset and pricing location.

Important: the default pattern uses NYISO public zonal-style DAM/RT zip naming as a starting point. For plant-grade use, confirm the generator bus/PTID or exact LBMP location and update the pattern/filter logic.

## Step 6: Use the website

After GitHub Pages deploys:

- Open the website.
- Go to Data Sources.
- Confirm plant assumptions.
- Import NYISO CSV manually if the automated endpoint needs adjustment.
- Build the Historical Training set.
- Review P10/P50/P90 and Probability Profitable.

## Best no-paid forecasting path

Use:

```text
NYISO public MIS data
EIA Henry Hub
NWS hourly forecast
NOAA/NCEI historical weather
Manual or CSV delivered gas basis
Actual plant run/fuel history when available
```

## Why local gas basis is manual

There is no reliable free professional API for delivered Northeast gas basis comparable to ICE/NGI/Platts/Argus. The no-paid solution is:

```text
delivered gas = EIA Henry Hub + manual basis + transport + retainage
```

or upload a CSV from your gas supplier/internal data.
