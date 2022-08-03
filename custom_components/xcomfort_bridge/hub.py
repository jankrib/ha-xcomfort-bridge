"""Class used to communicate with xComfort bridge."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from xcomfort.bridge import Bridge, State
from xcomfort.devices import Light, LightState

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
        bridge = Bridge(ip, auth_key)
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

        log("loading rooms")

        rooms = await self.bridge.get_rooms()
        self.rooms = rooms.values()

        log(f"loaded {len(self.rooms)} rooms")

    @property
    def hub_id(self) -> str:
        return self._id

    async def test_connection(self) -> bool:
        await asyncio.sleep(1)
        return True

    @staticmethod
    def get_hub(hass: HomeAssistant, entry: ConfigEntry) -> XComfortHub:
        return hass.data[DOMAIN][entry.entry_id]
