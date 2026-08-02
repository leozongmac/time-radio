from __future__ import annotations

from fastapi.testclient import TestClient

from time_radio.main import app
from time_radio.models import NewsStreamItem
from time_radio.providers.deepseek import (
    extract_complete_json_objects,
    parse_stream_content_line,
)


def test_health_and_main_page_are_available() -> None:
    with TestClient(app) as client:
        health_response = client.get("/api/health")
        page_response = client.get("/")

    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"
    assert health_response.json()["runtime_mode"] == "web"
    assert page_response.status_code == 200
    assert page_response.headers["content-type"].startswith("text/html")
    assert "AI时光收音机" in page_response.text
    assert "造物主" in page_response.text
    assert "三川" in page_response.text


def test_tts_rejects_missing_iflytek_credentials() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/tts",
            json={
                "engine": "iflytek",
                "text": "测试播音",
                "iflytek": None,
                "baidu": None,
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "iflytek_credentials_required"


def test_cloud_voice_catalogs_are_available() -> None:
    with TestClient(app) as client:
        iflytek_response = client.get("/api/tts/voices", params={"provider": "iflytek"})
        baidu_response = client.get("/api/tts/voices", params={"provider": "baidu"})

    assert iflytek_response.status_code == 200
    assert any(voice["id"] == "xiaoyan" for voice in iflytek_response.json()["voices"])
    assert baidu_response.status_code == 200
    assert any(voice["id"] == "0" for voice in baidu_response.json()["voices"])


def test_main_page_exposes_cloud_credential_controls() -> None:
    with TestClient(app) as client:
        page_response = client.get("/")

    assert 'data-testid="save-tts-settings"' in page_response.text
    assert 'data-testid="clear-tts-settings"' in page_response.text
    assert 'data-testid="refresh-iflytek-voices"' in page_response.text
    assert 'data-testid="save-deepseek-key"' in page_response.text
    assert 'data-testid="clear-deepseek-key"' in page_response.text
    assert 'data-testid="refresh-deepseek-models"' in page_response.text
    assert 'data-testid="select-deepseek-model"' in page_response.text
    assert 'data-testid="date-display"' in page_response.text
    assert "Qwen3-TTS" not in page_response.text


def test_white_noise_asset_and_volume_control_are_available() -> None:
    with TestClient(app) as client:
        page_response = client.get("/")
        audio_response = client.get("/static/assets/BZS.mp3")

    assert 'data-testid="white-noise-volume"' in page_response.text
    assert 'id="white-noise-audio"' in page_response.text
    assert audio_response.status_code == 200
    assert audio_response.headers["content-type"] == "audio/mpeg"
    assert len(audio_response.content) == 1_003_776


def test_deepseek_ndjson_news_item_is_validated() -> None:
    event = parse_stream_content_line(
        '{"type":"item","item":{"title":"测试新闻标题","date_label":"当月",'
        '"region":"中国","summary":"这是一段用于验证流式新闻事件解析与字段约束的完整中文新闻摘要。"}}'
    )

    assert isinstance(event, NewsStreamItem)
    assert event.item.title == "测试新闻标题"


def test_deepseek_flat_ndjson_news_item_is_normalized() -> None:
    event = parse_stream_content_line(
        '{"type":"item","title":"切尔诺贝利核事故后续影响持续发酵",'
        '"date_label":"5月1日-31日","region":"世界",'
        '"summary":"苏联切尔诺贝利核电站四月底爆炸后，五月辐射尘扩散至欧洲多国，'
        '引发全球反核浪潮，事故长期生态与健康后果成为国际焦点。"}'
    )

    assert isinstance(event, NewsStreamItem)
    assert event.item.title == "切尔诺贝利核事故后续影响持续发酵"
    assert event.item.region == "世界"


def test_stream_json_objects_do_not_require_newlines() -> None:
    first = '{"type":"intro","year":1986,"month":8,"text":"这里是八月的历史新闻开场。"}'
    second = (
        '{"type":"item","item":{"title":"包含括号的新闻","date_label":"当月",'
        '"region":"世界","summary":"摘要中即使出现 {示例} 字符，也不应破坏 JSON 对象边界识别。"}}'
    )

    objects, remainder = extract_complete_json_objects(f"```json{first}{second}```")

    assert objects == [first, second]
    assert remainder == ""
