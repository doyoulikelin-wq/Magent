import csv
import io
import json
from datetime import datetime

from dateutil import parser as date_parser


def parse_glucose_payload(filename: str, payload: bytes) -> tuple[list[dict], list[dict]]:
    """Return (rows, errors) where each row has ts and glucose_mgdl."""
    lower = filename.lower()
    if lower.endswith(".json"):
        return _parse_json(payload)
    return _parse_csv(payload)


def _parse_csv(payload: bytes) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    errors: list[dict] = []
    text = payload.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    for idx, row in enumerate(reader, start=2):
        try:
            ts_raw = row.get("ts") or row.get("timestamp") or row.get("time")
            glucose_raw = row.get("glucose_mgdl") or row.get("glucose")
            if not ts_raw or glucose_raw is None:
                raise ValueError("missing ts or glucose")
            ts = _parse_dt(ts_raw)
            glucose = int(float(glucose_raw))
            rows.append({"ts": ts, "glucose_mgdl": glucose})
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": idx, "reason": str(exc)})
    return rows, errors


def _parse_json(payload: bytes) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    errors: list[dict] = []
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, list):
        return [], [{"row": 1, "reason": "json must be an array"}]

    for idx, row in enumerate(data, start=1):
        try:
            ts_raw = row.get("ts") or row.get("timestamp") or row.get("time")
            glucose_raw = row.get("glucose_mgdl") or row.get("glucose")
            if not ts_raw or glucose_raw is None:
                raise ValueError("missing ts or glucose")
            rows.append({"ts": _parse_dt(ts_raw), "glucose_mgdl": int(float(glucose_raw))})
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": idx, "reason": str(exc)})
    return rows, errors


def _parse_dt(value: str) -> datetime:
    dt = date_parser.parse(value)
    if dt.tzinfo is None:
        # Default to UTC when timezone is omitted.
        from datetime import timezone

        dt = dt.replace(tzinfo=timezone.utc)
    return dt
