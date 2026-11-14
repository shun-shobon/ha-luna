"""Config flow for Luna."""

from typing import Any, override

import probatio
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_URL
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from yarl import URL

from .const import DOMAIN

STEP_USER_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        )
    }
)


def normalize_url(value: str) -> str | None:
    """Return the URL without trailing slashes, or None if it is not usable."""
    url = value.strip().rstrip("/")
    try:
        parsed = URL(url)
    except ValueError:
        return None
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.host
        or parsed.query_string
        or parsed.fragment
    ):
        return None
    return url


class LunaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Luna config flow."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the base URL of Luna's HTTP API."""
        errors: dict[str, str] = {}
        if user_input is not None:
            url = normalize_url(user_input[CONF_URL])
            if url is not None:
                return self.async_create_entry(title="Luna", data={CONF_URL: url})
            errors[CONF_URL] = "invalid_url"
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, user_input
            ),
            errors=errors,
        )
