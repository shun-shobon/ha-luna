"""Conversation agent that forwards Assist requests to Luna."""

import logging
from typing import Literal, override

from homeassistant.components import conversation
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import intent
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LunaConfigEntry
from .client import LunaConversationRequest, LunaError, LunaErrorReason
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_ERROR_SPEECH_EN = {
    LunaErrorReason.TIMEOUT: "Luna did not reply in time.",
    LunaErrorReason.CANNOT_CONNECT: "Could not connect to Luna.",
    LunaErrorReason.UNAVAILABLE: "Luna is shutting down.",
    LunaErrorReason.EXECUTION_FAILED: "Luna failed to process the request.",
    LunaErrorReason.INVALID_RESPONSE: "Luna returned an invalid response.",
}
_ERROR_SPEECH_JA = {
    LunaErrorReason.TIMEOUT: "ルナから時間内に返事がありませんでした。",
    LunaErrorReason.CANNOT_CONNECT: "ルナに接続できませんでした。",
    LunaErrorReason.UNAVAILABLE: "ルナは停止処理中です。",
    LunaErrorReason.EXECUTION_FAILED: "ルナが処理に失敗しました。",
    LunaErrorReason.INVALID_RESPONSE: "ルナから不正な応答が返りました。",
}


def _error_speech(reason: LunaErrorReason, language: str) -> str:
    if language.split("-", 1)[0].lower() == "ja":
        return _ERROR_SPEECH_JA[reason]
    return _ERROR_SPEECH_EN[reason]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LunaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Luna conversation entity."""
    async_add_entities([LunaConversationEntity(entry)])


class LunaConversationEntity(conversation.ConversationEntity):
    """Conversation agent backed by Luna."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    def __init__(self, entry: LunaConfigEntry) -> None:
        """Initialize the entity."""
        self._client = entry.runtime_data
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    @override
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return the supported languages."""
        return MATCH_ALL

    @override
    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Send the utterance to Luna and return its reply."""
        response = intent.IntentResponse(language=user_input.language)
        try:
            reply = await self._client.async_converse(
                await self._async_build_request(user_input, chat_log)
            )
        except LunaError as err:
            _LOGGER.error("Luna conversation request failed: %s", err)
            response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                _error_speech(err.reason, user_input.language),
            )
            return conversation.ConversationResult(
                response=response, conversation_id=chat_log.conversation_id
            )

        chat_log.async_add_assistant_content_without_tools(
            conversation.AssistantContent(
                agent_id=user_input.agent_id, content=reply.speech
            )
        )
        response.async_set_speech(reply.speech or "")
        return conversation.ConversationResult(
            response=response,
            conversation_id=chat_log.conversation_id,
            continue_conversation=reply.continue_conversation,
        )

    async def _async_build_request(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> LunaConversationRequest:
        device = (
            dr.async_get(self.hass).async_get(user_input.device_id)
            if user_input.device_id is not None
            else None
        )
        area = (
            ar.async_get(self.hass).async_get_area(device.area_id)
            if device is not None and device.area_id is not None
            else None
        )
        user = (
            await self.hass.auth.async_get_user(user_input.context.user_id)
            if user_input.context.user_id is not None
            else None
        )
        return {
            "text": user_input.text,
            "language": user_input.language,
            "conversation_id": chat_log.conversation_id,
            "device_id": user_input.device_id,
            "satellite_id": user_input.satellite_id,
            "device_name": (
                (device.name_by_user or device.name) if device is not None else None
            ),
            "area_name": area.name if area is not None else None,
            "user_name": user.name if user is not None else None,
        }
