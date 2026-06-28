"""Diagnostics de l'integration Edisio (export depuis l'UI)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICES, DOMAIN
from .gateway import EdisioGateway


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Donnees de diagnostic du reseau Edisio (passerelle + modules)."""
    gw: EdisioGateway = hass.data[DOMAIN][entry.entry_id]
    return {
        "passerelle": {
            "port": gw.port,
            "connectee": gw.connected,
            "dongle": gw.dongle_description,
            "dongle_vid_pid": gw.dongle_vidpid,
            "trames_recues": gw.frames_received,
            "derniere_trame": gw.last_frame_at.isoformat() if gw.last_frame_at else None,
            "mode_inclusion": gw.inclusion,
        },
        "emetteurs_appaires": [
            {"id": dev_id, "kinds": sorted(kinds)}
            for dev_id, kinds in gw.accepted.items()
        ],
        "emetteurs_bannis": sorted(gw.banned),
        "recepteurs": entry.options.get(CONF_DEVICES, []),
    }
