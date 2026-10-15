"""Common entity identity and grouping."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, NAME


class EventEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = {"identifiers": {(DOMAIN, DOMAIN)}, "name": NAME,
                                  "manufacturer": "Helltides.com", "entry_type": "service"}
