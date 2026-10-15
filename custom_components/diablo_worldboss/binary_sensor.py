"""Source health and active Helltide."""
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.entity import EntityCategory
from .entity import EventEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([Health(entry.runtime_data), Helltide(entry.runtime_data)])


class Health(EventEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "health", "Source health")

    @property
    def available(self):
        return True

    @property
    def is_on(self):
        return self.coordinator.last_update_success and self.coordinator.data['health']['success']

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {key: data.get(key) for key in ('health', 'freshness', 'last_attempt_at', 'last_success_at', 'source_coverage')}


class Helltide(EventEntity, BinarySensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator, "helltide_active", "Helltide active")

    @property
    def available(self):
        return super().available and (self.coordinator.data.get('helltide') or {}).get('active') is not None

    @property
    def is_on(self):
        return (self.coordinator.data.get('helltide') or {}).get('active')

    @property
    def extra_state_attributes(self):
        return {key: (self.coordinator.data.get('helltide') or {}).get(key) for key in ('starts_at', 'ends_at', 'next_starts_at', 'zone_id')}
