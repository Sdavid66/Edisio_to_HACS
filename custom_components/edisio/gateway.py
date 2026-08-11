"""Passerelle serie Edisio : lecture/ecriture + modes inclusion/exclusion."""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

import serial_asyncio_fast as serial_asyncio

from homeassistant.config_entries import ConfigEntry, SOURCE_INTEGRATION_DISCOVERY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import protocol
from .const import (
    CONF_BANNED, CONF_DISCOVERED, DOMAIN, EVENT_TYPES, INCLUSION_TIMEOUT,
    KNOWN_USB_IDS, SERIAL_BAUDRATE, SIGNAL_DISCOVERY, SIGNAL_INCLUSION,
    SIGNAL_RX, SIGNAL_STATUS, TX_DELAY, TX_REPEAT,
)

_LOGGER = logging.getLogger(__name__)

_HEADER = bytes.fromhex(protocol.HEADER)
_FOOTER = bytes.fromhex(protocol.FOOTER)


def classify(decoded: dict) -> set[str]:
    """Determine les capacites (kinds) d'un emetteur a partir d'une trame."""
    kinds: set[str] = set()
    if decoded.get("battery") is not None:
        kinds.add("battery")
    if "temperature" in decoded:
        kinds.add("temperature")
    val = decoded.get("value")
    if val in ("on", "off"):
        kinds.add("binary")
    if isinstance(val, str) and val in EVENT_TYPES:
        kinds.add("event")
    return kinds


class _EdisioProtocol(asyncio.Protocol):
    """Bufferise le flux serie et extrait les trames completes."""

    def __init__(self, on_frame, on_lost):
        self._on_frame = on_frame
        self._on_lost = on_lost
        self._buf = bytearray()
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        _LOGGER.debug("Connexion serie Edisio etablie")

    def data_received(self, data: bytes) -> None:
        self._buf.extend(data)
        while True:
            start = self._buf.find(_HEADER)
            if start == -1:
                if len(self._buf) > 2:
                    del self._buf[:-2]
                return
            if start > 0:
                del self._buf[:start]
            end = self._buf.find(_FOOTER, len(_HEADER))
            if end == -1:
                return
            frame = bytes(self._buf[: end + len(_FOOTER)])
            del self._buf[: end + len(_FOOTER)]
            self._on_frame(frame)

    def connection_lost(self, exc):
        _LOGGER.warning("Connexion serie Edisio perdue : %s", exc)
        self.transport = None
        self._on_lost()


class EdisioGateway:
    """Liaison serie + dispatch des trames + gestion inclusion/exclusion."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self.port = entry.data["port"]
        # etat accumule (hors config) persiste dans un Store dedie
        self._store: Store = Store(hass, 1, f"edisio_{entry.entry_id}")
        self.accepted: dict[str, set[str]] = {}   # {id: set(kinds)}
        self.names: dict[str, str] = {}           # {id: nom choisi a la decouverte}
        self.banned: set[str] = set()
        self.inclusion = False
        self._capturing = False                     # assistant « Ajouter un appareil »
        self._pending_emitter: dict | None = None
        self._inclusion_cancel: Callable | None = None
        self._transport = None
        self._protocol = None
        self._write_lock = asyncio.Lock()
        self._closing = False
        self._reconnect_task = None
        # etat expose aux entites de diagnostic du hub
        self.connected = False
        self.frames_received = 0
        self.last_frame_at = None
        self.dongle_description: str | None = None
        self.dongle_vidpid: str | None = None

    @property
    def paired_count(self) -> int:
        """Nombre d'emetteurs appaires (acceptes)."""
        return len(self.accepted)

    @callback
    def _notify_status(self) -> None:
        """Previent les entites de diagnostic d'un changement d'etat."""
        async_dispatcher_send(self.hass, SIGNAL_STATUS)

    # ------------------------------------------------------------------ vie
    async def async_start(self) -> None:
        self._closing = False
        await self._async_load()
        await self._resolve_dongle()
        await self._connect()
        # re-cree les entites des emetteurs deja connus (apres redemarrage)
        for dev_id, kinds in self.accepted.items():
            async_dispatcher_send(
                self.hass, SIGNAL_DISCOVERY,
                {"id": dev_id, "kinds": set(kinds), "name": self.names.get(dev_id)},
            )

    async def _resolve_dongle(self) -> None:
        """Identifie le dongle (description USB, VID:PID) pour l'appareil hub."""
        from serial.tools import list_ports
        try:
            ports = await self.hass.async_add_executor_job(list_ports.comports)
        except Exception:  # noqa: BLE001
            return
        for p in ports:
            if p.device != self.port:
                continue
            if p.description and p.description != "n/a":
                self.dongle_description = p.description
            if p.vid and p.pid:
                self.dongle_vidpid = f"{p.vid:04X}:{p.pid:04X}"
            return

    async def _connect(self) -> None:
        try:
            self._transport, self._protocol = await serial_asyncio.create_serial_connection(
                self.hass.loop,
                lambda: _EdisioProtocol(self._handle_frame, self._handle_lost),
                self.port, baudrate=SERIAL_BAUDRATE,
            )
            _LOGGER.info("Passerelle Edisio demarree sur %s", self.port)
            self.connected = True
            self._notify_status()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Ouverture du port %s impossible : %s", self.port, err)
            self.connected = False
            self._notify_status()
            self._schedule_reconnect()

    @callback
    def _handle_lost(self):
        self._transport = None
        self.connected = False
        self._notify_status()
        if not self._closing:
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        if self._closing or (self._reconnect_task and not self._reconnect_task.done()):
            return

        async def _retry():
            await asyncio.sleep(5)
            if not self._closing:
                await self._connect()

        self._reconnect_task = self.hass.async_create_task(_retry())

    async def async_stop(self):
        self._closing = True
        if self._inclusion_cancel:
            self._inclusion_cancel()
        if self._reconnect_task:
            self._reconnect_task.cancel()
        if self._transport:
            self._transport.close()
            self._transport = None
        self.connected = False
        self._notify_status()
        _LOGGER.info("Passerelle Edisio arretee")

    # -------------------------------------------------------------- reception
    @callback
    def _handle_frame(self, frame: bytes) -> None:
        decoded = protocol.decode(frame)
        if decoded is None:
            return
        self.frames_received += 1
        self.last_frame_at = dt_util.utcnow()
        self._notify_status()
        dev_id = decoded["id"]
        if dev_id in self.banned:
            _LOGGER.debug("Trame ignoree (banni) : %s", dev_id)
            return

        kinds = classify(decoded)

        # Assistant « Ajouter un appareil » : on capture le premier appui recu,
        # que l'emetteur soit deja connu ou non (pas de carte pendant la capture).
        if self._capturing:
            self._pending_emitter = {"id": dev_id, "kinds": sorted(kinds)}
            _LOGGER.info("Capture : emetteur %s detecte %s", dev_id, sorted(kinds))
            return

        known = dev_id in self.accepted
        if not known:
            if not self.inclusion:
                _LOGGER.debug("Emetteur %s ignore (hors mode inclusion)", dev_id)
                return
            # Mode inclusion : proposer l'emetteur via une carte de decouverte
            # (Appareils et services) plutot qu'un ajout silencieux.
            _LOGGER.info("Mode inclusion : emetteur %s detecte %s", dev_id, kinds)
            self._async_discover_emitter(dev_id, kinds)
            return
        else:
            # enrichit les capacites si une nouvelle apparait
            new_kinds = kinds - self.accepted[dev_id]
            if new_kinds:
                self.accepted[dev_id] |= new_kinds
                self._persist()
                decoded["kinds"] = set(self.accepted[dev_id])
                async_dispatcher_send(self.hass, SIGNAL_DISCOVERY, decoded)

        async_dispatcher_send(self.hass, f"{SIGNAL_RX}_{dev_id}", decoded)
        async_dispatcher_send(self.hass, SIGNAL_RX, decoded)

    # -------------------------------------------------------------- decouverte
    @callback
    def _async_discover_emitter(self, dev_id: str, kinds: set[str]) -> None:
        """Ouvre une carte de decouverte (Appareils et services) pour un emetteur.

        Deduplique : n'ouvre pas une 2e carte si un flux est deja en cours pour
        ce meme identifiant.
        """
        for flow in self.hass.config_entries.flow.async_progress():
            ctx = flow.get("context", {})
            if flow.get("handler") == DOMAIN and ctx.get("edisio_id") == dev_id:
                return
        self.hass.async_create_task(
            self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_INTEGRATION_DISCOVERY, "edisio_id": dev_id},
                data={"id": dev_id, "kinds": sorted(kinds)},
            )
        )

    async def async_accept_emitter(
        self, dev_id: str, kinds, name: str | None = None
    ) -> None:
        """Ajoute un emetteur decouvert (validation de la carte) et cree ses entites."""
        dev_id = dev_id.upper()
        self.banned.discard(dev_id)
        self.accepted[dev_id] = set(kinds)
        if name:
            self.names[dev_id] = name
        else:
            self.names.pop(dev_id, None)
        await self._store.async_save(self._data_to_save())
        async_dispatcher_send(
            self.hass, SIGNAL_DISCOVERY,
            {"id": dev_id, "kinds": set(kinds), "name": self.names.get(dev_id)},
        )
        _LOGGER.info("Emetteur %s ajoute via la decouverte (nom=%s)", dev_id, name)

    # --------------------------------------------------- capture (assistant)
    @callback
    def async_begin_capture(self, duration: int = INCLUSION_TIMEOUT) -> None:
        """Active l'inclusion et capture le prochain emetteur detecte.

        Utilise par l'assistant « Ajouter un appareil » : pendant la capture,
        un emetteur inconnu est bufferise (au lieu d'ouvrir une carte).
        """
        self._pending_emitter = None
        self._capturing = True
        self.async_set_inclusion(True, duration)

    @callback
    def async_end_capture(self) -> None:
        """Termine la capture et coupe l'inclusion."""
        self._capturing = False
        self._pending_emitter = None
        self.async_set_inclusion(False)

    @callback
    def take_pending_emitter(self) -> dict | None:
        """Renvoie (et consomme) l'emetteur capture, ou None si aucun appui."""
        pending = self._pending_emitter
        self._pending_emitter = None
        return pending

    # -------------------------------------------------------------- inclusion
    @callback
    def async_set_inclusion(self, enabled: bool, duration: int = INCLUSION_TIMEOUT):
        """Active/desactive le mode inclusion (avec fenetre auto-off)."""
        if self._inclusion_cancel:
            self._inclusion_cancel()
            self._inclusion_cancel = None
        if not enabled:
            self._capturing = False
        self.inclusion = enabled
        _LOGGER.info("Mode inclusion : %s", "ON" if enabled else "OFF")
        if enabled and duration:
            self._inclusion_cancel = async_call_later(
                self.hass, duration, self._auto_off
            )
        async_dispatcher_send(self.hass, SIGNAL_INCLUSION, enabled)

    @callback
    def _auto_off(self, _now):
        self._inclusion_cancel = None
        self.inclusion = False
        self._capturing = False
        _LOGGER.info("Mode inclusion : OFF (fin de fenetre)")
        async_dispatcher_send(self.hass, SIGNAL_INCLUSION, False)

    # -------------------------------------------------------------- exclusion
    async def async_forget(self, dev_id: str, ban: bool = False) -> None:
        """Exclut un emetteur : retire entites/appareil et oublie l'id."""
        dev_id = dev_id.upper()
        self.accepted.pop(dev_id, None)
        self.names.pop(dev_id, None)
        if ban:
            self.banned.add(dev_id)
        self._persist()
        await self._remove_from_registries(dev_id)
        _LOGGER.info("Emetteur %s exclu%s", dev_id, " et banni" if ban else "")

    async def _remove_from_registries(self, dev_id: str) -> None:
        from homeassistant.helpers import device_registry as dr, entity_registry as er
        ent_reg = er.async_get(self.hass)
        prefix = f"edisio_{dev_id}_"
        for ent in list(ent_reg.entities.values()):
            if ent.platform == "edisio" and ent.unique_id.startswith(prefix):
                ent_reg.async_remove(ent.entity_id)
        dev_reg = dr.async_get(self.hass)
        for ident in (("edisio", f"emitter_{dev_id}"), ("edisio", dev_id)):
            device = dev_reg.async_get_device(identifiers={ident})
            if device:
                dev_reg.async_remove_device(device.id)

    # ---------------------------------------------------------------- import
    async def async_import_emitters(self, emitters: list[dict]) -> int:
        """Pre-enregistre des emetteurs (import Jeedom) et sauvegarde aussitot.

        Les entites seront creees au rechargement de l'entree (declenche par la
        mise a jour des options) via la re-emission de SIGNAL_DISCOVERY.
        """
        added = 0
        for e in emitters:
            dev_id = str(e.get("id", "")).upper()
            if not dev_id or dev_id in self.banned:
                continue
            kinds = set(e.get("kinds", []))
            if dev_id not in self.accepted:
                self.accepted[dev_id] = kinds
                added += 1
            else:
                self.accepted[dev_id] |= kinds
        if added:
            await self._store.async_save(self._data_to_save())
        return added

    # ---------------------------------------------------------------- emission
    async def async_send(self, frames: list[str]) -> None:
        if self._transport is None:
            _LOGGER.warning("Envoi impossible : port serie ferme")
            return
        async with self._write_lock:
            for frame in frames:
                if not protocol.is_valid(bytes.fromhex(frame)):
                    _LOGGER.error("Trame a emettre invalide : %s", frame)
                    continue
                payload = bytes.fromhex(frame)
                for _ in range(TX_REPEAT):
                    self._transport.write(payload)
                    await asyncio.sleep(TX_DELAY)

    # ---------------------------------------------------------------- persist
    async def _async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.accepted = {}
        self.names = {}
        for d in data.get(CONF_DISCOVERED, []):
            self.accepted[d["id"]] = set(d.get("kinds", []))
            if d.get("name"):
                self.names[d["id"]] = d["name"]
        self.banned = set(data.get(CONF_BANNED, []))

    @callback
    def _data_to_save(self) -> dict:
        return {
            CONF_DISCOVERED: [
                {"id": i, "kinds": sorted(k), "name": self.names.get(i)}
                for i, k in self.accepted.items()
            ],
            CONF_BANNED: sorted(self.banned),
        }

    @callback
    def _persist(self) -> None:
        # sauvegarde debattue (1 s) : ne declenche PAS de rechargement de l'entree
        self._store.async_delay_save(self._data_to_save, 1)
