#!/usr/bin/env python3
"""Refresh public market/fuel/weather data without third-party Python packages."""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "data" / "live"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def request(url, headers=None, timeout=45):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_config():
    return json.loads((ROOT / "config" / "free-data-config.json").read_text())


def parse_float(value):
    if value is None:
        return None
    text = str(value).replace("$", "").replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def validate_range(rows, key, low, high):
    values = [row.get(key) for row in rows if row.get(key) is not None]
    if not values:
        raise ValueError(f"no numeric {key} values")
    invalid = [value for value in values if value < low or value > high]
    if invalid:
        raise ValueError(f"{len(invalid)} {key} values outside {low}..{high}")


def normalize_nyiso_time(value):
    value = value.strip()
    for pattern in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, pattern).isoformat()
        except ValueError:
            pass
    return value


def fetch_nyiso(config, target_date):
    pattern = config["nyiso"]["dam_url_pattern"]
    url = pattern.format(yyyymmdd=target_date.strftime("%Y%m%d"))
    raw = request(url)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise ValueError("NYISO archive contains no CSV")
        text = archive.read(csv_names[0]).decode("utf-8-sig")
    wanted = config["nyiso"]["location_name"].strip().upper()
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        normalized = {key.strip().lower(): value for key, value in row.items() if key}
        name = (normalized.get("name") or normalized.get("zone name") or normalized.get("location") or "").strip().upper()
        if wanted and name != wanted:
            continue
        timestamp = normalized.get("timestamp") or normalized.get("time stamp") or normalized.get("datetime")
        lbmp = parse_float(normalized.get("lbmp ($/mwhr)") or normalized.get("lbmp ($/mwh)") or normalized.get("lbmp") or normalized.get("dam lbmp"))
        if timestamp and lbmp is not None:
            rows.append({"hour": normalize_nyiso_time(timestamp), "lbmp": lbmp, "location": name, "source": "NYISO DAM"})
    if len(rows) < config["validation"]["minimum_market_rows"]:
        raise ValueError(f"NYISO location {wanted!r} produced {len(rows)} rows")
    validate_range(rows, "lbmp", config["validation"]["lbmp_min"], config["validation"]["lbmp_max"])
    return rows, url


def fetch_nws(config):
    plant = config["plant"]
    headers = {"User-Agent": config["nws"]["user_agent"], "Accept": "application/geo+json"}
    point_url = f"https://api.weather.gov/points/{plant['latitude']},{plant['longitude']}"
    point = json.loads(request(point_url, headers).decode())
    forecast_url = point["properties"]["forecastHourly"]
    forecast = json.loads(request(forecast_url, headers).decode())
    rows = [{
        "hour": period["startTime"], "temperature": period.get("temperature"),
        "temperature_unit": period.get("temperatureUnit"), "condition": period.get("shortForecast"),
        "wind_speed": period.get("windSpeed"), "source": "NWS"
    } for period in forecast["properties"]["periods"]]
    if not rows:
        raise ValueError("NWS returned zero hourly periods")
    return rows, forecast_url


def fetch_eia(config, api_key):
    if not api_key:
        raise ValueError("EIA_API_KEY is not configured")
    # EIA v2 natural-gas daily Henry Hub spot-price route.
    params = urllib.parse.urlencode({
        "api_key": api_key, "frequency": "daily", "data[0]": "value",
        "facets[process][]": config["eia"]["series_id"], "sort[0][column]": "period",
        "sort[0][direction]": "desc", "length": 30
    })
    url = "https://api.eia.gov/v2/natural-gas/pri/fut/data/?" + params
    payload = json.loads(request(url).decode())
    source_rows = payload.get("response", {}).get("data", [])
    rows = [{"date": row.get("period"), "gas": parse_float(row.get("value")), "source": "EIA"} for row in source_rows]
    rows = [row for row in rows if row["date"] and row["gas"] is not None]
    validate_range(rows, "gas", config["validation"]["gas_min"], config["validation"]["gas_max"])
    return rows, "https://api.eia.gov/v2/natural-gas/pri/fut/data/"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="NYISO operating date (YYYY-MM-DD); defaults to tomorrow")
    args = parser.parse_args()
    config = load_config()
    target = date.fromisoformat(args.date) if args.date else datetime.now(timezone.utc).date() + timedelta(days=1)
    status = {"generated_at": now_iso(), "overall": "offline", "sources": {}}
    successes = 0
    operations = [
        ("nyiso", lambda: fetch_nyiso(config, target), LIVE / "market_latest.json"),
        ("nws", lambda: fetch_nws(config), LIVE / "nws_hourly_forecast_latest.json"),
        ("eia", lambda: fetch_eia(config, os.getenv("EIA_API_KEY")), LIVE / "eia_henry_hub_latest.json")
    ]
    for name, operation, path in operations:
        try:
            rows, source_url = operation()
            atomic_json(path, {"generated_at": now_iso(), "source_url": source_url, "row_count": len(rows), "rows": rows})
            status["sources"][name] = {"state": "online", "row_count": len(rows), "updated_at": now_iso()}
            successes += 1
        except Exception as error:
            status["sources"][name] = {"state": "offline", "row_count": 0, "updated_at": now_iso(), "error": str(error)[:500]}
    status["overall"] = "online" if successes == len(operations) else ("degraded" if successes else "offline")
    atomic_json(LIVE / "refresh_status.json", status)
    print(json.dumps(status, indent=2))
    return 0 if status["sources"]["nyiso"]["state"] == "online" and status["sources"]["nws"]["state"] == "online" else 1


if __name__ == "__main__":
    sys.exit(main())
