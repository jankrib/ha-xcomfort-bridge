"""Platform for light integration."""
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv

# Import the device class from the component that you want to support
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    SUPPORT_BRIGHTNESS,
    PLATFORM_SCHEMA,
    LightEntity,
)
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_IP_ADDRESS

from xcomfort import Bridge, Light as XLight
from .const import DOMAIN
from math import ceil

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Platform uses config entry setup."""
    pass


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Abode light devices."""
    bridge = hass.data[DOMAIN][entry.entry_id]

    if not isinstance(bridge, Bridge):
        _LOGGER.error(f"Invalid bridge. Got {bridge} for {entry.entry_id}")

    devices = await bridge.get_devices()

    lights = filter(lambda d: isinstance(d, XLight), devices.values())
    lights = map(lambda d: XComfortLight(hass, bridge, d), lights)
    lights = list(lights)

    async_add_entities(lights)


class XComfortDevice(Entity):
    """Representation of an xComfort Device."""

    def __init__(self, hass, bridge: Bridge, device: XLight):
        self.hass = hass
        self._bridge = bridge
        self._device = device

        # self.entity_id = f"light.d{device.device_id}"

        self._name = device.name
        self._state = None
        #self.unique_id = f"light_{device.bridge.connection.device_id}_{device.device_id}"
        self._unique_id = f"light_{DOMAIN}_{device.bridge.connection.device_id}-{device.device_id}"
        self._device.state.subscribe(self._state_change)

    def _state_change(self, state):
        update = self._state is not None
        self._state = state

        _LOGGER.warning(f"_state_change : {state}")

        if update:
            self.schedule_update_ha_state()


class XComfortLight(XComfortDevice, LightEntity):
    """Representation of an xComfort Light."""

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
    def brightness(self):
        """Return the brightness of the light.

        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        return int(255.0 * self._state.dimmvalue / 99.0)

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state.switch

    @property
    def supported_features(self):
        """Flag supported features."""
        if self._device.dimmable:
            return SUPPORT_BRIGHTNESS
        return 0

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        if ATTR_BRIGHTNESS in kwargs and self._device.dimmable:
            # Convert Home Assistant brightness (0-255) to Abode brightness (0-99)
            # If 100 is sent to Abode, response is 99 causing an error
            await self._device.dimm(ceil(kwargs[ATTR_BRIGHTNESS] * 99 / 255.0))
            return

        switch_task = self._device.switch(True)
        self._state.switch = True
        self.schedule_update_ha_state()

        await switch_task

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        switch_task = self._device.switch(False)
        self._state.switch = False
        self.schedule_update_ha_state()

        await switch_task

    def update(self):
        pass

