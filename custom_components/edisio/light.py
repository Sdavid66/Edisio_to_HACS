"""Plateforme light : recepteurs Edisio lumiere/variateur (EMV-400, EDR-D4…)."""
from __future__ import annotations

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import EdisioReceiver


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    gw = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        EdisioLight(gw, d) for d in EdisioReceiver.devices_for(entry, "light")
    )


class EdisioLight(EdisioReceiver, LightEntity):
    def __init__(self, gw, dev):
        super().__init__(gw, dev)
        self._dimmable = self._model.get("dimmable", False)
        self._attr_is_on = False
        self._attr_brightness = 0
        mode = ColorMode.BRIGHTNESS if self._dimmable else ColorMode.ONOFF
        self._attr_color_mode = mode
        self._attr_supported_color_modes = {mode}

    async def async_turn_on(self, **kwargs):
        if self._dimmable and ATTR_BRIGHTNESS in kwargs:
            pct = round(kwargs[ATTR_BRIGHTNESS] / 255 * 100)
            await self._send("slider", slider=pct)
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]
            self._attr_is_on = pct > 0
        else:
            await self._send("on")
            self._attr_is_on = True
            if self._dimmable and not self._attr_brightness:
                self._attr_brightness = 255
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._send("off")
        self._attr_is_on = False
        self.async_write_ha_state()
