from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import httpx
from pydantic import ValidationError

from time_radio.errors import ErrorDetails, ExternalServiceError
from time_radio.models import (
    NEWS_CONTENT_EVENT_ADAPTER,
    DeepSeekCompletion,
    DeepSeekModelList,
    DeepSeekModelsRequest,
    DeepSeekStreamChunk,
    NewsContentEvent,
    NewsDigest,
    NewsRequest,
    NewsStreamDisclaimer,
    NewsStreamIntro,
    NewsStreamItem,
    NewsItem,
)
from time_radio.retry import retry_async

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODELS_URL = "https://api.deepseek.com/models"
logger = logging.getLogger(__name__)


def build_news_prompt(year: int, month: int) -> tuple[str, str]:
    system_prompt = (
        "你是一名严谨的中文历史新闻编辑。请仅依据你已有的知识整理内容，不声称已经联网检索，"
        "不编造来源链接。输出必须是 JSON，所有字段都必须存在。若具体日期不确定，date_label 使用"
        "“当月”，不要猜测日期。摘要适合新闻播音，每条八十到一百四十个汉字。"
    )
    user_prompt = (
        f"请整理 {year} 年 {month:02d} 月最重要的五条历史新闻，兼顾中国与世界。"
        "JSON 格式必须严格如下："
        '{"year":1986,"month":8,"broadcast_intro":"开场白",'
        '"items":[{"title":"标题","date_label":"日期或当月","region":"中国或世界","summary":"摘要"}],'
        '"disclaimer":"本期内容由 DeepSeek 基于模型知识整理，可能存在遗漏或偏差，请以权威史料为准。"}'
        "items 必须恰好五条，region 只能是“中国”或“世界”。"
    )
    return system_prompt, user_prompt


def build_stream_news_prompt(year: int, month: int) -> tuple[str, str]:
    system_prompt = (
        "你是一名严谨的中文历史新闻编辑。请仅依据你已有的知识整理内容，不声称已经联网检索，"
        "不编造来源链接。你必须输出 NDJSON：每行是一个完整 JSON 对象，禁止 Markdown 代码块，"
        "禁止在 JSON 行之外输出任何文字。具体日期不确定时使用“当月”，不要猜测日期。"
    )
    user_prompt = (
        f"请按生成顺序流式整理 {year} 年 {month:02d} 月最重要的五条历史新闻，兼顾中国与世界。"
        "第一行必须是开场白："
        f'{{"type":"intro","year":{year},"month":{month},"text":"十到一百八十字开场白"}}。'
        "随后恰好五行新闻，每生成一条就立即输出一行："
        '{"type":"item","item":{"title":"标题","date_label":"日期或当月",'
        '"region":"中国或世界","summary":"八十到一百四十个汉字的播音摘要"}}。'
        "最后一行必须是："
        '{"type":"disclaimer","text":"本期内容由 DeepSeek 基于模型知识整理，'
        '可能存在遗漏或偏差，请以权威史料为准。"}'
    )
    return system_prompt, user_prompt


def parse_stream_content_line(line: str) -> NewsContentEvent | None:
    normalized = line.strip()
    if not normalized or normalized in {"```", "```json"}:
        return None
    try:
        parsed = json.loads(normalized)
        if not isinstance(parsed, dict):
            raise ValueError("The event must be a JSON object.")
        if parsed.get("type") == "item" and "item" not in parsed:
            item = NewsItem.model_validate(parsed)
            return NewsStreamItem(type="item", item=item)
        return NEWS_CONTENT_EVENT_ADAPTER.validate_python(parsed)
    except (json.JSONDecodeError, ValidationError, ValueError) as error:
        raise ExternalServiceError(
            ErrorDetails(
                code="deepseek_invalid_stream_event",
                message=(
                    "DeepSeek returned an invalid streaming news event. "
                    f"event={normalized[:1200]}, reason={error}"
                ),
                status_code=502,
            )
        ) from error


def extract_complete_json_objects(buffer: str) -> tuple[list[str], str]:
    objects: list[str] = []
    object_start: int | None = None
    depth = 0
    in_string = False
    escaped = False

    for index, character in enumerate(buffer):
        if object_start is None:
            if character == "{":
                object_start = index
                depth = 1
            continue
        if escaped:
            escaped = False
            continue
        if character == "\\" and in_string:
            escaped = True
            continue
        if character == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if character == "{":
            depth += 1
            continue
        if character != "}":
            continue
        depth -= 1
        if depth == 0:
            objects.append(buffer[object_start : index + 1])
            object_start = None

    remainder = buffer[object_start:] if object_start is not None else ""
    return objects, remainder


class DeepSeekConnector:
    """OpenAI-compatible connector for DeepSeek historical news generation."""

    def __init__(self, timeout_seconds: float) -> None:
        self._timeout_seconds = timeout_seconds

    async def list_models(self, request: DeepSeekModelsRequest) -> list[str]:
        async def operation() -> list[str]:
            return await self._list_models_once(request)

        return await retry_async(
            operation=operation,
            service="deepseek_models",
            attempts=3,
            delays_seconds=(1.0, 2.0),
        )

    async def _list_models_once(self, request: DeepSeekModelsRequest) -> list[str]:
        headers = {
            "Authorization": f"Bearer {request.deepseek_api_key.get_secret_value()}",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(DEEPSEEK_MODELS_URL, headers=headers)
        except httpx.RequestError as error:
            raise ExternalServiceError(
                ErrorDetails(
                    code="deepseek_models_network_error",
                    message=f"DeepSeek model refresh failed before receiving a response. reason={error}",
                    status_code=502,
                )
            ) from error
        if response.status_code >= 400:
            raise ExternalServiceError(
                ErrorDetails(
                    code="deepseek_models_http_error",
                    message=(
                        "DeepSeek rejected the model refresh request. "
                        f"status={response.status_code}, response={response.text[:1200]}"
                    ),
                    status_code=502,
                )
            )
        try:
            model_list = DeepSeekModelList.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise ExternalServiceError(
                ErrorDetails(
                    code="deepseek_models_invalid_response",
                    message=f"DeepSeek returned an invalid model list. response={response.text[:1200]}",
                    status_code=502,
                )
            ) from error
        models = sorted({model.id for model in model_list.data})
        if not models:
            raise ExternalServiceError(
                ErrorDetails(
                    code="deepseek_models_empty",
                    message="DeepSeek returned an empty model list for this API key.",
                    status_code=502,
                )
            )
        return models

    async def create_news_digest(self, request: NewsRequest) -> NewsDigest:
        async def operation() -> NewsDigest:
            return await self._create_news_digest_once(request)

        return await retry_async(
            operation=operation,
            service="deepseek",
            attempts=3,
            delays_seconds=(1.0, 2.0),
        )

    async def _create_news_digest_once(self, request: NewsRequest) -> NewsDigest:
        system_prompt, user_prompt = build_news_prompt(request.year, request.month)
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "stream": False,
            "thinking": {"type": "disabled"},
            "temperature": 0.2,
            "max_tokens": 2200,
        }
        headers = {
            "Authorization": f"Bearer {request.deepseek_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(DEEPSEEK_URL, headers=headers, json=payload)
        except httpx.RequestError as error:
            raise ExternalServiceError(
                ErrorDetails(
                    code="deepseek_network_error",
                    message=(
                        "DeepSeek request failed before receiving a response. "
                        f"model={request.model}, year={request.year}, month={request.month}, "
                        f"reason={error}"
                    ),
                    status_code=502,
                )
            ) from error

        if response.status_code >= 400:
            raise ExternalServiceError(
                ErrorDetails(
                    code="deepseek_http_error",
                    message=(
                        "DeepSeek rejected the news request. "
                        f"model={request.model}, year={request.year}, month={request.month}, "
                        f"status={response.status_code}, response={response.text[:1200]}"
                    ),
                    status_code=502,
                )
            )

        try:
            completion = DeepSeekCompletion.model_validate(response.json())
            content = completion.choices[0].message.content
            if not content.strip():
                raise ExternalServiceError(
                    ErrorDetails(
                        code="deepseek_empty_response",
                        message=(
                            "DeepSeek returned an empty response. "
                            f"model={request.model}, year={request.year}, month={request.month}"
                        ),
                        status_code=502,
                    )
                )
            parsed_content = json.loads(content)
            digest = NewsDigest.model_validate(parsed_content)
        except (json.JSONDecodeError, ValidationError) as error:
            raise ExternalServiceError(
                ErrorDetails(
                    code="deepseek_invalid_response",
                    message=(
                        "DeepSeek returned data that did not match the required news schema. "
                        f"model={request.model}, year={request.year}, month={request.month}, "
                        f"response={response.text[:1200]}, reason={error}"
                    ),
                    status_code=502,
                )
            ) from error

        if digest.year != request.year or digest.month != request.month:
            raise ExternalServiceError(
                ErrorDetails(
                    code="deepseek_date_mismatch",
                    message=(
                        "DeepSeek returned news for a different date. "
                        f"requested={request.year}-{request.month:02d}, "
                        f"returned={digest.year}-{digest.month:02d}"
                    ),
                    status_code=502,
                )
            )
        return digest

    async def stream_news_events(self, request: NewsRequest) -> AsyncIterator[NewsContentEvent]:
        delays_seconds = (1.0, 2.0)
        for attempt in range(1, 4):
            emitted_event = False
            try:
                async for event in self._stream_news_events_once(request):
                    emitted_event = True
                    yield event
                return
            except ExternalServiceError as error:
                if emitted_event or attempt == 3:
                    raise
                logger.warning(
                    "External service request will be retried",
                    extra={
                        "service": "deepseek_stream",
                        "attempt": attempt,
                        "maximum_attempts": 3,
                        "error_code": error.details.code,
                    },
                )
                await asyncio.sleep(delays_seconds[attempt - 1])

    async def _stream_news_events_once(
        self,
        request: NewsRequest,
    ) -> AsyncIterator[NewsContentEvent]:
        system_prompt, user_prompt = build_stream_news_prompt(request.year, request.month)
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": True,
            "thinking": {"type": "disabled"},
            "temperature": 0.2,
            "max_tokens": 3600,
        }
        headers = {
            "Authorization": f"Bearer {request.deepseek_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

        try:
            async with (
                httpx.AsyncClient(timeout=self._timeout_seconds) as client,
                client.stream(
                    "POST",
                    DEEPSEEK_URL,
                    headers=headers,
                    json=payload,
                ) as response,
            ):
                if response.status_code >= 400:
                    response_body = (await response.aread()).decode("utf-8", errors="replace")
                    raise ExternalServiceError(
                        ErrorDetails(
                            code="deepseek_http_error",
                            message=(
                                "DeepSeek rejected the streaming news request. "
                                f"model={request.model}, year={request.year}, "
                                f"month={request.month}, status={response.status_code}, "
                                f"response={response_body[:1200]}"
                            ),
                            status_code=502,
                        )
                    )
                async for event in self._parse_stream_response(response, request):
                    yield event
        except httpx.RequestError as error:
            raise ExternalServiceError(
                ErrorDetails(
                    code="deepseek_network_error",
                    message=(
                        "DeepSeek streaming request failed. "
                        f"model={request.model}, year={request.year}, month={request.month}, "
                        f"reason={error}"
                    ),
                    status_code=502,
                )
            ) from error

    async def _parse_stream_response(
        self,
        response: httpx.Response,
        request: NewsRequest,
    ) -> AsyncIterator[NewsContentEvent]:
        content_buffer = ""
        content_character_count = 0
        reasoning_character_count = 0
        finish_reason: str | None = None
        intro_received = False
        disclaimer_received = False
        item_count = 0

        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            payload_text = line[5:].strip()
            if payload_text == "[DONE]":
                break
            try:
                chunk = DeepSeekStreamChunk.model_validate_json(payload_text)
            except ValidationError as error:
                raise ExternalServiceError(
                    ErrorDetails(
                        code="deepseek_invalid_stream_chunk",
                        message=(
                            "DeepSeek returned an invalid SSE chunk. "
                            f"chunk={payload_text[:1200]}, reason={error}"
                        ),
                        status_code=502,
                    )
                ) from error
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            finish_reason = choice.finish_reason or finish_reason
            reasoning_content = choice.delta.reasoning_content
            if reasoning_content is not None:
                reasoning_character_count += len(reasoning_content)
            content = choice.delta.content
            if content is None:
                continue
            content_character_count += len(content)
            content_buffer += content
            raw_events, content_buffer = extract_complete_json_objects(content_buffer)
            for raw_event in raw_events:
                event = parse_stream_content_line(raw_event)
                if event is None:
                    continue
                intro_received, disclaimer_received, item_count = self._validate_event_order(
                    event=event,
                    request=request,
                    intro_received=intro_received,
                    disclaimer_received=disclaimer_received,
                    item_count=item_count,
                )
                yield event

        if not intro_received or not disclaimer_received or item_count != 5:
            raise ExternalServiceError(
                ErrorDetails(
                    code="deepseek_incomplete_stream",
                    message=(
                        "DeepSeek streaming response ended before the required news set was complete. "
                        f"intro_received={intro_received}, item_count={item_count}, "
                        f"disclaimer_received={disclaimer_received}, "
                        f"content_characters={content_character_count}, "
                        f"reasoning_characters={reasoning_character_count}, "
                        f"finish_reason={finish_reason}, buffered_content={content_buffer[:600]}"
                    ),
                    status_code=502,
                )
            )

    @staticmethod
    def _validate_event_order(
        event: NewsContentEvent,
        request: NewsRequest,
        intro_received: bool,
        disclaimer_received: bool,
        item_count: int,
    ) -> tuple[bool, bool, int]:
        if isinstance(event, NewsStreamIntro):
            if intro_received or item_count > 0 or disclaimer_received:
                raise DeepSeekConnector._invalid_event_order("intro", item_count)
            if event.year != request.year or event.month != request.month:
                raise ExternalServiceError(
                    ErrorDetails(
                        code="deepseek_date_mismatch",
                        message=(
                            "DeepSeek streamed news for a different date. "
                            f"requested={request.year}-{request.month:02d}, "
                            f"returned={event.year}-{event.month:02d}"
                        ),
                        status_code=502,
                    )
                )
            return True, False, 0
        if isinstance(event, NewsStreamItem):
            if not intro_received or disclaimer_received or item_count >= 5:
                raise DeepSeekConnector._invalid_event_order("item", item_count)
            return True, False, item_count + 1
        if isinstance(event, NewsStreamDisclaimer):
            if not intro_received or disclaimer_received or item_count != 5:
                raise DeepSeekConnector._invalid_event_order("disclaimer", item_count)
            return True, True, item_count
        raise TypeError(f"Unsupported news stream event type: {type(event).__name__}")

    @staticmethod
    def _invalid_event_order(event_type: str, item_count: int) -> ExternalServiceError:
        return ExternalServiceError(
            ErrorDetails(
                code="deepseek_invalid_stream_order",
                message=(
                    "DeepSeek returned streaming events in an invalid order. "
                    f"event_type={event_type}, item_count={item_count}"
                ),
                status_code=502,
            )
        )
