"""Derive only times supported by the captured source records."""
from .parser import record


def iso(value):
    return value.isoformat().replace("+00:00", "Z") if value else None


def snapshot(bundle, now, fetched_at):
    errors, parsed, events = [], {}, []
    result = {"schema_version": 1, "source_url": "https://helltides.com/", "evaluated_at": iso(now),
              "last_attempt_at": iso(fetched_at), "last_success_at": None,
              "helltide": None, "world_boss": None, "upcoming_events": [],
              "source_coverage": {}, "freshness": "unknown"}
    for kind in ("helltide", "world_boss", "legion"):
        wrapper = bundle.get(kind, {})
        try:
            if not isinstance(wrapper, dict):
                raise ValueError("Invalid source envelope")
            if "error" in wrapper:
                raise ValueError(str(wrapper["error"]))
            parsed[kind] = record(wrapper.get("data"), kind)
        except (ValueError, TypeError) as error:
            errors.append({"source": kind, "code": "invalid_source", "message": str(error)})
    for kind, (raw, start, boundary) in parsed.items():
        url = bundle[kind].get("url")
        result["source_coverage"][kind] = {"through": iso(boundary), "exhausted": now >= boundary}
        if now >= boundary:
            errors.append({"source": kind, "code": "coverage_exhausted", "message": "Refresh required; no verified later record"})
        if kind == "helltide":
            active = start <= now < boundary if now < boundary else None
            result["helltide"] = {"active": active, "starts_at": iso(start), "ends_at": iso(boundary),
                "next_starts_at": iso(start) if now < start else None,
                "seconds_until_transition": max(0, int(((boundary if active else start) - now).total_seconds())) if active is not None else None,
                "zone_id": raw.get("zone"), "source_url": url}
            if start > now:
                events.append({"type": kind, "name": "Helltide", "starts_at": iso(start), "ends_at": iso(boundary), "source_url": url})
        else:
            # At spawn, hand off to nextTime; its identity/location are unknown.
            future = start > now
            when = start if future else boundary
            zones = raw.get("zone", []) if future and kind == "world_boss" else []
            event = {"type": kind, "name": raw.get("boss") if future and kind == "world_boss" else ("Legion" if kind == "legion" else None),
                     "starts_at": iso(when), "seconds_until_start": max(0, int((when-now).total_seconds())),
                     "locations": zones, "identity_status": "source_reported" if future else "unknown_next_event",
                     "source_url": url}
            if now < boundary:
                events.append(event)
                if kind == "world_boss":
                    result["world_boss"] = event
    result["upcoming_events"] = sorted(events, key=lambda e: (e["starts_at"], e["type"]))
    status = "ok" if not errors else ("partial" if parsed else "error")
    result["health"] = {"success": not errors, "status": status, "errors": errors}
    result["freshness"] = "fresh" if not errors else "partial_or_stale" if parsed else "unknown"
    if not errors:
        result["last_success_at"] = iso(fetched_at)
    return result
