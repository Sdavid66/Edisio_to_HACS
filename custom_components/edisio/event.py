"""Plateforme event : appuis sur les telecommandes Edisio (pour automatisations)."""
from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_DISCOVERY, SIGNAL_RX
from .device import emitter_device_info

EVENT_TYPES = ["on", "off", "toggle", "up", "down", "stop"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    seen: set[str] = set()

    @callback
    def _discovered(data: dict) -> None:
        kinds = data.get("kinds") or set()
        val = data.get("value")
        is_event = "event" in kinds or (isinstance(val, str) and val in EVENT_TYPES)
        if not is_event:
            return
        dev_id = data["id"]
        if dev_id in seen:
            return
        seen.add(dev_id)
        async_add_entities([EdisioRemoteEvent(entry.entry_id, dev_id, data.get("name"))])

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_DISCOVERY, _discovered)
    )


class EdisioRemoteEvent(EventEntity):
    _attr_should_poll = False
    _attr_event_types = EVENT_TYPES

    def __init__(self, entry_id: str, dev_id: str, name: str | None = None):
        self._dev_id = dev_id
        self._attr_name = f"Edisio {dev_id} telecommande"
        self._attr_unique_id = f"{DOMAIN}_{dev_id}_remote"
        self._attr_device_info = emitter_device_info(entry_id, dev_id, name)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{SIGNAL_RX}_{self._dev_id}", self._handle
            )
        )

    @callback
    def _handle(self, data: dict) -> None:
        val = data.get("value")
        if val in EVENT_TYPES:
            self._trigger_event(val, {"button": data.get("button"),
                                      "cmd": data.get("cmd")})
            self.async_write_ha_state()
