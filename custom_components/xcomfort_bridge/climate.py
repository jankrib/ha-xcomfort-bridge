import logging
from math import ceil

import rx
from xcomfort.connection import Messages
from xcomfort.bridge import Bridge, Room

from homeassistant.components.climate import ClimateEntity
from .hub import XComfortHub
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
from homeassistant.const import (
    TEMP_CELSIUS,
)

# HA_TO_XCOMF_PRESET = {
#     'Protection': 1,
#     PRESET_ECO: 2,
#     PRESET_COMFORT: 3,    
# }


SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE #| SUPPORT_PRESET_MODE

from .const import DOMAIN, VERBOSE

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

    rcts= list()
    for room in rooms:
        if room.state.value.setpoint is not None:
            #_LOGGER.info(f"Adding {room}")
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

        self._unique_id = f"climate_{DOMAIN}_{hub.identifier}-{room.room_id}"
    
    async def async_added_to_hass(self):
        log(f"Added to hass {self._name} ")
        if self._room.state is None:
            log(f"State is null for {self._name}")
        else:
            self._room.state.subscribe(lambda state: self._state_change(state))

    def _state_change(self, state):
        self._state = state        
        should_update = self._state is not None

        log(f"State changed {self._name} : {state}")

        if should_update:
            self.schedule_update_ha_state()

    async def async_set_preset_mode(self, preset_mode):
        log(f"Set Preset mode {preset_mode}")
        # await self.hub.bridge.connection.send_message(Messages.SET_HEATING_STATE,{             
        #     "roomId" :self._room.room_id,
        #     "mode" : self._state.raw.mode,
        #     "state" : self._state.raw.state,            
        #     "confirmed": False})

    async def async_set_temperature(self, **kwargs):
        log(f"Set temperature {kwargs}") 
        await self._room.set_target_temperature(kwargs['temperature'])
    
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
        return self._state.temperature

    @property
    def hvac_mode(self):
        return HVAC_MODE_AUTO

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return int(self._state.humidity)
    
    @property
    def hvac_action(self):
        if(self._state.power > 0):
            return CURRENT_HVAC_HEAT	
        else:
            return CURRENT_HVAC_IDLE
    
    @property
    def target_temperature(self):
        """Returns the setpoint from RC touch, e.g. target_temperature"""
        return self._state.setpoint

    @property
    def preset_modes(self):
        return ['Protection', PRESET_ECO, PRESET_COMFORT]

    @property
    def preset_mode(self):
        mode = self._state.raw.get("mode")
        if mode == 0:
            return 'Protection'
        if mode == 1:
            return 'Protection'
        if mode == 2:
            return PRESET_ECO
        if mode == 3:
            return PRESET_COMFORT

