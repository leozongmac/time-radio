from __future__ import annotations

from dataclasses import dataclass

from time_radio.errors import ConfigurationError, ErrorDetails
from time_radio.models import TTSRequest
from time_radio.providers.baidu import BaiduTTSConnector
from time_radio.providers.iflytek import IflytekTTSConnector


@dataclass(frozen=True)
class AudioResult:
    content: bytes
    media_type: str
    filename: str


async def synthesize_speech(
    request: TTSRequest,
    iflytek_connector: IflytekTTSConnector,
    baidu_connector: BaiduTTSConnector,
) -> AudioResult:
    if request.engine == "iflytek":
        if request.iflytek is None:
            raise ConfigurationError(
                ErrorDetails(
                    code="iflytek_credentials_required",
                    message="iFLYTEK TTS requires AppID, APIKey, and APISecret.",
                    status_code=400,
                )
            )
        content = await iflytek_connector.synthesize(request.text, request.iflytek)
        return AudioResult(content=content, media_type="audio/mpeg", filename="time-radio-iflytek.mp3")

    if request.baidu is None:
        raise ConfigurationError(
            ErrorDetails(
                code="baidu_credentials_required",
                message="Baidu TTS requires API Key and Secret Key.",
                status_code=400,
            )
        )
    content = await baidu_connector.synthesize(request.text, request.baidu)
    return AudioResult(content=content, media_type="audio/mpeg", filename="time-radio-baidu.mp3")
