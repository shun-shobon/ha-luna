"""Client for Luna's Home Assistant conversation endpoint."""

import json
from dataclasses import dataclass
from enum import StrEnum
from http import HTTPStatus
from typing import TypedDict

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import CONVERSATION_PATH, REQUEST_TIMEOUT


class LunaConversationRequest(TypedDict):
    text: str
    language: str
    conversation_id: str
    device_id: str | None
    satellite_id: str | None
    device_name: str | None
    area_name: str | None
    user_name: str | None


@dataclass(frozen=True, slots=True)
class LunaConversationReply:
    speech: str | None
    continue_conversation: bool


class LunaErrorReason(StrEnum):
    TIMEOUT = "timeout"
    CANNOT_CONNECT = "cannot_connect"
    UNAVAILABLE = "unavailable"
    EXECUTION_FAILED = "execution_failed"
    INVALID_RESPONSE = "invalid_response"


class LunaError(Exception):
    """Raised when Luna does not return a usable conversation reply."""

    def __init__(self, reason: LunaErrorReason, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason


class LunaClient:
    def __init__(self, session: ClientSession, base_url: str) -> None:
        self._session = session
        self._endpoint = f"{base_url}{CONVERSATION_PATH}"

    async def async_converse(
        self, request: LunaConversationRequest
    ) -> LunaConversationReply:
        try:
            async with self._session.post(
                self._endpoint,
                json=request,
                timeout=ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                status = response.status
                body = await response.text()
        except TimeoutError as err:
            raise LunaError(
                LunaErrorReason.TIMEOUT, f"no reply within {REQUEST_TIMEOUT} seconds"
            ) from err
        except ClientError as err:
            raise LunaError(LunaErrorReason.CANNOT_CONNECT, repr(err)) from err

        if status == HTTPStatus.SERVICE_UNAVAILABLE:
            raise LunaError(LunaErrorReason.UNAVAILABLE, body)
        if status == HTTPStatus.INTERNAL_SERVER_ERROR:
            raise LunaError(LunaErrorReason.EXECUTION_FAILED, body)
        if status != HTTPStatus.OK:
            raise LunaError(LunaErrorReason.INVALID_RESPONSE, f"HTTP {status}: {body}")
        return _parse_reply(body)


def _parse_reply(body: str) -> LunaConversationReply:
    try:
        payload = json.loads(body)
    except ValueError as err:
        raise LunaError(
            LunaErrorReason.INVALID_RESPONSE, f"body is not JSON: {body}"
        ) from err
    if not isinstance(payload, dict) or "speech" not in payload:
        raise LunaError(LunaErrorReason.INVALID_RESPONSE, f"unexpected body: {body}")
    speech = payload["speech"]
    continue_conversation = payload.get("continue_conversation")
    if not (speech is None or isinstance(speech, str)) or not isinstance(
        continue_conversation, bool
    ):
        raise LunaError(LunaErrorReason.INVALID_RESPONSE, f"unexpected body: {body}")
    return LunaConversationReply(
        speech=speech, continue_conversation=continue_conversation
    )
