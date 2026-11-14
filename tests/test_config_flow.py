"""Tests for the Luna config flow."""

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.luna.const import DOMAIN


@pytest.mark.parametrize(
    ("entered", "stored"),
    [
        ("http://luna.local:3000", "http://luna.local:3000"),
        ("  http://luna.local:3000/  ", "http://luna.local:3000"),
        ("https://luna.example/base//", "https://luna.example/base"),
    ],
)
async def test_user_step_creates_entry_with_normalized_url(
    hass: HomeAssistant, entered: str, stored: str
) -> None:
    """A valid URL is stored without surrounding spaces or trailing slashes."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: entered}
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Luna"
    assert result["data"] == {CONF_URL: stored}


@pytest.mark.parametrize(
    "entered",
    [
        "luna.local:3000",
        "localhost:3000",
        "ftp://luna.local",
        "http://",
        "http:///path",
        "http://luna.local:99999",
        "http://luna.local:3000/?token=x",
        "http://luna.local:3000/#top",
        "not a url",
        "",
    ],
)
async def test_user_step_rejects_invalid_url(hass: HomeAssistant, entered: str) -> None:
    """An unusable URL keeps the form open with an error on the URL field."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: entered}
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {CONF_URL: "invalid_url"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: "http://luna.local:3000"}
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY


async def test_user_step_aborts_when_already_configured(hass: HomeAssistant) -> None:
    """Only one Luna entry can exist."""
    MockConfigEntry(
        domain=DOMAIN, title="Luna", data={CONF_URL: "http://luna.local:3000"}
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
