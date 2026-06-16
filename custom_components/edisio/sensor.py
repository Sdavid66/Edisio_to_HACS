"""Plateforme sensor : temperature et batterie des modules Edisio (decouverte auto)."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_DISCOVERY, SIGNAL_RX


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    seen: set[str] = set()

    @callback
    def _discovered(data: dict) -> None:
        dev_id = data["id"]
        kinds = data.get("kinds") or set()
        new = []
        has_batt = "battery" in kinds or data.get("battery") is not None
        has_temp = "temperature" in kinds or "temperature" in data
        if has_batt and f"{dev_id}_battery" not in seen:
            seen.add(f"{dev_id}_battery")
            new.append(EdisioBatterySensor(dev_id))
        if has_temp and f"{dev_id}_temp" not in seen:
            seen.add(f"{dev_id}_temp")
            new.append(EdisioTemperatureSensor(dev_id))
        if new:
            async_add_entities(new)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_DISCOVERY, _discovered)
    )


class _Base(SensorEntity):
    _attr_should_poll = False

    def __init__(self, dev_id: str):
        self._dev_id = dev_id

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{SIGNAL_RX}_{self._dev_id}", self._update
            )
        )

    @callback
    def _update(self, data: dict) -> None:
        raise NotImplementedError


class EdisioBatterySensor(_Base):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = True

    def __init__(self, dev_id: str):
        super().__init__(dev_id)
        self._attr_name = f"Edisio {dev_id} batterie"
        self._attr_unique_id = f"{DOMAIN}_{dev_id}_battery"

    @callback
    def _update(self, data: dict) -> None:
        if data.get("battery") is not None:
            self._attr_native_value = data["battery"]
            self.async_write_ha_state()


class EdisioTemperatureSensor(_Base):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, dev_id: str):
        super().__init__(dev_id)
        self._attr_name = f"Edisio {dev_id} temperature"
        self._attr_unique_id = f"{DOMAIN}_{dev_id}_temperature"

    @callback
    def _update(self, data: dict) -> None:
        if "temperature" in data:
            self._attr_native_value = data["temperature"]
            self.async_write_ha_state()
