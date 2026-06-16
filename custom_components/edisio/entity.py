"""Classe de base pour les recepteurs Edisio pilotables."""
from __future__ import annotations

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.device_info import DeviceInfo

from . import models, protocol
from .const import CONF_CHANNEL, CONF_EDISIO_ID, CONF_MODEL, CONF_NAME, DOMAIN
from .gateway import EdisioGateway


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
        )

    async def _send(self, action: str, slider: int | None = None) -> None:
        template = self._model["frames"].get(action)
        if not template:
            return
        await self._gateway.async_send(
            protocol.render(template, self._id, self._channel, slider)
        )

    @staticmethod
    def devices_for(entry, platform: str) -> list[dict]:
        from .const import CONF_DEVICES
        return [
            d for d in entry.options.get(CONF_DEVICES, [])
            if models.model(d[CONF_MODEL]) and models.model(d[CONF_MODEL])["platform"] == platform
        ]
