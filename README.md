# NOAA/NCEI Token Setup Added

This version activates the NOAA/NCEI historical weather backfill. Add your token as the GitHub secret `NCEI_TOKEN`, then run the Import Internet Training Data workflow. Do not hard-code the token into public files.

# Internet Training Import Added

This version includes `scripts/import_internet_training.py` and `.github/workflows/import-training.yml` to pull no-paid internet history into `data/live/internet_training_rows.json`. Use the Historical Training page button to import those rows into the browser model.

# Production-Free Version

This package now includes GitHub Actions, GitHub Pages deployment, and free data-refresh scripts. See `FREE_PRODUCTION_SETUP.md`.

# Indeck Silver Springs DAM Margin Website

A free, static, browser-based website for forecasting gas-fired power plant run margins against NYISO Day-Ahead Market pricing.

## What it does

- Uses demo NYISO DAM LBMP, natural gas, and weather data out of the box.
- Lets the user edit plant variables such as heat rate, MW limits, VOM, gas basis, startup cost, no-load cost, min run hours, ramp rate, derate, auxiliary load, reserve/capacity adders, and margin threshold.
- Calculates:
  - Fuel cost = gas price including basis/transport × heat rate
  - All-in variable cost = fuel cost + VOM + emissions + other adders
  - Energy margin = DAM LBMP - all-in variable cost
  - Gross profit = margin × dispatch MW
  - Net profit after allocated startup/no-load costs
  - Break-even LBMP
- Ranks suggested run blocks using a simplified minimum-run/startup model.
- Supports CSV import and CSV export.
- Includes a market-education page explaining DAM, LBMP, PTID/generator bus, BPCG/uplift, startup/no-load, and settlement caveats.

## How to run locally

1. Unzip the folder.
2. Open `index.html` in Chrome, Edge, or Firefox.
3. Edit the plant inputs and scenarios.
4. Import CSV data if available.

## CSV format

Use columns like:

```csv
hour,lbmp,gas,temperature,condition
2026-06-03T00:00,42.50,3.85,66,Off-peak
```

Accepted alternate names:
- hour: `hour`, `datetime`, or `date`
- LBMP: `lbmp`, `DAM`, or `price`
- gas: `gas`, `ng`, or `gasPrice`
- temperature: `temperature` or `temp`

## Free hosting options

- GitHub Pages
- Netlify
- Vercel
- Cloudflare Pages

## Important caveat

This is a decision-support forecast, not a NYISO settlement engine. Actual results can differ due to dispatch instructions, bid parameters, outages, deviations, metering, reserves, BPCG/uplift, and other settlement factors.


## Free API upgrade

This version adds free-source connectors and a browser-side forecast confidence model.

### Free sources used

1. **NYISO MIS public data**
   - Use for Day-Ahead LBMP, Real-Time LBMP, load, and market history.
   - The website includes configurable NYISO endpoint patterns.
   - Many NYISO public files are zipped CSVs; if the browser cannot read them directly, use a free GitHub Action, Cloudflare Worker, or Netlify Function to unzip and republish as plain CSV/JSON.

2. **EIA Open Data API**
   - Use for Henry Hub gas prices, natural gas storage, and energy fundamentals.
   - Requires a free EIA API key.

3. **NWS API**
   - Use for hourly forecast weather.
   - No key required.
   - Requires a User-Agent header.

4. **NOAA/NCEI CDO API**
   - Use for historical weather.
   - Requires a free token.

5. **Manual/CSV local basis**
   - No reliable free professional local gas basis API is included.
   - The best no-paid approach is: Henry Hub from EIA + user-entered basis/transport + CSV import for any actual delivered gas pricing.

### Forecast confidence model

The website now includes:
- P10 / P50 / P90 forecast net profit
- Probability profitable
- Monte Carlo uncertainty simulation
- Correlation snapshot across DAM LBMP, gas, temperature, hour, and month
- Historical training storage in browser local storage
- Training dataset export

### Recommended free production pattern

For a stronger no-paid setup:

- GitHub Actions scheduled daily:
  - Download NYISO public CSV/ZIP files
  - Unzip into JSON/CSV
  - Commit/update `/data/history/*.csv`
- Website loads those static files from GitHub Pages or Netlify.
- EIA/NWS/NCEI are pulled live or cached daily.
- User continues to maintain local gas basis/transport manually or through CSV.

## Patch note: RUN status corrected

The forecast table no longer marks an hour as `RUN` only because the $/MWh margin is positive. `RUN` now requires positive net profit after startup/no-load allocation. Hours with positive margin but negative net are treated as `NEED RUN BLOCK`, meaning they may only make sense as part of a longer profitable run block.


## Status label updated

The hourly forecast table now uses `NEED RUN BLOCK` instead of `WAIT / NEED BLOCK`.

Meaning:
- `RUN` = positive net profit after startup/no-load allocation.
- `NEED RUN BLOCK` = positive $/MWh spread, but negative net profit for the individual hour.
- `NO RUN` = not enough spread to clear variable cost/threshold.

`NEED RUN BLOCK` means the hour may help inside a longer profitable run window, but should not trigger a start by itself.


## 7-day forecast horizon added

The website now forecasts 7 days by default (`Forecast Horizon Days = 7` in Plant Inputs).

How the outer days are modeled:
- Uses live/free rows when available.
- Extends missing hours using historical training analogs by hour/month.
- Applies weekday/weekend and peak/off-peak shape.
- Applies weather-sensitive price adjustment from modeled temperature.
- Uses gas mean reversion/drift.
- Widens Monte Carlo uncertainty bands as the forecast gets farther out.

Operational caveat:
The farther out the forecast goes, the more it should be treated as planning intelligence, not a dispatch instruction.
