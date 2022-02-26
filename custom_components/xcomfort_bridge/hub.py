"""Class used to communicate with xComfort bridge."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from xcomfort.bridge import Bridge, State
from xcomfort.devices import Light, LightState
from .rctouch import RcTouch, RcTouchState

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERBOSE

_LOGGER = logging.getLogger(__name__)

"""Logging function."""
def log(msg: str):
    if VERBOSE:
        _LOGGER.info(msg)


"""Wrapper class over bridge library to emulate hub."""
class XComfortHub:
    def __init__(self, hass: HomeAssistant, identifier: str, ip: str, auth_key: str):
        """Initialize underlying bridge"""
        bridge = XComfortBridge(ip, auth_key)
        self.bridge = bridge
        self.identifier = identifier
        if self.identifier is None:
            self.identifier = ip
        self._id = ip
        self.devices = list()
        log("getting event loop")
        self._loop = asyncio.get_event_loop()

    def start(self):
        """Starts the event loop running the bridge."""
        asyncio.create_task(self.bridge.run())

    async def stop(self):
        """Stops the bridge event loop.
        Will also shut down websocket, if open."""
        await self.bridge.close()

    async def load_devices(self):
        """Loads devices from bridge."""
        log("loading devices")
        devs = await self.bridge.get_devices()
        self.devices = devs.values()
        log(f"loaded {len(self.devices)} devices")

    @property
    def hub_id(self) -> str:
        return self._id

    async def test_connection(self) -> bool:
        await asyncio.sleep(1)
        return True

    @staticmethod
    def get_hub(hass: HomeAssistant, entry: ConfigEntry) -> XComfortHub:
        return hass.data[DOMAIN][entry.entry_id]


"""Low-level library that handles incoming data from websocket."""
class XComfortBridge(Bridge):
    def __init__(self, ip_address: str, authkey: str, session=None):
        super().__init__(ip_address, authkey, session)
        self._devicelist = {}
        self._roomHeatinglist = {}
        self._comps = {}

    def _add_device(self, device):
        self._devices[device.device_id] = device            

    def _handle_SET_STATE_INFO(self, payload):
        for item in payload['item']:
            if 'deviceId' in item:
                deviceId = item['deviceId']
                if deviceId in self._devices:
                    device = self._devices[deviceId]

                    if isinstance(device, Light):
                        device.state.on_next(LightState(item['switch'], item['dimmvalue']))     
                    if isinstance(device, RcTouch):
                        device.state.on_next(RcTouchState(payload))                        

    def _handle_SET_ALL_DATA(self, payload):
        
        if "devices" in payload:
            for device in payload["devices"]:
                self._devicelist[device['deviceId']] = device
        if "roomHeating" in payload:
            for rh in payload["roomHeating"]:
                self._roomHeatinglist[rh['roomId']] = rh
        if "comps" in payload:
            for comp in payload["comps"]:
                self._comps[comp['compId']] = comp

    def _handle_SET_HOME_DATA(self, payload):                
        for device in self._devicelist.values():
            device_id = device["deviceId"]
            name = device["name"]                
            dev_type = device["devType"]            
            if dev_type == 100 or dev_type == 101:                    
                state = LightState(device["switch"], device["dimmvalue"])
                thing = self._devices.get(device_id)
                if thing is not None:
                    log(f"updating light {device_id},{name} {state}")
                    thing.state.on_next(state)
                else:
                    dimmable = device["dimmable"]
                    log(f"adding light {device_id},{name} {state}")
                    light = Light(self, device_id, name, dimmable, state)
                    self._add_device(light)
            elif dev_type == 450:
                rh = self.getRoomHeating(device_id)                                                            
                state = RcTouchState(device,float(rh['power']),float(rh['setpoint']),rh['currentMode'])
                
                thing = self._devices.get(device_id)
                if thing is not None:
                    log(f"updating rc touch {device_id},{name} {state}")
                    thing.state.on_next(state)
                else:
                    log(f"adding rc touch {device_id},{name} {state}")
                    rctouch = RcTouch(self,device_id,name,device,state)
                    self._add_device(rctouch)

            else:            
                log(f"Unknown device type {dev_type} named '{name}' - Skipped")

        self.state = State.Ready

    def getComp(self, compId):
        for comp in self._comps.values():
            if comp["compId"] == compId:
                return comp
    def getRoomHeating(self, sensorId):
        for rh in self._roomHeatinglist.values():
            if rh["roomSensorId"] == sensorId:
                return rh

