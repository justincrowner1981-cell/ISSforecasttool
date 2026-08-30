#!/usr/bin/env python3
"""Build aligned hourly training rows from NYISO, EIA and optional NCEI history."""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from refresh_free_data import ROOT, LIVE, atomic_json, fetch_nyiso, load_config, now_iso, parse_float, request

HISTORY = ROOT / "data" / "history"


def fetch_eia_history(config, api_key, start, end):
    if not api_key:
        raise ValueError("EIA_API_KEY is not configured")
    params = urllib.parse.urlencode({
        "api_key": api_key, "frequency": "daily", "data[0]": "value",
        "facets[process][]": config["eia"]["series_id"], "start": start.isoformat(), "end": end.isoformat(),
        "sort[0][column]": "period", "sort[0][direction]": "asc", "length": 5000
    })
    payload = json.loads(request("https://api.eia.gov/v2/natural-gas/pri/fut/data/?" + params).decode())
    result = {}
    for row in payload.get("response", {}).get("data", []):
        value = parse_float(row.get("value"))
        if row.get("period") and value is not None:
            result[row["period"]] = value
    if not result:
        raise ValueError("EIA returned no historical gas rows")
    return result


def ncei_headers(token):
    return {"token": token, "User-Agent": "ISSforecasttool/1.0"}


def choose_station(config, token, start, end):
    configured = config["ncei"].get("station_id", "").strip()
    if configured:
        return configured
    lat, lon = config["plant"]["latitude"], config["plant"]["longitude"]
    radius = config["ncei"].get("search_radius_degrees", 0.5)
    extent = f"{lat-radius},{lon-radius},{lat+radius},{lon+radius}"
    params = urllib.parse.urlencode({"datasetid": "GHCND", "extent": extent, "startdate": start.isoformat(), "enddate": end.isoformat(), "limit": 1000})
    payload = json.loads(request("https://www.ncei.noaa.gov/cdo-web/api/v2/stations?" + params, ncei_headers(token)).decode())
    stations = payload.get("results", [])
    if not stations:
        raise ValueError("NCEI station search returned no stations")
    stations.sort(key=lambda item: item.get("datacoverage", 0), reverse=True)
    return stations[0]["id"]


def fetch_ncei(config, token, start, end):
    if not token:
        raise ValueError("NCEI_TOKEN is not configured")
    station = choose_station(config, token, start, end)
    params = urllib.parse.urlencode([
        ("datasetid", "GHCND"), ("stationid", station), ("startdate", start.isoformat()),
        ("enddate", end.isoformat()), ("units", "standard"), ("limit", "1000"),
        ("datatypeid", "TMAX"), ("datatypeid", "TMIN"), ("datatypeid", "TAVG")
    ])
    payload = json.loads(request("https://www.ncei.noaa.gov/cdo-web/api/v2/data?" + params, ncei_headers(token)).decode())
    daily = {}
    for item in payload.get("results", []):
        day = item["date"][:10]
        daily.setdefault(day, {})[item["datatype"].lower()] = item["value"]
    for values in daily.values():
        values["temperature"] = values.get("tavg")
        if values["temperature"] is None and values.get("tmin") is not None and values.get("tmax") is not None:
            values["temperature"] = (values["tmin"] + values["tmax"]) / 2
    if not daily:
        raise ValueError("NCEI returned no historical weather observations")
    atomic_json(LIVE / "ncei_weather_history_latest.json", {"generated_at": now_iso(), "station_id": station, "row_count": len(daily), "rows": daily})
    return daily, station


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fields = ["hour", "lbmp", "gas", "temperature", "weather_station", "market_location", "source"]
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()
    config = load_config()
    end = date.fromisoformat(args.end) if args.end else datetime.now(timezone.utc).date() - timedelta(days=1)
    start = date.fromisoformat(args.start) if args.start else end - timedelta(days=config["nyiso"]["history_days"] - 1)
    if end < start or (end - start).days > 365:
        raise ValueError("backfill range must be 1 to 366 days")
    gas = fetch_eia_history(config, os.getenv("EIA_API_KEY"), start, end)
    weather = {}; station = None; weather_error = None
    try:
        weather, station = fetch_ncei(config, os.getenv("NCEI_TOKEN"), start, end)
    except Exception as error:
        weather_error = str(error)[:500]
    rows, logs = [], []
    current = start
    while current <= end:
        try:
            market_rows, url = fetch_nyiso(config, current)
            logs.append({"date": current.isoformat(), "state": "online", "rows": len(market_rows), "url": url})
            for market in market_rows:
                day = market["hour"][:10] if market["hour"][:4].isdigit() else current.isoformat()
                rows.append({"hour": market["hour"], "lbmp": market["lbmp"], "gas": gas.get(day),
                             "temperature": weather.get(day, {}).get("temperature"), "weather_station": station,
                             "market_location": market["location"], "source": "NYISO+EIA" + ("+NCEI" if day in weather else "")})
        except Exception as error:
            logs.append({"date": current.isoformat(), "state": "offline", "rows": 0, "error": str(error)[:500]})
        current += timedelta(days=1)
    unique = {row["hour"]: row for row in rows if row.get("gas") is not None}
    rows = [unique[key] for key in sorted(unique)]
    if not rows:
        raise ValueError("backfill produced zero aligned NYISO/EIA rows; existing output was preserved")
    output = {"generated_at": now_iso(), "start": start.isoformat(), "end": end.isoformat(), "row_count": len(rows), "rows": rows}
    atomic_json(LIVE / "internet_training_rows.json", output)
    atomic_json(LIVE / "internet_training_nyiso_log.json", {"generated_at": now_iso(), "days": logs})
    atomic_json(LIVE / "internet_training_summary.json", {
        "generated_at": now_iso(), "state": "complete" if all(item["state"] == "online" for item in logs) else "partial",
        "row_count": len(rows), "market_days_ok": sum(item["state"] == "online" for item in logs),
        "market_days_failed": sum(item["state"] != "online" for item in logs), "weather_station": station,
        "weather_state": "online" if weather else "skipped", "weather_error": weather_error
    })
    write_csv(HISTORY / "internet_training_rows.csv", rows)
    print(json.dumps({"row_count": len(rows), "weather_station": station, "weather_error": weather_error}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
