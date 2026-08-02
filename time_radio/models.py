from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    TypeAdapter,
    field_validator,
)


class APIModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class NewsRequest(APIModel):
    year: int
    month: int = Field(ge=1, le=12)
    deepseek_api_key: SecretStr
    model: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9._:-]+$")


class DeepSeekModelsRequest(APIModel):
    deepseek_api_key: SecretStr


class DeepSeekModelItem(APIModel):
    id: str = Field(min_length=1, max_length=120)
    object: Literal["model"]
    owned_by: str = Field(min_length=1, max_length=120)


class DeepSeekModelList(APIModel):
    object: Literal["list"]
    data: list[DeepSeekModelItem]


class DeepSeekModelsResponse(APIModel):
    models: list[str]


class NewsItem(APIModel):
    title: str = Field(min_length=2, max_length=80)
    date_label: str = Field(min_length=2, max_length=32)
    region: Literal["中国", "世界"]
    summary: str = Field(min_length=20, max_length=360)


class NewsDigest(APIModel):
    year: int
    month: int
    broadcast_intro: str = Field(min_length=10, max_length=180)
    items: list[NewsItem] = Field(min_length=5, max_length=5)
    disclaimer: str = Field(min_length=10, max_length=160)


class DeepSeekMessage(APIModel):
    content: str


class DeepSeekChoice(APIModel):
    message: DeepSeekMessage


class DeepSeekCompletion(APIModel):
    choices: list[DeepSeekChoice] = Field(min_length=1)


class DeepSeekStreamDelta(APIModel):
    content: str | None = None
    reasoning_content: str | None = None


class DeepSeekStreamChoice(APIModel):
    delta: DeepSeekStreamDelta
    finish_reason: str | None = None


class DeepSeekStreamChunk(APIModel):
    choices: list[DeepSeekStreamChoice]


class NewsStreamIntro(APIModel):
    type: Literal["intro"]
    year: int
    month: int
    text: str = Field(min_length=10, max_length=180)


class NewsStreamItem(APIModel):
    type: Literal["item"]
    item: NewsItem


class NewsStreamDisclaimer(APIModel):
    type: Literal["disclaimer"]
    text: str = Field(min_length=10, max_length=160)


NewsContentEvent = Annotated[
    NewsStreamIntro | NewsStreamItem | NewsStreamDisclaimer,
    Field(discriminator="type"),
]
NEWS_CONTENT_EVENT_ADAPTER: TypeAdapter[NewsContentEvent] = TypeAdapter(NewsContentEvent)


class NewsStreamComplete(APIModel):
    type: Literal["complete"]
    item_count: int = Field(ge=5, le=5)


class NewsStreamErrorDetails(APIModel):
    code: str
    message: str


class NewsStreamError(APIModel):
    type: Literal["error"]
    error: NewsStreamErrorDetails


class IflytekCredentials(APIModel):
    app_id: SecretStr
    api_key: SecretStr
    api_secret: SecretStr
    voice: str = Field(min_length=1, max_length=64)
    speed: int = Field(ge=0, le=100)
    pitch: int = Field(ge=0, le=100)
    volume: int = Field(ge=0, le=100)


class BaiduCredentials(APIModel):
    api_key: SecretStr
    secret_key: SecretStr
    voice: int = Field(ge=0, le=99999)
    speed: int = Field(ge=0, le=15)
    pitch: int = Field(ge=0, le=15)
    volume: int = Field(ge=0, le=15)


class TTSRequest(APIModel):
    engine: Literal["iflytek", "baidu"]
    text: str = Field(min_length=1, max_length=300)
    iflytek: IflytekCredentials | None
    baidu: BaiduCredentials | None

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must contain at least one visible character.")
        return value


class HealthResponse(APIModel):
    status: Literal["ok"]
    runtime_mode: Literal["web"]
    minimum_year: int
    maximum_year: int


class VoiceCatalogItem(APIModel):
    id: str
    name: str
    category: str
    requires_authorization: bool


class VoiceCatalogResponse(APIModel):
    provider: Literal["iflytek", "baidu"]
    voices: list[VoiceCatalogItem]
    source_note: str


class BaiduTokenResponse(APIModel):
    access_token: str
