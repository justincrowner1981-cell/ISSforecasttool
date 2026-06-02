# No-Paid-API Forecasting Architecture

## Goal

Forecast Indeck Silver Springs run profitability using the best free data sources available.

## Data Sources

| Source | Cost | Use | Key Required |
|---|---:|---|---|
| NYISO MIS public data | Free | DAM LBMP, RT LBMP, load, market history | No |
| EIA Open Data API | Free | Henry Hub gas, gas storage, fundamentals | Yes, free |
| NWS API | Free | Hourly forecast weather | No |
| NOAA/NCEI CDO API | Free | Historical weather | Yes, free |
| Manual/CSV local gas basis | Free | Delivered gas adjustment | No |

## Confidence Model

The model compares:
- DAM LBMP
- Gas price
- Weather
- Hour of day
- Month
- Plant cost inputs
- Scenario shocks

It produces:
- Expected net profit
- P10 downside
- P50 median
- P90 upside
- Probability profitable

## Important Limitation

The weakest free input is local delivered gas/basis pricing. For best results without paid APIs, keep a CSV of actual delivered gas prices, supplier quotes, or internal fuel settlement values and import it regularly.


## 7-Day Horizon

For hours beyond directly available DAM/live data, the website uses a model-extension process:
- hour-of-day analogs
- month/season analogs
- weekday/weekend effects
- peak/off-peak shape
- temperature-based load pressure
- gas mean reversion
- widening confidence intervals

This is intended to identify likely profitable windows, not guarantee future DAM outcomes.
