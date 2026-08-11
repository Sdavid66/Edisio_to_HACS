"""Flux de configuration UI pour Edisio (pilote par le catalogue de modeles)."""
from __future__ import annotations

import json
import secrets

import voluptuous as vol
from serial.tools import list_ports

from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.config_entries import (
    ConfigEntry, ConfigFlow, ConfigSubentryFlow, OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import FileSelector, FileSelectorConfig

from . import jeedom_import, models
from .const import (
    CONF_CHANNEL, CONF_DEVICES, CONF_EDISIO_ID, CONF_MODEL, CONF_NAME,
    CONF_PORT, DOMAIN, KNOWN_USB_IDS, SUBENTRY_TYPE_DEVICE,
)

CONF_FILE = "file"
CONF_PATH = "path"


def _read_text(path: str) -> str:
    """Lecture synchrone d'un fichier texte (appelee dans un executor)."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _read_uploaded(hass: HomeAssistant, file_id: str) -> str:
    """Lecture synchrone d'un fichier televerse via l'UI (executor)."""
    with process_uploaded_file(hass, file_id) as path:
        return path.read_text(encoding="utf-8", errors="replace")


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

    async def async_step_integration_discovery(self, discovery_info):
        """Emetteur Edisio detecte : affiche une carte sur Appareils et services."""
        self._disc_id = discovery_info["id"]
        self._disc_kinds = discovery_info.get("kinds", [])
        await self.async_set_unique_id(
            f"edisio_emitter_{self._disc_id}", raise_on_progress=False
        )
        self.context["title_placeholders"] = {"name": f"Edisio {self._disc_id}"}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(self, user_input=None):
        """Validation de la carte : lie l'emetteur et cree ses entites."""
        entries = self._async_current_entries()
        if not entries:
            return self.async_abort(reason="no_hub")
        if user_input is not None:
            gateway = self.hass.data[DOMAIN][entries[0].entry_id]
            name = (user_input.get(CONF_NAME) or "").strip() or None
            await gateway.async_accept_emitter(self._disc_id, self._disc_kinds, name)
            return self.async_abort(
                reason="device_added",
                description_placeholders={"id": self._disc_id},
            )
        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema({
                vol.Optional(CONF_NAME, default=f"Edisio {self._disc_id}"): str,
            }),
            description_placeholders={
                "id": self._disc_id,
                "kinds": ", ".join(self._disc_kinds) or "—",
            },
        )

    async def async_step_reconfigure(self, user_input=None):
        """Changer le port serie du dongle sans perdre les modules configures."""
        entry = self._get_reconfigure_entry()
        ports = await _async_serial_ports(self.hass)
        if user_input is not None:
            port = user_input[CONF_PORT].strip()
            return self.async_update_reload_and_abort(
                entry,
                title=f"Edisio ({port})",
                data={**entry.data, CONF_PORT: port},
            )
        current = entry.data.get(CONF_PORT, "")
        choices = dict(ports)
        # Garde le port actuel dans la liste meme si le dongle est debranche.
        if current and current not in choices:
            choices[current] = f"{current} (actuel)"
        selector = vol.In({**choices, "": "Saisie manuelle…"}) if choices else str
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {vol.Required(CONF_PORT, default=current): selector}
            ),
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Active le bouton « Ajouter un appareil » sur la page d'integration."""
        return {SUBENTRY_TYPE_DEVICE: EdisioDeviceSubentryFlow}

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return EdisioOptionsFlow(entry)


class EdisioDeviceSubentryFlow(ConfigSubentryFlow):
    """Assistant « Ajouter un appareil » : detection d'emetteur ou ajout de recepteur."""

    _model: str | None = None
    _pending: dict | None = None

    def _gateway(self):
        entry = self._get_entry()
        return self.hass.data.get(DOMAIN, {}).get(entry.entry_id) if entry else None

    async def async_step_user(self, user_input=None):
        """Menu : detecter un emetteur (bouton/telecommande) ou ajouter un recepteur."""
        return self.async_show_menu(step_id="user", menu_options=["pair", "receiver"])

    # ---------------------------------------- emetteur : inclusion + appui bouton
    async def async_step_pair(self, user_input=None):
        """Active l'inclusion sur la passerelle et attend un appui bouton."""
        gateway = self._gateway()
        if gateway is None:
            return self.async_abort(reason="no_hub")
        if user_input is None:
            # 1re presentation : on ouvre la fenetre d'inclusion (capture)
            gateway.async_begin_capture()
            return self.async_show_form(step_id="pair", data_schema=vol.Schema({}))
        pending = gateway.take_pending_emitter()
        if not pending:
            # Aucun appui detecte : on redemande (l'inclusion reste active)
            return self.async_show_form(
                step_id="pair", data_schema=vol.Schema({}),
                errors={"base": "no_press"},
            )
        self._pending = pending
        return await self.async_step_pair_name()

    async def async_step_pair_name(self, user_input=None):
        """Nomme l'emetteur detecte et l'ajoute."""
        gateway = self._gateway()
        if user_input is not None:
            name = (user_input.get(CONF_NAME) or "").strip() or None
            if gateway is not None:
                await gateway.async_accept_emitter(
                    self._pending["id"], self._pending["kinds"], name
                )
                gateway.async_end_capture()
            return self.async_abort(
                reason="emitter_added",
                description_placeholders={"id": self._pending["id"]},
            )
        return self.async_show_form(
            step_id="pair_name",
            data_schema=vol.Schema({
                vol.Optional(CONF_NAME,
                             default=f"Edisio {self._pending['id']}"): str,
            }),
            description_placeholders={
                "id": self._pending["id"],
                "kinds": ", ".join(self._pending["kinds"]) or "—",
            },
        )

    # ---------------------------------------- recepteur : ajout par modele
    async def async_step_receiver(self, user_input=None):
        """Choisir le modele reel (EMV-400, EDR-D4, …)."""
        if user_input is not None:
            self._model = user_input[CONF_MODEL]
            return await self.async_step_configure()
        return self.async_show_form(
            step_id="receiver",
            data_schema=vol.Schema(
                {vol.Required(CONF_MODEL): vol.In(models.choices())}
            ),
        )

    async def async_step_configure(self, user_input=None):
        """Etape 2 : nom et ID Edisio (vide = emetteur virtuel genere)."""
        mdl = models.model(self._model)
        if user_input is not None:
            edisio_id = (user_input.get(CONF_EDISIO_ID) or "").strip().upper()
            if not edisio_id:
                edisio_id = secrets.token_hex(4).upper()
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_MODEL: self._model,
                    CONF_EDISIO_ID: edisio_id,
                },
            )
        return self.async_show_form(
            step_id="configure",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=mdl["name"]): str,
                vol.Optional(CONF_EDISIO_ID, default=""): str,
            }),
            description_placeholders={"model": mdl["name"]},
        )

    async def async_step_reconfigure(self, user_input=None):
        """Modifier le nom / l'ID Edisio d'un appareil existant."""
        subentry = self._get_reconfigure_subentry()
        if user_input is not None:
            edisio_id = (user_input.get(CONF_EDISIO_ID) or "").strip().upper()
            data = {**subentry.data, CONF_NAME: user_input[CONF_NAME]}
            if edisio_id:
                data[CONF_EDISIO_ID] = edisio_id
            return self.async_update_and_abort(
                self._get_entry(), subentry, data=data, title=user_input[CONF_NAME]
            )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=subentry.data.get(CONF_NAME, "")): str,
                vol.Optional(CONF_EDISIO_ID,
                             default=subentry.data.get(CONF_EDISIO_ID, "")): str,
            }),
        )


class EdisioOptionsFlow(OptionsFlow):
    """Gestion des recepteurs pilotables, a partir du catalogue de modeles."""

    def __init__(self, entry: ConfigEntry):
        self.entry = entry
        self._model: str | None = None
        self._import: dict | None = None

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=["remove_device", "import_jeedom"],
        )

    # ------------------------------------------------------------- import Jeedom
    async def async_step_import_jeedom(self, user_input=None):
        """Etape 1 : televerser le fichier d'import (ou indiquer un chemin)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            file_id = user_input.get(CONF_FILE)
            path = (user_input.get(CONF_PATH) or "").strip()
            raw: str | None = None
            try:
                if file_id:  # fichier televerse depuis le navigateur (priorite)
                    raw = await self.hass.async_add_executor_job(
                        _read_uploaded, self.hass, file_id)
                elif path:   # chemin sur le serveur HA (alternative)
                    raw = await self.hass.async_add_executor_job(_read_text, path)
                else:
                    errors["base"] = "no_input"
            except FileNotFoundError:
                errors["base"] = "file_not_found"
            except (OSError, ValueError):
                errors["base"] = "read_error"
            if raw is not None and not errors:
                try:
                    self._import = jeedom_import.load_import(json.loads(raw))
                except (json.JSONDecodeError, jeedom_import.ImportError_):
                    errors["base"] = "invalid_format"
                else:
                    if not (self._import["receivers"] or self._import["emitters"]):
                        errors["base"] = "nothing_found"
                    else:
                        return await self.async_step_import_confirm()
        return self.async_show_form(
            step_id="import_jeedom",
            data_schema=vol.Schema({
                vol.Optional(CONF_FILE): FileSelector(
                    FileSelectorConfig(accept=".json,application/json")
                ),
                vol.Optional(CONF_PATH): str,
            }),
            errors=errors,
        )

    async def async_step_import_confirm(self, user_input=None):
        """Etape 2 : recapitulatif puis application de l'import."""
        data = self._import or {}
        if user_input is not None:
            # 1) recepteurs -> fusion dans options.devices
            devices = list(self.entry.options.get(CONF_DEVICES, []))
            keys = {(d[CONF_EDISIO_ID], d.get(CONF_CHANNEL, 1)) for d in devices}
            for d in data.get("receivers", []):
                key = (d[CONF_EDISIO_ID], d[CONF_CHANNEL])
                if key not in keys:
                    devices.append(d)
                    keys.add(key)
            # 2) emetteurs -> store de la passerelle (entites creees au reload)
            gateway = self.hass.data[DOMAIN].get(self.entry.entry_id)
            if gateway is not None and data.get("emitters"):
                await gateway.async_import_emitters(data["emitters"])
            # La mise a jour des options declenche le rechargement de l'entree.
            return self.async_create_entry(title="", data={CONF_DEVICES: devices})

        return self.async_show_form(
            step_id="import_confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "receivers": str(len(data.get("receivers", []))),
                "emitters": str(len(data.get("emitters", []))),
                "warnings": str(len(data.get("warnings", []))),
            },
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
