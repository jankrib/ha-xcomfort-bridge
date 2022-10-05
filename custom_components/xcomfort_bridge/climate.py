import logging

from xcomfort.connection import Messages
from xcomfort.bridge import Room, RctMode, RctState
from homeassistant.components.climate import ClimateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.climate.const import (
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    HVAC_MODE_AUTO,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_PRESET_MODE,
    PRESET_ECO,
    PRESET_COMFORT,
)
from homeassistant.const import TEMP_CELSIUS

from .hub import XComfortHub
from .const import DOMAIN, VERBOSE

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE


_LOGGER = logging.getLogger(__name__)


def log(msg: str):
    if VERBOSE:
        _LOGGER.info(msg)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:

    hub = XComfortHub.get_hub(hass, entry)

    rooms = hub.rooms

    _LOGGER.info(f"Found {len(rooms)} xcomfort rooms")

    rcts = list()
    for room in rooms:
        if room.state.value is not None:
            if room.state.value.setpoint is not None:
                # _LOGGER.info(f"Adding {room}")
                rct = HASSXComfortRcTouch(hass, hub, room)
                rcts.append(rct)

    _LOGGER.info(f"Added {len(rcts)} rc touch units")
    async_add_entities(rcts)
    return


class HASSXComfortRcTouch(ClimateEntity):
    _attr_temperature_unit = TEMP_CELSIUS
    _attr_hvac_modes = [HVAC_MODE_AUTO]
    _attr_supported_features = SUPPORT_FLAGS

    def __init__(self, hass: HomeAssistant, hub: XComfortHub, room: Room):
        self.hass = hass
        self.hub = hub
        self._room = room
        self._name = room.name
        self._state = None

        self.rctpreset = RctMode.Comfort
        self.rctstate = RctState.Idle
        self.temperature = 20.0
        self.currentsetpoint = 20.0

        self._unique_id = f"climate_{DOMAIN}_{hub.identifier}-{room.room_id}"

    async def async_added_to_hass(self):
        log(f"Added to hass {self._name} ")
        if self._room.state is None:
            log(f"State is null for {self._name}")
        else:
            self._room.state.subscribe(lambda state: self._state_change(state))

    def _state_change(self, state):
        self._state = state

        if self._state is not None:
            if "currentMode" in state.raw:
                self.rctpreset = RctMode(state.raw["currentMode"])
            if "mode" in state.raw:
                self.rctpreset = RctMode(state.raw["mode"])
            self.temperature = state.temperature
            self.currentsetpoint = state.setpoint

            log(f"State changed {self._name} : {state}")

            self.schedule_update_ha_state()

    async def async_set_preset_mode(self, preset_mode):
        log(f"Set Preset mode {preset_mode}")

        if preset_mode == "Cool":
            mode = RctMode.Cool
        if preset_mode == PRESET_ECO:
            mode = RctMode.Eco
        if preset_mode == PRESET_COMFORT:
            mode = RctMode.Comfort
        if self.rctpreset != mode:
            await self._room.set_mode(mode)
            self.rctpreset = mode
            self.schedule_update_ha_state()

    async def async_set_temperature(self, **kwargs):
        log(f"Set temperature {kwargs}")

        # TODO: Move everything below into Room class in xcomfort-python library.
        # Latest implementation in the base library is broken, so everything moved here
        # To facilitate easier debugging inside HA.
        # Also consider changing the `mode` object on RoomState class to be just a number,
        # at current it is an object(possibly due to erroneous parsing of the 300/310-messages)
        setpoint = kwargs["temperature"]
        setpointrange = self._room.bridge.rctsetpointallowedvalues[
            RctMode(self.rctpreset)
        ]

        if setpointrange.Max < setpoint:
            setpoint = setpointrange.Max

        if setpoint < setpointrange.Min:
            setpoint = setpointrange.Min

        payload = {
            "roomId": self._room.room_id,
            "mode": self.rctpreset.value,
            "state": self._room.state.value.rctstate.value,
            "setpoint": setpoint,
            "confirmed": False,
        }
        await self._room.bridge.send_message(Messages.SET_HEATING_STATE, payload)
        self._room.modesetpoints[self.rctpreset] = setpoint
        self.currentsetpoint = setpoint
        # After moving everything to base library, ideally line below should be the entry point
        # into the library for setting target temperature.
        # await self._room.set_target_temperature(kwargs["temperature"])

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self._name,
            "manufacturer": "Eaton",
            "model": "RC Touch",
            "via_device": self.hub.hub_id,
        }

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.temperature

    @property
    def hvac_mode(self):
        return HVAC_MODE_AUTO

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return int(self._state.humidity)

    @property
    def hvac_action(self):
        if self._state.power > 0:
            return CURRENT_HVAC_HEAT
        else:
            return CURRENT_HVAC_IDLE

    @property
    def max_temp(self):
        if self._state is None:
            return 40.0
        return self._room.bridge.rctsetpointallowedvalues[self.rctpreset].Max

    @property
    def min_temp(self):
        if self._state is None:
            return 5.0
        return self._room.bridge.rctsetpointallowedvalues[self.rctpreset].Min

    @property
    def target_temperature(self):
        """Returns the setpoint from RC touch, e.g. target_temperature"""
        return self.currentsetpoint

    @property
    def preset_modes(self):
        return ["Cool", PRESET_ECO, PRESET_COMFORT]

    @property
    def preset_mode(self):
        if self.rctpreset == RctMode.Cool:
            return "Cool"
        if self.rctpreset == RctMode.Eco:
            return PRESET_ECO
        if self.rctpreset == RctMode.Comfort:
            return PRESET_COMFORT
