"""Event names and automation-friendly timestamps."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from .entity import EventEntity
from .lib.parser import timestamp

SENSORS = (
    ('helltide_transition', 'Helltide next transition', True),
    ('world_boss', 'Next world boss', False),
    ('world_boss_time', 'Next world boss time', True),
    ('upcoming', 'Next upcoming event', False),
    ('upcoming_time', 'Next upcoming event time', True),
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(EventSensor(entry.runtime_data, *description) for description in SENSORS)


class EventSensor(EventEntity, SensorEntity):
    def __init__(self, coordinator, key, name, is_time):
        super().__init__(coordinator, key, name)
        self.key = key
        self.is_time = is_time
        if is_time:
            self._attr_device_class = SensorDeviceClass.TIMESTAMP

    def event(self):
        data = self.coordinator.data
        if self.key == 'helltide_transition':
            event = data.get('helltide') or {}
            active = event.get('active')
            return {'starts_at': event.get('ends_at') if active else event.get('next_starts_at')} if active is not None else {}
        if self.key.startswith('world_boss'):
            return data.get('world_boss') or {}
        return next(iter(data.get('upcoming_events', [])), {})

    @property
    def available(self):
        return super().available and bool(self.event())

    @property
    def native_value(self):
        event = self.event()
        if self.is_time:
            return timestamp(event['starts_at']) if event.get('starts_at') else None
        return event.get('name')

    @property
    def extra_state_attributes(self):
        event = self.event()
        return {key: event.get(key) for key in ('type', 'starts_at', 'locations', 'identity_status', 'source_url') if key in event}
