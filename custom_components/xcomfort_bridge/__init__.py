"""Support for XComfort Bridge."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS,Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import CONF_AUTH_KEY, CONF_IDENTIFIER, DOMAIN
from .hub import XComfortHub

PLATFORMS = [Platform.LIGHT, Platform.CLIMATE, Platform.SENSOR, Platform.COVER]


_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Boilerplate."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Connects to bridge and loads devices."""
    config = entry.data
    identifier = str(config.get(CONF_IDENTIFIER))
    ip = str(config.get(CONF_IP_ADDRESS))
    auth_key = str(config.get(CONF_AUTH_KEY))

    hub = XComfortHub(hass, identifier=identifier, ip=ip, auth_key=auth_key)
    hub.start()
    hass.data[DOMAIN][entry.entry_id] = hub

    await hub.load_devices()

    await hass.config_entries.async_forward_entry_setups (entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Disconnects from bridge and removes devices loaded."""
    hub = XComfortHub.get_hub(hass, entry)
    await hub.stop()

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
