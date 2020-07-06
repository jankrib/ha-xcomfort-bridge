"""The Eaton xComfort Bridge integration."""
import asyncio
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_IP_ADDRESS,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from xcomfort import Bridge

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_IP_ADDRESS): cv.string,
                vol.Required("authkey"): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = ["light"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Eaton xComfort Bridge component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Eaton xComfort Bridge from a config entry."""

    ip_address = entry.data.get(CONF_IP_ADDRESS)
    auth_key = entry.data.get("authkey")

    bridge = Bridge(ip_address, auth_key)
    # bridge.logger = lambda x: _LOGGER.warning(x)
    # hass.async_create_task(bridge.run())
    asyncio.create_task(bridge.run())

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = bridge

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""

    bridge = hass.data[DOMAIN][entry.entry_id]

    bridge.close()

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
