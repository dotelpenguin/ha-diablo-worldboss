"""One-shot JSON output and deterministic source replay."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from .client import fetch
from .parser import timestamp
from .schedule import iso, snapshot
from .watch import watch


def interval(value):
    result = int(value)
    if not 5 <= result <= 120:
        raise argparse.ArgumentTypeError("Interval must be 5–120 minutes")
    return result


def positive(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("Count must be positive")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    watch_command = sub.add_parser("watch")
    watch_command.add_argument("--interval-minutes", type=interval, default=5)
    watch_command.add_argument("--count", type=positive, help="Stop after this many snapshots")
    live = sub.add_parser("fetch")
    live.add_argument("--capture", type=Path, help="Write source envelope for replay")
    replay = sub.add_parser("parse")
    replay.add_argument("--fixture", type=Path, required=True)
    replay.add_argument("--at", type=timestamp, required=True)
    for command in (live, replay):
        command.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "watch":
        try:
            asyncio.run(watch(args.interval_minutes, args.count))
        except KeyboardInterrupt:
            return 0
        return 0
    now = datetime.now(timezone.utc)
    try:
        if args.command == "fetch":
            bundle = asyncio.run(fetch())
            now = datetime.now(timezone.utc)
            envelope = {"captured_at": iso(now), "sources": bundle}
            if args.capture:
                args.capture.write_text(json.dumps(envelope, indent=2) + "\n")
            fetched_at = now
        else:
            envelope = json.loads(args.fixture.read_text())
            if not isinstance(envelope, dict) or not isinstance(envelope.get("sources"), dict):
                raise ValueError("Invalid fixture envelope")
            bundle = envelope["sources"]
            fetched_at = timestamp(envelope["captured_at"])
            now = args.at
        output = snapshot(bundle, now, fetched_at)
    except (OSError, ValueError, KeyError) as error:
        output = {"schema_version": 1, "health": {"success": False, "status": "error", "errors": [{"code": "cli_failed", "message": str(error)}]}}
    print(json.dumps(output, indent=2 if args.pretty else None))
    status = output["health"]["status"]
    if status != "ok":
        print(f"Event result: {status}", file=sys.stderr)
    return {"ok": 0, "partial": 3, "error": 1}[status]
