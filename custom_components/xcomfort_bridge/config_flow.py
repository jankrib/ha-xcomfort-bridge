"""Config flow for Eaton xComfort Bridge."""
import logging
from typing import List, Optional

from aiohttp import ClientConnectionError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_MONITORED_CONDITIONS,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client, config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CONF_AUTH_KEY, CONF_IDENTIFIER, DOMAIN

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class XComfortBridgeConfigFlow(config_entries.ConfigFlow):

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        self.data = {}

    async def async_step_user(self, user_input=None):

        entries = self.hass.config_entries.async_entries(DOMAIN)
        if entries:
            return self.async_abort(reason="already_setup")

        errors = {}

        if user_input is not None:

            self.data[CONF_IP_ADDRESS] = user_input[CONF_IP_ADDRESS]
            self.data[CONF_AUTH_KEY] = user_input[CONF_AUTH_KEY]
            self.data[CONF_IDENTIFIER] = user_input.get(CONF_IDENTIFIER)

            await self.async_set_unique_id(self.data[CONF_IP_ADDRESS])

            return self.async_create_entry(
                title=f"{user_input[CONF_IP_ADDRESS]}",
                data=user_input,
            )

        data_schema = {
            vol.Required(CONF_IP_ADDRESS): str,
            vol.Required(CONF_AUTH_KEY): str,
            vol.Optional(CONF_IDENTIFIER, default="XComfort Bridge"): str,
        }

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )

    async def async_step_import(self, import_data: dict):
        return await self.async_step_user(import_data)
