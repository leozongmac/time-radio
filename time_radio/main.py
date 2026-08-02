from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from time_radio.errors import ErrorDetails, TimeRadioError
from time_radio.models import (
    HealthResponse,
    DeepSeekModelsRequest,
    DeepSeekModelsResponse,
    NewsDigest,
    NewsRequest,
    NewsStreamComplete,
    NewsStreamError,
    NewsStreamErrorDetails,
    TTSRequest,
    VoiceCatalogResponse,
)
from time_radio.providers.baidu import BaiduTTSConnector
from time_radio.providers.deepseek import DeepSeekConnector
from time_radio.providers.iflytek import IflytekTTSConnector
from time_radio.providers.voice_catalogs import get_voice_catalog
from time_radio.services import synthesize_speech
from time_radio.settings import AppSettings, load_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).resolve().parents[1]
SETTINGS = load_settings(PROJECT_DIR)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.settings = SETTINGS
    app.state.deepseek_connector = DeepSeekConnector(timeout_seconds=180.0)
    app.state.iflytek_connector = IflytekTTSConnector()
    app.state.baidu_connector = BaiduTTSConnector(timeout_seconds=45.0)
    yield


app = FastAPI(
    title="AI时光收音机",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(TimeRadioError)
async def handle_time_radio_error(request: Request, error: TimeRadioError) -> JSONResponse:
    logger.error(
        "Time Radio request failed",
        extra={
            "path": request.url.path,
            "error_code": error.details.code,
            "status_code": error.details.status_code,
        },
    )
    return JSONResponse(
        status_code=error.details.status_code,
        content={
            "error": {
                "code": error.details.code,
                "message": error.details.message,
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(request: Request, error: StarletteHTTPException) -> Response:
    return await http_exception_handler(request, error)


@app.get("/api/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings: AppSettings = request.app.state.settings
    return HealthResponse(
        status="ok",
        runtime_mode="web",
        minimum_year=settings.minimum_year,
        maximum_year=datetime.now(UTC).year,
    )


@app.post("/api/news", response_model=NewsDigest)
async def create_news(request_body: NewsRequest, request: Request) -> NewsDigest:
    settings: AppSettings = request.app.state.settings
    maximum_year = datetime.now(UTC).year
    if request_body.year < settings.minimum_year or request_body.year > maximum_year:
        raise TimeRadioError(
            ErrorDetails(
                code="news_year_out_of_range",
                message=(
                    "The selected year is outside the supported range. "
                    f"selected={request_body.year}, minimum={settings.minimum_year}, maximum={maximum_year}"
                ),
                status_code=400,
            )
        )
    connector: DeepSeekConnector = request.app.state.deepseek_connector
    return await connector.create_news_digest(request_body)


@app.post("/api/deepseek/models", response_model=DeepSeekModelsResponse)
async def list_deepseek_models(
    request_body: DeepSeekModelsRequest,
    request: Request,
) -> DeepSeekModelsResponse:
    connector: DeepSeekConnector = request.app.state.deepseek_connector
    models = await connector.list_models(request_body)
    return DeepSeekModelsResponse(models=models)


@app.post("/api/news/stream")
async def stream_news(request_body: NewsRequest, request: Request) -> StreamingResponse:
    settings: AppSettings = request.app.state.settings
    maximum_year = datetime.now(UTC).year
    if request_body.year < settings.minimum_year or request_body.year > maximum_year:
        raise TimeRadioError(
            ErrorDetails(
                code="news_year_out_of_range",
                message=(
                    "The selected year is outside the supported range. "
                    f"selected={request_body.year}, minimum={settings.minimum_year}, maximum={maximum_year}"
                ),
                status_code=400,
            )
        )
    connector: DeepSeekConnector = request.app.state.deepseek_connector

    async def generate_events() -> AsyncIterator[bytes]:
        try:
            item_count = 0
            async for event in connector.stream_news_events(request_body):
                if event.type == "item":
                    item_count += 1
                yield f"{event.model_dump_json()}\n".encode()
            complete = NewsStreamComplete(type="complete", item_count=item_count)
            yield f"{complete.model_dump_json()}\n".encode()
        except TimeRadioError as error:
            stream_error = NewsStreamError(
                type="error",
                error=NewsStreamErrorDetails(
                    code=error.details.code,
                    message=error.details.message,
                ),
            )
            yield f"{stream_error.model_dump_json()}\n".encode()

    return StreamingResponse(
        generate_events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache, no-transform"},
    )


@app.get("/api/tts/voices", response_model=VoiceCatalogResponse)
async def list_tts_voices(
    provider: Literal["iflytek", "baidu"],
) -> VoiceCatalogResponse:
    return get_voice_catalog(provider)


@app.post("/api/tts")
async def create_speech(request_body: TTSRequest, request: Request) -> Response:
    audio_result = await synthesize_speech(
        request=request_body,
        iflytek_connector=request.app.state.iflytek_connector,
        baidu_connector=request.app.state.baidu_connector,
    )
    return Response(
        content=audio_result.content,
        media_type=audio_result.media_type,
        headers={"Content-Disposition": f'inline; filename="{audio_result.filename}"'},
    )


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(SETTINGS.static_dir / "index.html")


if not SETTINGS.static_dir.is_dir():
    raise RuntimeError(f"Static directory is missing: {SETTINGS.static_dir}")

app.mount(
    "/static",
    StaticFiles(directory=SETTINGS.static_dir),
    name="static",
)
