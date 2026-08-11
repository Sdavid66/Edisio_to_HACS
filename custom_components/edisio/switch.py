"""Plateforme switch : recepteurs ON/OFF + interrupteur 'Mode inclusion'."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, SIGNAL_INCLUSION
from .device import gateway_device_info
from .entity import EdisioReceiver
from .gateway import EdisioGateway


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities) -> None:
    gw: EdisioGateway = hass.data[DOMAIN][entry.entry_id]
    for sub_id, devs in EdisioReceiver.groups_for(entry, "switch"):
        async_add_entities(
            (EdisioSwitch(gw, d) for d in devs), config_subentry_id=sub_id
        )
    async_add_entities([EdisioInclusionSwitch(gw, entry)])


class EdisioSwitch(EdisioReceiver, SwitchEntity):
    def __init__(self, gw, dev):
        super().__init__(gw, dev)
        self._attr_is_on = False

    async def async_turn_on(self, **kwargs):
        await self._send("on")
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._send("off")
        self._attr_is_on = False
        self.async_write_ha_state()


class EdisioInclusionSwitch(SwitchEntity):
    """Interrupteur global activant la decouverte de nouveaux emetteurs."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:radar"

    def __init__(self, gateway: EdisioGateway, entry: ConfigEntry):
        self._gateway = gateway
        self._attr_name = "Edisio mode inclusion"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_inclusion"
        self._attr_device_info = gateway_device_info(entry.entry_id, gateway.port)

    @property
    def is_on(self) -> bool:
        return self._gateway.inclusion

    async def async_turn_on(self, **kwargs):
        self._gateway.async_set_inclusion(True)

    async def async_turn_off(self, **kwargs):
        self._gateway.async_set_inclusion(False)

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_INCLUSION, self._changed)
        )

    @callback
    def _changed(self, _enabled: bool):
        self.async_write_ha_state()
