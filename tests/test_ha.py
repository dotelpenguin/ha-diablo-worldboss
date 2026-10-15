"""Runtime checks against the installed Home Assistant APIs; no network."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

HAS_HA = importlib.util.find_spec('homeassistant') is not None


@unittest.skipUnless(HAS_HA, 'Install Home Assistant to run integration tests')
class HomeAssistantTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from diablo_events.cache import EventCache
        from diablo_events.parser import timestamp
        bundle = json.loads((Path(__file__).parent / 'fixtures/live.json').read_text())['sources']
        self.now = timestamp('2026-10-14T15:10:00Z')
        cache = EventCache()
        cache.update(bundle, self.now)
        self.coordinator = SimpleNamespace(data=cache.evaluate(self.now), last_update_success=True,
                                           config_entry=SimpleNamespace(entry_id='test'),
                                           async_request_refresh=AsyncMock())

    async def test_entity_values_and_expiry(self):
        from custom_components.diablo_worldboss.binary_sensor import Health, Helltide
        from custom_components.diablo_worldboss.sensor import EventSensor
        health, helltide = Health(self.coordinator), Helltide(self.coordinator)
        boss = EventSensor(self.coordinator, 'world_boss', 'Boss', False)
        time = EventSensor(self.coordinator, 'world_boss_time', 'Time', True)
        self.assertTrue(health.is_on)
        self.assertTrue(helltide.is_on)
        self.assertTrue(helltide.available)
        self.assertEqual(boss.native_value, 'Ashava')
        self.assertIsNotNone(time.native_value.tzinfo)
        self.assertEqual(len(boss.extra_state_attributes['locations']), 2)
        self.coordinator.data['helltide']['active'] = None
        self.assertFalse(helltide.available)
        self.coordinator.data['health']['success'] = False
        self.assertFalse(health.is_on)
        self.assertTrue(health.available)

    async def test_refresh(self):
        from custom_components.diablo_worldboss.button import Refresh
        await Refresh(self.coordinator).async_press()
        self.coordinator.async_request_refresh.assert_awaited_once()

    async def test_interval_schema(self):
        from custom_components.diablo_worldboss.config_flow import schema
        import voluptuous as vol
        self.assertEqual(schema(5)({'interval_minutes': 120})['interval_minutes'], 120)
        with self.assertRaises(vol.Invalid):
            schema(5)({'interval_minutes': 121})

    async def test_local_boundary_does_not_reset_polling(self):
        from custom_components.diablo_worldboss.coordinator import EventCoordinator
        coordinator = Mock()
        coordinator.cache.evaluate.return_value = {'health': {}}
        EventCoordinator._boundary(coordinator, self.now)
        coordinator.async_update_listeners.assert_called_once()
        coordinator.async_set_updated_data.assert_not_called()
        coordinator.schedule_boundary.assert_called_once()

    async def test_unload(self):
        from custom_components.diablo_worldboss import async_unload_entry
        hass = SimpleNamespace(config_entries=SimpleNamespace(async_unload_platforms=AsyncMock(return_value=True)))
        self.assertTrue(await async_unload_entry(hass, SimpleNamespace()))
        hass.config_entries.async_unload_platforms.assert_awaited_once()

    async def test_coordinator_failure_recovery_and_cleanup(self):
        from homeassistant.core import HomeAssistant
        from homeassistant.config_entries import ConfigEntry
        from homeassistant.helpers.update_coordinator import UpdateFailed
        from custom_components.diablo_worldboss.coordinator import EventCoordinator
        from custom_components.diablo_worldboss.entity import EventEntity
        from types import MappingProxyType
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            hass = HomeAssistant(directory)
            entry = ConfigEntry(domain='diablo_worldboss', title='Test', data={'interval_minutes': 120},
                                options={}, version=1, minor_version=1, source='user', unique_id='test',
                                discovery_keys=MappingProxyType({}), subentries_data=[])
            with patch('custom_components.diablo_worldboss.coordinator.async_get_clientsession', return_value=Mock()), \
                 patch('custom_components.diablo_worldboss.coordinator.async_track_point_in_utc_time') as track:
                cancel = Mock()
                track.return_value = cancel
                coordinator = EventCoordinator(hass, entry)
                self.assertEqual(coordinator.update_interval.total_seconds(), 7200)
                coordinator._read = AsyncMock(side_effect=lambda kind: (kind, {'error': 'failed'}))
                with self.assertRaises(UpdateFailed):
                    await coordinator._async_update_data()
                bundle = json.loads((Path(__file__).parent / 'fixtures/live.json').read_text())['sources']
                coordinator._read = AsyncMock(side_effect=lambda kind: (kind, bundle[kind]))
                with patch('custom_components.diablo_worldboss.coordinator.dt_util.utcnow', return_value=self.now):
                    result = await coordinator._async_update_data()
                self.assertTrue(result['health']['success'])
                entity = EventEntity(coordinator, 'test', 'Test')
                self.assertIn(entry.entry_id, entity.unique_id)
                coordinator.cancel_boundary()
                cancel.assert_called_once()
                self.assertIsNone(coordinator._cancel_boundary)
