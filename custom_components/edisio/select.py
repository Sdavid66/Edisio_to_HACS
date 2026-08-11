"""Plateforme select : modules de chauffage Edisio (fil pilote, chaudiere)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import EdisioReceiver

# action catalogue -> libelle expose
MODES = {"heat_on": "Confort", "heat_off": "Arret", "heat_other": "Eco"}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    gw = hass.data[DOMAIN][entry.entry_id]
    for sub_id, devs in EdisioReceiver.groups_for(entry, "select"):
        async_add_entities(
            (EdisioHeating(gw, d) for d in devs), config_subentry_id=sub_id
        )


class EdisioHeating(EdisioReceiver, SelectEntity):
    def __init__(self, gw, dev):
        super().__init__(gw, dev)
        # n'expose que les modes disponibles dans le catalogue du modele
        self._actions = {MODES[a]: a for a in self._model["frames"] if a in MODES}
        self._attr_options = list(self._actions)
        self._attr_current_option = None

    async def async_select_option(self, option: str) -> None:
        action = self._actions.get(option)
        if action:
            await self._send(action)
            self._attr_current_option = option
            self.async_write_ha_state()
