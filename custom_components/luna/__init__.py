"""The Luna integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import LunaClient

PLATFORMS = (Platform.CONVERSATION,)

type LunaConfigEntry = ConfigEntry[LunaClient]


async def async_setup_entry(hass: HomeAssistant, entry: LunaConfigEntry) -> bool:
    """Set up Luna from a config entry."""
    entry.runtime_data = LunaClient(async_get_clientsession(hass), entry.data[CONF_URL])
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LunaConfigEntry) -> bool:
    """Unload a Luna config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
