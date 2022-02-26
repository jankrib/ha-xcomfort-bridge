import logging
from math import ceil

import rx
from xcomfort.connection import Messages

from homeassistant.components.climate import ClimateEntity
from .hub import XComfortHub
from .rctouch import RcTouch
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


SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

from .const import DOMAIN, VERBOSE

_LOGGER = logging.getLogger(__name__)


def log(msg: str):
    if VERBOSE:
        _LOGGER.warning(msg)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:

    hub = XComfortHub.get_hub(hass, entry)

    devices = hub.devices

    _LOGGER.info(f"Found {len(devices)} xcomfort devices")

    rcts= list()
    for device in devices:
        if isinstance(device,RcTouch):
            _LOGGER.info(f"Adding {device}")
            rct = HASSXComfortRcTouch(hass, hub, device)
            rcts.append(rct)

    _LOGGER.info(f"Added {len(rcts)} rc touch units")
    async_add_entities(rcts)
    return


class HASSXComfortRcTouch(ClimateEntity):
    _attr_temperature_unit = TEMP_CELSIUS
    _attr_hvac_modes = [HVAC_MODE_AUTO]
    _attr_supported_features = SUPPORT_FLAGS
    

    def __init__(self, hass: HomeAssistant, hub: XComfortHub, device: RcTouch):
        self.hass = hass
        self.hub = hub
        self._device = device
        self._name = device.name
        self._state = None
        self.device_id = device.device_id
        self._unique_id = f"rctouch_{DOMAIN}_{hub.identifier}-{device.device_id}"

        comp = hub.bridge.getComp(self._device._device["compId"])
        self.versionFW = comp["versionFW"]
        
        rh = hub.bridge.getRoomHeating(self.device_id)
        self.setpoint = float(rh["setpoint"])        
    
    async def async_added_to_hass(self):
        _LOGGER.warning(f"Added to hass {self._name} ")
        if self._device.state is None:
            _LOGGER.warning(f"State is null for {self._name}")
        else:
            self._device.state.subscribe(lambda state: self._state_change(state))

    def _state_change(self, state):
        self._state = state        
        should_update = self._state is not None

        log(f"State changed {self._name} : {state}")

        if should_update:
            self.schedule_update_ha_state()

    async def async_set_preset_mode(self, preset_mode):
        log(f"Set Preset mode {preset_mode}")    
        rh = self.hub.bridge.getRoomHeating(self.device_id)
        await self.hub.bridge.connection.send_message(Messages.SET_HEATING_STATE,{             
            "roomId" :rh['roomId'],
            "mode" : self._state.mode,
            "state" : rh['state'],            
            "confirmed": False})

    async def async_set_temperature(self, **kwargs):        
        log(f"Set temperature {kwargs}") 
        rh = self.hub.bridge.getRoomHeating(self.device_id)
        await self.hub.bridge.connection.send_message(Messages.SET_HEATING_STATE,{             
            "roomId" :rh['roomId'],
            "mode" : self._state.mode,
            "state" : rh['state'],
            "setpoint" : kwargs['temperature'],
            "confirmed": False})
    
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self._name,
            "manufacturer": "Eaton",
            "model": "RC Touch",
            "sw_version": self.versionFW,
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
        return self._state.current_temperature

    @property
    def hvac_mode(self):
        return HVAC_MODE_AUTO

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return int(self._state.current_humidity)
    
    @property
    def hvac_action(self):
        if(self._state.power > 0):
            return CURRENT_HVAC_HEAT	
        else:
            return CURRENT_HVAC_IDLE
    
    @property
    def target_temperature(self):
        """Returns the setpoint from RC touch, e.g. target_temperature"""
        return self.setpoint

    @property
    def preset_modes(self):
        return ['Protection', PRESET_ECO, PRESET_COMFORT]

    @property
    def preset_mode(self):
        if self._state.mode == 0:
            return 'Protection'
        if self._state.mode == 1:
            return 'Protection'
        if self._state.mode == 2:
            return PRESET_ECO
        if self._state.mode == 3:
            return PRESET_COMFORT

