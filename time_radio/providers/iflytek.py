from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import time
from email.utils import formatdate
from urllib.parse import urlencode, urlparse

from websockets.exceptions import WebSocketException
from websockets.sync.client import connect

from time_radio.errors import ErrorDetails, ExternalServiceError
from time_radio.models import IflytekCredentials
from time_radio.retry import retry_async

IFLYTEK_TTS_URL = "wss://tts-api.xfyun.cn/v2/tts"


def build_iflytek_authenticated_url(
    host_url: str,
    api_key: str,
    api_secret: str,
    timestamp_seconds: float,
) -> str:
    parsed_url = urlparse(host_url)
    request_line = f"GET {parsed_url.path} HTTP/1.1"
    date = formatdate(timeval=timestamp_seconds, localtime=False, usegmt=True)
    signature_origin = f"host: {parsed_url.netloc}\ndate: {date}\n{request_line}"
    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")
    authorization_origin = (
        f'api_key="{api_key}",algorithm="hmac-sha256",'
        f'headers="host date request-line",signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
    query = urlencode(
        {
            "authorization": authorization,
            "date": date,
            "host": parsed_url.netloc,
        }
    )
    return f"{host_url}?{query}"


def synthesize_iflytek_sync(text: str, credentials: IflytekCredentials) -> bytes:
    authenticated_url = build_iflytek_authenticated_url(
        host_url=IFLYTEK_TTS_URL,
        api_key=credentials.api_key.get_secret_value(),
        api_secret=credentials.api_secret.get_secret_value(),
        timestamp_seconds=time.time(),
    )
    request_payload = {
        "common": {"app_id": credentials.app_id.get_secret_value()},
        "business": {
            "aue": "lame",
            "sfl": 1,
            "auf": "audio/L16;rate=16000",
            "vcn": credentials.voice,
            "speed": credentials.speed,
            "pitch": credentials.pitch,
            "volume": credentials.volume,
            "tte": "UTF8",
        },
        "data": {
            "status": 2,
            "text": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
        },
    }
    audio_parts: list[bytes] = []
    session_id = "unknown"

    try:
        with connect(
            authenticated_url,
            open_timeout=15,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10,
        ) as websocket:
            websocket.send(json.dumps(request_payload, ensure_ascii=False))
            while True:
                raw_message = websocket.recv(timeout=30)
                if not isinstance(raw_message, str):
                    raise ExternalServiceError(
                        ErrorDetails(
                            code="iflytek_binary_protocol_error",
                            message="iFLYTEK returned an unexpected binary control frame.",
                            status_code=502,
                        )
                    )
                message = json.loads(raw_message)
                session_id = str(message.get("sid", session_id))
                code = int(message.get("code", -1))
                if code != 0:
                    raise ExternalServiceError(
                        ErrorDetails(
                            code="iflytek_tts_error",
                            message=(
                                "iFLYTEK rejected the TTS request. "
                                f"voice={credentials.voice}, code={code}, sid={session_id}, "
                                f"message={message.get('message', '')}"
                            ),
                            status_code=502,
                        )
                    )
                data = message.get("data")
                if not isinstance(data, dict):
                    raise ExternalServiceError(
                        ErrorDetails(
                            code="iflytek_invalid_response",
                            message=f"iFLYTEK returned a response without data. sid={session_id}",
                            status_code=502,
                        )
                    )
                encoded_audio = data.get("audio")
                if isinstance(encoded_audio, str) and encoded_audio:
                    audio_parts.append(base64.b64decode(encoded_audio))
                if int(data.get("status", -1)) == 2:
                    break
    except (OSError, TimeoutError, WebSocketException, json.JSONDecodeError) as error:
        raise ExternalServiceError(
            ErrorDetails(
                code="iflytek_network_error",
                message=(
                    "iFLYTEK WebSocket synthesis failed. "
                    f"voice={credentials.voice}, sid={session_id}, reason={error}"
                ),
                status_code=502,
            )
        ) from error

    if not audio_parts:
        raise ExternalServiceError(
            ErrorDetails(
                code="iflytek_empty_audio",
                message=f"iFLYTEK completed without returning audio. voice={credentials.voice}, sid={session_id}",
                status_code=502,
            )
        )
    return b"".join(audio_parts)


class IflytekTTSConnector:
    """WebSocket connector for iFLYTEK online speech synthesis."""

    async def synthesize(self, text: str, credentials: IflytekCredentials) -> bytes:
        if len(text.encode("utf-8")) >= 8000:
            raise ExternalServiceError(
                ErrorDetails(
                    code="iflytek_text_too_long",
                    message=(
                        "iFLYTEK online TTS accepts fewer than 8000 UTF-8 bytes per request. "
                        f"received_bytes={len(text.encode('utf-8'))}"
                    ),
                    status_code=400,
                )
            )

        async def operation() -> bytes:
            return await asyncio.to_thread(synthesize_iflytek_sync, text, credentials)

        return await retry_async(
            operation=operation,
            service="iflytek_tts",
            attempts=3,
            delays_seconds=(1.0, 2.0),
        )

