"""Validate source records without guessing missing values."""
from datetime import datetime, timezone


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Expected an ISO 8601 timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return result.astimezone(timezone.utc)


def record(value, kind):
    if not isinstance(value, dict) or "error" in value:
        raise ValueError("Missing or rejected event record")
    start = timestamp(value.get("startTime"))
    end = timestamp(value.get("endTime" if kind == "helltide" else "nextTime"))
    if end <= start:
        raise ValueError("Event times are not increasing")
    if kind == "world_boss":
        boss = value.get("boss")
        if boss is not None and (not isinstance(boss, str) or not boss.strip()):
            raise ValueError("Invalid boss name")
        zones = value.get("zone", [])
        if not isinstance(zones, list) or any(not isinstance(z, dict) for z in zones):
            raise ValueError("Invalid boss locations")
        for zone in zones:
            for field in ("name", "id", "boss"):
                if field in zone and not isinstance(zone[field], str):
                    raise ValueError("Invalid location field")
    return value, start, end
