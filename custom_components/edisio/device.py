"""Helpers d'appareils : passerelle (hub) et emetteurs rattaches au hub."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER


def gateway_id(entry_id: str) -> tuple[str, str]:
    """Identifiant de l'appareil passerelle (hub) pour une entree donnee."""
    return (DOMAIN, f"gateway_{entry_id}")


def gateway_device_info(entry_id: str, port: str) -> DeviceInfo:
    """DeviceInfo de la passerelle, partagee par ses entites de diagnostic."""
    return DeviceInfo(
        identifiers={gateway_id(entry_id)},
        manufacturer=MANUFACTURER,
        name=f"Passerelle Edisio ({port})",
    )


def emitter_device_info(
    entry_id: str, dev_id: str, name: str | None = None
) -> DeviceInfo:
    """DeviceInfo d'un emetteur decouvert, rattache au hub via via_device."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"emitter_{dev_id}")},
        manufacturer=MANUFACTURER,
        name=name or f"Edisio {dev_id}",
        via_device=gateway_id(entry_id),
    )
