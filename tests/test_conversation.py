"""Tests for the Luna conversation agent."""

from typing import Any

import pytest
from aiohttp import ClientConnectionError
from homeassistant.components import conversation
from homeassistant.const import CONF_URL
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import intent
from homeassistant.helpers.chat_session import async_get_chat_session
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.luna.const import DOMAIN

LUNA_URL = "http://luna.local:3000"
ENDPOINT = f"{LUNA_URL}/home-assistant/conversation"
AGENT_ID = "conversation.luna"


@pytest.fixture(autouse=True)
async def setup_luna(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> MockConfigEntry:
    """Set up a Luna entry whose HTTP session is the mocked one."""
    entry = MockConfigEntry(domain=DOMAIN, title="Luna", data={CONF_URL: LUNA_URL})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def converse(
    hass: HomeAssistant,
    *,
    context: Context | None = None,
    device_id: str | None = None,
    satellite_id: str | None = None,
    language: str = "ja",
) -> conversation.ConversationResult:
    return await conversation.async_converse(
        hass,
        "電気消して",
        None,
        context or Context(),
        language=language,
        agent_id=AGENT_ID,
        device_id=device_id,
        satellite_id=satellite_id,
    )


def sent_body(aioclient_mock: AiohttpClientMocker) -> dict[str, Any]:
    assert aioclient_mock.call_count == 1
    method, url, body, _headers = aioclient_mock.mock_calls[0]
    assert method == "POST"
    assert str(url) == ENDPOINT
    assert isinstance(body, dict)
    return body


def last_assistant_content(
    hass: HomeAssistant, conversation_id: str
) -> conversation.Content:
    with (
        async_get_chat_session(hass, conversation_id) as session,
        conversation.async_get_chat_log(hass, session) as chat_log,
    ):
        return chat_log.content[-1]


async def test_reply_is_spoken_and_recorded(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Luna's speech becomes the Assist response and the chat log content."""
    aioclient_mock.post(
        ENDPOINT, json={"speech": "消したよ", "continue_conversation": False}
    )

    result = await converse(hass)

    assert result.response.response_type is intent.IntentResponseType.ACTION_DONE
    assert result.response.speech["plain"]["speech"] == "消したよ"
    assert result.continue_conversation is False
    assert result.conversation_id is not None
    assert sent_body(aioclient_mock)["conversation_id"] == result.conversation_id
    content = last_assistant_content(hass, result.conversation_id)
    assert isinstance(content, conversation.AssistantContent)
    assert content.agent_id == AGENT_ID
    assert content.content == "消したよ"


async def test_null_speech_is_silent(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A null speech is a successful turn with nothing to read aloud."""
    aioclient_mock.post(ENDPOINT, json={"speech": None, "continue_conversation": False})

    result = await converse(hass)

    assert result.response.response_type is intent.IntentResponseType.ACTION_DONE
    assert result.response.speech["plain"]["speech"] == ""
    assert result.continue_conversation is False
    assert result.conversation_id is not None
    content = last_assistant_content(hass, result.conversation_id)
    assert isinstance(content, conversation.AssistantContent)
    assert content.content is None


async def test_continue_conversation_is_passed_through(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Luna can keep the satellite listening for a follow-up."""
    aioclient_mock.post(
        ENDPOINT, json={"speech": "どの部屋？", "continue_conversation": True}
    )

    result = await converse(hass)

    assert result.response.speech["plain"]["speech"] == "どの部屋？"
    assert result.continue_conversation is True


async def test_follow_up_turn_reuses_conversation_id(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A follow-up turn sends the same conversation ID to Luna."""
    aioclient_mock.post(
        ENDPOINT, json={"speech": "どの部屋？", "continue_conversation": True}
    )
    first = await converse(hass)

    second = await conversation.async_converse(
        hass, "リビング", first.conversation_id, Context(), "ja", AGENT_ID
    )

    assert second.conversation_id == first.conversation_id
    bodies = [call[2] for call in aioclient_mock.mock_calls]
    assert [body["conversation_id"] for body in bodies] == [first.conversation_id] * 2
    assert bodies[1]["text"] == "リビング"


@pytest.mark.parametrize(
    ("mock", "speech"),
    [
        pytest.param(
            {"exc": TimeoutError()},
            "ルナから時間内に返事がありませんでした。",
            id="timeout",
        ),
        pytest.param(
            {"exc": ClientConnectionError()},
            "ルナに接続できませんでした。",
            id="cannot_connect",
        ),
        pytest.param(
            {"status": 503, "json": {"error": "unavailable"}},
            "ルナは停止処理中です。",
            id="unavailable",
        ),
        pytest.param(
            {"status": 500, "json": {"error": "execution_failed"}},
            "ルナが処理に失敗しました。",
            id="execution_failed",
        ),
        pytest.param(
            {"status": 400, "json": {"error": "invalid_request"}},
            "ルナから不正な応答が返りました。",
            id="invalid_request",
        ),
        pytest.param(
            {"status": 415, "text": ""},
            "ルナから不正な応答が返りました。",
            id="unsupported_media_type",
        ),
        pytest.param(
            {"text": "<html>not json</html>"},
            "ルナから不正な応答が返りました。",
            id="malformed_json",
        ),
        pytest.param(
            {"json": ["speech"]},
            "ルナから不正な応答が返りました。",
            id="not_an_object",
        ),
        pytest.param(
            {"json": {"continue_conversation": False}},
            "ルナから不正な応答が返りました。",
            id="missing_speech",
        ),
        pytest.param(
            {"json": {"speech": "消したよ"}},
            "ルナから不正な応答が返りました。",
            id="missing_continue_conversation",
        ),
        pytest.param(
            {"json": {"speech": 1, "continue_conversation": False}},
            "ルナから不正な応答が返りました。",
            id="speech_not_string",
        ),
        pytest.param(
            {"json": {"speech": "消したよ", "continue_conversation": "false"}},
            "ルナから不正な応答が返りました。",
            id="continue_conversation_not_bool",
        ),
    ],
)
async def test_failure_returns_error_response(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
    mock: dict[str, Any],
    speech: str,
) -> None:
    """Every failure becomes an Assist error and is logged."""
    aioclient_mock.post(ENDPOINT, **mock)

    result = await converse(hass)

    assert result.response.response_type is intent.IntentResponseType.ERROR
    assert result.response.error_code is intent.IntentResponseErrorCode.UNKNOWN
    assert result.response.speech["plain"]["speech"] == speech
    assert result.continue_conversation is False
    assert result.conversation_id == sent_body(aioclient_mock)["conversation_id"]
    assert "Luna conversation request failed" in caplog.text


async def test_failure_speech_is_english_for_other_languages(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Languages other than Japanese get the English error speech."""
    aioclient_mock.post(ENDPOINT, exc=TimeoutError())

    result = await converse(hass, language="en")

    assert result.response.speech["plain"]["speech"] == "Luna did not reply in time."


async def test_entity_supports_control(hass: HomeAssistant) -> None:
    """The prefer-local-intents option is offered for this agent."""
    state = hass.states.get(AGENT_ID)

    assert state is not None
    assert (
        state.attributes["supported_features"]
        == conversation.ConversationEntityFeature.CONTROL
    )


async def test_request_includes_device_area_and_user_names(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Names are resolved from the registries and Home Assistant users."""
    other_entry = MockConfigEntry(domain="test")
    other_entry.add_to_hass(hass)
    area = ar.async_get(hass).async_create("リビング")
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=other_entry.entry_id,
        identifiers={("test", "voice-pe")},
        name="Home Assistant Voice",
    )
    device_registry.async_update_device(
        device.id, name_by_user="リビングの Voice PE", area_id=area.id
    )
    user = await hass.auth.async_create_user("しゅん")
    aioclient_mock.post(
        ENDPOINT, json={"speech": "消したよ", "continue_conversation": False}
    )

    result = await converse(
        hass,
        context=Context(user_id=user.id),
        device_id=device.id,
        satellite_id="assist_satellite.living_room",
    )

    assert sent_body(aioclient_mock) == {
        "text": "電気消して",
        "language": "ja",
        "conversation_id": result.conversation_id,
        "device_id": device.id,
        "satellite_id": "assist_satellite.living_room",
        "device_name": "リビングの Voice PE",
        "area_name": "リビング",
        "user_name": "しゅん",
    }


async def test_device_name_falls_back_to_integration_name(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Without a user-given name the device's own name is sent, and no area."""
    other_entry = MockConfigEntry(domain="test")
    other_entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=other_entry.entry_id,
        identifiers={("test", "voice-pe")},
        name="Home Assistant Voice",
    )
    aioclient_mock.post(
        ENDPOINT, json={"speech": "消したよ", "continue_conversation": False}
    )

    await converse(hass, device_id=device.id)

    body = sent_body(aioclient_mock)
    assert body["device_name"] == "Home Assistant Voice"
    assert body["area_name"] is None


@pytest.mark.parametrize(
    ("context", "device_id"),
    [
        pytest.param(Context(), None, id="no_device_no_user"),
        pytest.param(Context(user_id="missing-user"), "missing-device", id="unknown"),
    ],
)
async def test_unresolved_names_are_null(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    context: Context,
    device_id: str | None,
) -> None:
    """Names Home Assistant cannot resolve are sent as null."""
    aioclient_mock.post(
        ENDPOINT, json={"speech": "消したよ", "continue_conversation": False}
    )

    result = await converse(hass, context=context, device_id=device_id)

    assert sent_body(aioclient_mock) == {
        "text": "電気消して",
        "language": "ja",
        "conversation_id": result.conversation_id,
        "device_id": device_id,
        "satellite_id": None,
        "device_name": None,
        "area_name": None,
        "user_name": None,
    }
