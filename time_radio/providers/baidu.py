from __future__ import annotations

from urllib.parse import quote

import httpx

from time_radio.errors import ErrorDetails, ExternalServiceError
from time_radio.models import BaiduCredentials, BaiduTokenResponse
from time_radio.retry import retry_async

BAIDU_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
BAIDU_TTS_URL = "https://tsn.baidu.com/text2audio"


def gbk_byte_length(text: str) -> int:
    return len(text.encode("gbk"))


class BaiduTTSConnector:
    """REST connector for Baidu short-text speech synthesis."""

    def __init__(self, timeout_seconds: float) -> None:
        self._timeout_seconds = timeout_seconds

    async def synthesize(self, text: str, credentials: BaiduCredentials) -> bytes:
        if gbk_byte_length(text) > 1024:
            raise ExternalServiceError(
                ErrorDetails(
                    code="baidu_text_too_long",
                    message=(
                        "Baidu short-text TTS accepts at most 1024 GBK bytes per request. "
                        f"received_bytes={gbk_byte_length(text)}"
                    ),
                    status_code=400,
                )
            )

        async def operation() -> bytes:
            return await self._synthesize_once(text, credentials)

        return await retry_async(
            operation=operation,
            service="baidu_tts",
            attempts=3,
            delays_seconds=(1.0, 2.0),
        )

    async def _synthesize_once(self, text: str, credentials: BaiduCredentials) -> bytes:
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            token = await self._get_access_token(client, credentials)
            form_data = {
                "tex": quote(text, safe=""),
                "tok": token,
                "cuid": "time-radio-local",
                "ctp": "1",
                "lan": "zh",
                "aue": "3",
                "spd": str(credentials.speed),
                "pit": str(credentials.pitch),
                "vol": str(credentials.volume),
                "per": str(credentials.voice),
            }
            try:
                response = await client.post(
                    BAIDU_TTS_URL,
                    data=form_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            except httpx.RequestError as error:
                raise ExternalServiceError(
                    ErrorDetails(
                        code="baidu_tts_network_error",
                        message=(
                            "Baidu TTS request failed before receiving a response. "
                            f"voice={credentials.voice}, text_bytes={gbk_byte_length(text)}, reason={error}"
                        ),
                        status_code=502,
                    )
                ) from error

        content_type = response.headers.get("content-type", "")
        if response.status_code >= 400 or "audio/" not in content_type:
            raise ExternalServiceError(
                ErrorDetails(
                    code="baidu_tts_http_error",
                    message=(
                        "Baidu TTS did not return audio. "
                        f"voice={credentials.voice}, status={response.status_code}, "
                        f"content_type={content_type}, response={response.text[:1200]}"
                    ),
                    status_code=502,
                )
            )
        return response.content

    async def _get_access_token(
        self,
        client: httpx.AsyncClient,
        credentials: BaiduCredentials,
    ) -> str:
        params = {
            "grant_type": "client_credentials",
            "client_id": credentials.api_key.get_secret_value(),
            "client_secret": credentials.secret_key.get_secret_value(),
        }
        try:
            response = await client.post(BAIDU_TOKEN_URL, params=params)
        except httpx.RequestError as error:
            raise ExternalServiceError(
                ErrorDetails(
                    code="baidu_token_network_error",
                    message=f"Baidu access-token request failed before receiving a response. reason={error}",
                    status_code=502,
                )
            ) from error

        if response.status_code >= 400:
            raise ExternalServiceError(
                ErrorDetails(
                    code="baidu_token_http_error",
                    message=(
                        "Baidu rejected the access-token request. "
                        f"status={response.status_code}, response={response.text[:1200]}"
                    ),
                    status_code=502,
                )
            )

        try:
            return BaiduTokenResponse.model_validate(response.json()).access_token
        except ValueError as error:
            raise ExternalServiceError(
                ErrorDetails(
                    code="baidu_token_invalid_response",
                    message=f"Baidu returned an invalid access-token response. response={response.text[:1200]}",
                    status_code=502,
                )
            ) from error

