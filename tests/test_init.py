"""Tests for setting up and unloading Luna."""

from homeassistant.components.conversation.agent_manager import async_get_agent
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_URL, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.luna.const import DOMAIN


async def test_setup_and_unload_entry(hass: HomeAssistant) -> None:
    """The entry provides one all-language agent until it is unloaded."""
    entry = MockConfigEntry(
        domain=DOMAIN, title="Luna", data={CONF_URL: "http://luna.local:3000"}
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    entity_id = er.async_get(hass).async_get_entity_id(
        "conversation", DOMAIN, entry.entry_id
    )
    assert entity_id == "conversation.luna"
    assert hass.states.get(entity_id) is not None
    agent = async_get_agent(hass, entity_id)
    assert agent is not None
    assert agent.supported_languages == MATCH_ALL

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
