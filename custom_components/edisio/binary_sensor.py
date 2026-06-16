"""Plateforme binary_sensor : etat ON/OFF des emetteurs/contacts Edisio."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_DISCOVERY, SIGNAL_RX


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    seen: set[str] = set()

    @callback
    def _discovered(data: dict) -> None:
        kinds = data.get("kinds") or set()
        if "binary" not in kinds and data.get("value") not in ("on", "off"):
            return
        dev_id = data["id"]
        if dev_id in seen:
            return
        seen.add(dev_id)
        async_add_entities([EdisioBinarySensor(dev_id, data.get("value") == "on")])

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_DISCOVERY, _discovered)
    )


class EdisioBinarySensor(BinarySensorEntity):
    _attr_should_poll = False

    def __init__(self, dev_id: str, initial: bool):
        self._dev_id = dev_id
        self._attr_is_on = initial
        self._attr_name = f"Edisio {dev_id} etat"
        self._attr_unique_id = f"{DOMAIN}_{dev_id}_state"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{SIGNAL_RX}_{self._dev_id}", self._update
            )
        )

    @callback
    def _update(self, data: dict) -> None:
        if data.get("value") == "on":
            self._attr_is_on = True
        elif data.get("value") == "off":
            self._attr_is_on = False
        else:
            return
        self.async_write_ha_state()
