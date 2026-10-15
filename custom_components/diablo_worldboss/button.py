"""Manual debounced refresh."""
from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.helpers.entity import EntityCategory
from .entity import EventEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([Refresh(entry.runtime_data)])


class Refresh(EventEntity, ButtonEntity):
    _attr_device_class = ButtonDeviceClass.UPDATE
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator):
        super().__init__(coordinator, 'refresh', 'Refresh')

    @property
    def available(self):
        return True

    async def async_press(self):
        await self.coordinator.async_request_refresh()
