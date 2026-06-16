"""Flux de configuration UI pour Edisio (pilote par le catalogue de modeles)."""
from __future__ import annotations

import secrets

import voluptuous as vol
from serial.tools import list_ports

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback

from . import models
from .const import (
    CONF_CHANNEL, CONF_DEVICES, CONF_EDISIO_ID, CONF_MODEL, CONF_NAME,
    CONF_PORT, DOMAIN, KNOWN_USB_IDS,
)


async def _async_serial_ports(hass) -> dict[str, str]:
    ports = await hass.async_add_executor_job(list_ports.comports)
    result: dict[str, str] = {}
    for p in ports:
        label = p.device
        if p.description and p.description != "n/a":
            label = f"{p.device} ({p.description})"
        vid_pid = (
            (format(p.vid, "04X"), format(p.pid, "04X"))
            if p.vid and p.pid else None
        )
        if vid_pid in KNOWN_USB_IDS:
            label = f"⭐ {label}"
        result[p.device] = label
    return result


class EdisioConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        ports = await _async_serial_ports(self.hass)
        if user_input is not None:
            port = user_input[CONF_PORT].strip()
            await self.async_set_unique_id(port)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Edisio ({port})",
                data={CONF_PORT: port},
                options={CONF_DEVICES: []},
            )
        selector = vol.In({**ports, "": "Saisie manuelle…"}) if ports else str
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_PORT): selector}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return EdisioOptionsFlow(entry)


class EdisioOptionsFlow(OptionsFlow):
    """Gestion des recepteurs pilotables, a partir du catalogue de modeles."""

    def __init__(self, entry: ConfigEntry):
        self.entry = entry
        self._model: str | None = None

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init", menu_options=["add_device", "remove_device"]
        )

    async def async_step_add_device(self, user_input=None):
        """Etape 1 : choisir le modele reel (EMV-400, EDR-D4, …)."""
        if user_input is not None:
            self._model = user_input[CONF_MODEL]
            return await self.async_step_configure_device()
        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema({vol.Required(CONF_MODEL): vol.In(models.choices())}),
        )

    async def async_step_configure_device(self, user_input=None):
        """Etape 2 : nom et ID virtuel. Tous les canaux du module sont crees."""
        mdl = models.model(self._model)
        if user_input is not None:
            devices = list(self.entry.options.get(CONF_DEVICES, []))
            edisio_id = (user_input.get(CONF_EDISIO_ID) or "").strip().upper()
            if not edisio_id:
                edisio_id = secrets.token_hex(4).upper()
            base = user_input[CONF_NAME]
            multi = len(mdl["channels"]) > 1
            for ch in mdl["channels"]:
                devices.append({
                    CONF_NAME: f"{base} C{ch}" if multi else base,
                    CONF_MODEL: self._model,
                    CONF_CHANNEL: ch,
                    CONF_EDISIO_ID: edisio_id,
                })
            return self.async_create_entry(title="", data={CONF_DEVICES: devices})

        return self.async_show_form(
            step_id="configure_device",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=mdl["name"]): str,
                vol.Optional(CONF_EDISIO_ID, default=""): str,
            }),
            description_placeholders={"model": mdl["name"]},
        )

    async def async_step_remove_device(self, user_input=None):
        devices = list(self.entry.options.get(CONF_DEVICES, []))
        if user_input is not None:
            rm = set(user_input.get("remove", []))
            keep = [d for d in devices
                    if f'{d[CONF_EDISIO_ID]}_{d.get(CONF_CHANNEL,1)}' not in rm]
            return self.async_create_entry(title="", data={CONF_DEVICES: keep})
        choices = {
            f'{d[CONF_EDISIO_ID]}_{d.get(CONF_CHANNEL,1)}':
                f'{d[CONF_NAME]} ({models.model(d[CONF_MODEL])["name"]})'
            for d in devices
        }
        return self.async_show_form(
            step_id="remove_device",
            data_schema=vol.Schema(
                {vol.Optional("remove", default=[]):
                    vol.All(vol.ensure_list, [vol.In(choices)])}
            ),
        )
