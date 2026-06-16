"""Plateforme cover : volets roulants Edisio (EMV-400, module volet)."""
from __future__ import annotations

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import EdisioReceiver


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    gw = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        EdisioCover(gw, d) for d in EdisioReceiver.devices_for(entry, "cover")
    )


class EdisioCover(EdisioReceiver, CoverEntity):
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )

    def __init__(self, gw, dev):
        super().__init__(gw, dev)
        self._attr_is_closed = None  # pas de retour d'etat

    async def async_open_cover(self, **kwargs):
        await self._send("open")
        self._attr_is_closed = False
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        await self._send("close")
        self._attr_is_closed = True
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs):
        await self._send("stop")
