"""Classe de base pour les recepteurs Edisio pilotables."""
from __future__ import annotations

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.device_registry import DeviceInfo

from . import models, protocol
from .const import (
    CONF_CHANNEL, CONF_DEVICES, CONF_EDISIO_ID, CONF_MODEL, CONF_NAME, DOMAIN,
    SUBENTRY_TYPE_DEVICE,
)
from .device import gateway_id
from .gateway import EdisioGateway


def expand_channels(data: dict) -> list[dict]:
    """Developpe un module (sous-entree) en un dict par canal du modele."""
    model = models.model(data[CONF_MODEL])
    if not model:
        return []
    base = data[CONF_NAME]
    multi = len(model["channels"]) > 1
    return [
        {
            CONF_NAME: f"{base} C{ch}" if multi else base,
            CONF_MODEL: data[CONF_MODEL],
            CONF_CHANNEL: ch,
            CONF_EDISIO_ID: data[CONF_EDISIO_ID],
        }
        for ch in model["channels"]
    ]


class EdisioReceiver(Entity):
    """Base : detient la config, le modele et l'emission de trames."""

    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(self, gateway: EdisioGateway, dev: dict):
        self._gateway = gateway
        self._dev = dev
        self._model = models.model(dev[CONF_MODEL])
        self._id = dev[CONF_EDISIO_ID]
        self._channel = dev.get(CONF_CHANNEL, 1)
        self._attr_name = dev[CONF_NAME]
        self._attr_unique_id = (
            f"{DOMAIN}_{self._id}_{self._channel}_{self._model['platform']}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            manufacturer="Edisio",
            model=self._model["name"],
            name=dev[CONF_NAME].rsplit(" C", 1)[0],
            via_device=gateway_id(gateway.entry.entry_id),
        )

    async def _send(self, action: str, slider: int | None = None) -> None:
        template = self._model["frames"].get(action)
        if not template:
            return
        await self._gateway.async_send(
            protocol.render(template, self._id, self._channel, slider)
        )

    @staticmethod
    def groups_for(entry, platform: str) -> list[tuple[str | None, list[dict]]]:
        """Récepteurs d'une plateforme, groupés par source.

        Retourne une liste de couples ``(config_subentry_id | None, [dicts])`` :
        - ``None`` pour les récepteurs « legacy » stockés dans les options
          (compat : installations d'avant les sous-entrées) ;
        - l'``id`` de la sous-entrée pour ceux ajoutés via *Ajouter un appareil*.
        """
        groups: list[tuple[str | None, list[dict]]] = []

        legacy = [
            d for d in entry.options.get(CONF_DEVICES, [])
            if models.model(d[CONF_MODEL])
            and models.model(d[CONF_MODEL])["platform"] == platform
        ]
        if legacy:
            groups.append((None, legacy))

        for sub_id, sub in entry.subentries.items():
            if sub.subentry_type != SUBENTRY_TYPE_DEVICE:
                continue
            model = models.model(sub.data.get(CONF_MODEL))
            if not model or model["platform"] != platform:
                continue
            chans = expand_channels(dict(sub.data))
            if chans:
                groups.append((sub_id, chans))

        return groups
