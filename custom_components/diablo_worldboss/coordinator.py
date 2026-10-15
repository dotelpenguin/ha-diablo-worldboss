"""Shared HTTP polling and independent local boundary notifications."""
import asyncio
from datetime import timedelta
import json
import logging
import aiohttp
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from .const import NAME, CONF_INTERVAL, DEFAULT_INTERVAL
from .lib.cache import EventCache

_LOGGER = logging.getLogger(__name__)
BASE = "https://helltides-7e530-r1.firebaseio.com"


class EventCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        minutes = entry.options.get(CONF_INTERVAL, entry.data.get(CONF_INTERVAL, DEFAULT_INTERVAL))
        super().__init__(hass, _LOGGER, name=NAME, config_entry=entry,
                         update_interval=timedelta(minutes=minutes),
                         request_refresh_debouncer=Debouncer(hass, _LOGGER, cooldown=30, immediate=True))
        self.cache = EventCache()
        self.session = async_get_clientsession(hass)
        self._cancel_boundary = None
        self._blocked_until = {}

    async def _read(self, kind):
        url = f"{BASE}/{kind}.json"
        try:
            if dt_util.utcnow() < self._blocked_until.get(kind, dt_util.utcnow()):
                raise ValueError("Source rate limited; waiting for Retry-After")
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=15),
                                        headers={"Accept": "application/json", "User-Agent": "diablo-worldboss/0.1"}) as response:
                if response.status in (429, 503):
                    retry = response.headers.get("Retry-After", "300")
                    try:
                        delay = max(0, int(retry))
                        until = dt_util.utcnow() + timedelta(seconds=delay)
                    except ValueError:
                        from email.utils import parsedate_to_datetime
                        until = parsedate_to_datetime(retry)
                    self._blocked_until[kind] = until
                response.raise_for_status()
                body = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    body.extend(chunk)
                    if len(body) > 1_000_000:
                        raise ValueError("Source response exceeds size limit")
                return kind, {"url": url, "data": json.loads(body)}
        except (aiohttp.ClientError, TimeoutError, ValueError, TypeError, OverflowError) as error:
            _LOGGER.debug("Event source %s failed: %s", kind, error)
            return kind, {"url": url, "error": {"code": "fetch_failed"}}

    async def _async_update_data(self):
        bundle = dict(await asyncio.gather(*(self._read(kind) for kind in ('helltide', 'world_boss', 'legion'))))
        now = dt_util.utcnow()
        self.cache.update(bundle, now)
        if not self.cache.sources:
            raise UpdateFailed("No valid event records retrieved")
        self.schedule_boundary()
        return self.cache.evaluate(now)

    @callback
    def cancel_boundary(self):
        if self._cancel_boundary:
            self._cancel_boundary()
            self._cancel_boundary = None

    @callback
    def schedule_boundary(self):
        self.cancel_boundary()
        boundary = self.cache.next_boundary(dt_util.utcnow())
        if boundary:
            self._cancel_boundary = async_track_point_in_utc_time(self.hass, self._boundary, boundary)

    @callback
    def _boundary(self, now):
        self._cancel_boundary = None
        # Notify listeners without resetting the coordinator's HTTP poll timer.
        self.data = self.cache.evaluate(dt_util.utcnow())
        self.async_update_listeners()
        self.schedule_boundary()
