"""Config flow for Eaton xComfort Bridge."""
import logging
import asyncio

from homeassistant import config_entries, data_entry_flow
from homeassistant.helpers import config_entry_flow
import voluptuous as vol
from collections import OrderedDict
from homeassistant.const import CONF_IP_ADDRESS

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class XComfortBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    def __init__(self):
        """Initialize."""
        self.data_schema = {
            vol.Required(CONF_IP_ADDRESS): str,
            vol.Required("authkey"): str,
        }

    async def async_step_user(self, user_input):
        """Handle a flow initialized by the user."""

        if user_input is not None:
            # TODO Validate user input

            return self.async_create_entry(
                title=f"{user_input[CONF_IP_ADDRESS]}",
                data={
                    CONF_IP_ADDRESS: user_input[CONF_IP_ADDRESS],
                    "authkey": user_input["authkey"],
                },
            )

        data_schema = OrderedDict()
        data_schema[vol.Required(CONF_IP_ADDRESS)] = str
        data_schema[vol.Required("authkey")] = str

        return self.async_show_form(step_id="user", data_schema=vol.Schema(data_schema))

