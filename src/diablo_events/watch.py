"""Cached source records and local boundary updates without extra HTTP polls."""
import asyncio
from datetime import datetime, timezone
import json
import time

from .client import fetch
from .parser import record
from .schedule import iso, snapshot


from .cache import EventCache


async def watch(interval_minutes, count=None, fetcher=fetch, emit=None,
                clock=lambda: datetime.now(timezone.utc), monotonic=time.monotonic,
                sleep=asyncio.sleep):
    """Emit at polls and boundaries. Count limits emitted snapshots, not polls."""
    emit = emit or (lambda value: print(json.dumps(value), flush=True))
    cache = EventCache()
    next_poll = monotonic()
    emitted = 0
    while True:
        if monotonic() >= next_poll:
            bundle = await fetcher()
            cache.update(bundle, clock())
            next_poll = monotonic() + interval_minutes * 60
        now = clock()
        emit(cache.evaluate(now))
        emitted += 1
        if count is not None and emitted >= count:
            return
        boundary = cache.next_boundary(now)
        delay = max(0, next_poll - monotonic())
        if boundary:
            delay = min(delay, max(0, (boundary - now).total_seconds()))
        # Short chunks tolerate wall-clock adjustments and remain cancellable.
        deadline = monotonic() + delay
        while monotonic() < deadline:
            await sleep(min(30, deadline - monotonic()))
            now = clock()
            if boundary and now >= boundary:
                break
