"""Sensor platform for FireServiceRota integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import HomeAssistantType

from .const import DOMAIN as FIRESERVICEROTA_DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up FireServiceRota sensor based on a config entry."""
    coordinator = hass.data[FIRESERVICEROTA_DOMAIN][entry.entry_id]

    async_add_entities([IncidentsSensor(coordinator)])


class IncidentsSensor(RestoreEntity):
    """Representation of FireServiceRota incidents sensor."""

    def __init__(self, coordinator):
        """Initialize."""
        self._coordinator = coordinator
        self._entry_id = self._coordinator._entry.entry_id
        self._unique_id = f"{self._coordinator._entry.unique_id}_Incidents"
        self._state = None
        self._state_attributes = {}

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Incidents"

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        if (
            "prio" in self._state_attributes
            and self._state_attributes["prio"][0] == "a"
        ):
            return "mdi:ambulance"

        return "mdi:fire-truck"

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        return self._state

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def device_state_attributes(self) -> object:
        """Return available attributes for sensor."""
        attr = {}
        data = self._state_attributes

        if not data:
            return attr

        for value in (
            "trigger",
            "created_at",
            "message_to_speech_url",
            "prio",
            "type",
            "responder_mode",
            "can_respond_until",
        ):
            if data.get(value):
                attr[value] = data[value]

            if "address" not in data:
                continue

            for address_value in (
                "latitude",
                "longitude",
                "address_type",
                "formatted_address",
            ):
                if address_value in data["address"]:
                    attr[address_value] = data["address"][address_value]

        return attr

    async def async_added_to_hass(self) -> None:
        """Run when about to be added to hass."""
        await super().async_added_to_hass()

        state = await self.async_get_last_state()
        if state:
            self._state = state.state
            self._state_attributes = state.attributes
            _LOGGER.debug("Restored entity 'Incidents' state to: %s", self._state)

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{FIRESERVICEROTA_DOMAIN}_{self._entry_id}_update",
                self.coordinator_update,
            )
        )

    @callback
    def coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self._coordinator.websocket.incident_data()
        if not data or "body" not in data:
            return

        self._state = data["body"]
        self._state_attributes = data
        self.async_write_ha_state()