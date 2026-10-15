"""Public read-only transport. Replaceable by a HA-owned async session later."""
import asyncio
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

BASE = "https://helltides-7e530-r1.firebaseio.com"
PATHS = {"helltide": "helltide", "world_boss": "world_boss", "legion": "legion"}
MAX_BYTES = 1_000_000


def get_json(url):
    request = Request(url, headers={"User-Agent": "diablo-events/0.1 (event reader)", "Accept": "application/json"})
    with urlopen(request, timeout=15) as response:
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("Source response exceeds size limit")
    return json.loads(payload)


def retry_delay(error, attempt):
    if isinstance(error, HTTPError):
        if error.code not in (429, 500, 502, 503, 504):
            return None
        value = error.headers.get("Retry-After") if error.headers else None
        if value:
            try:
                delay = float(value)
            except ValueError:
                try:
                    delay = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
                except (ValueError, TypeError):
                    return None
            # Defer to the next regular poll rather than shorten a long server delay.
            return max(0, delay) if delay <= 30 else None
    elif not isinstance(error, OSError):
        return None
    return 2 ** attempt


async def fetch():
    async def read(key, path):
        url = f"{BASE}/{path}.json"
        for attempt in range(3):
            try:
                return key, {"url": url, "data": await asyncio.to_thread(get_json, url)}
            except (OSError, ValueError) as error:
                delay = retry_delay(error, attempt)
                if attempt == 2 or delay is None:
                    return key, {"url": url, "error": {"code": "fetch_failed", "message": str(error)}}
                await asyncio.sleep(delay)
    return dict(await asyncio.gather(*(read(key, path) for key, path in PATHS.items())))
