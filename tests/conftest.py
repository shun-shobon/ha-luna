"""Shared pytest configuration for Luna."""

from collections.abc import Generator

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

pytest_plugins = ("pytest_homeassistant_custom_component",)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable loading integrations from custom_components."""
    yield


@pytest.fixture(autouse=True)
async def setup_core_integration(hass: HomeAssistant) -> None:
    """Load the core integration that a running Home Assistant always has.

    The conversation integration reads exposed entities from it during setup.
    """
    assert await async_setup_component(hass, "homeassistant", {})
