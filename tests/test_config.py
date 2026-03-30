from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings


@pytest.fixture(autouse=True)
def no_local_dotenv(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Без .env в CWD тесты зависят только от monkeypatch.setenv."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("METRICS_PORT", raising=False)


def test_settings_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("RSS_FEED_URL", "https://example.com/rss.xml")
    s = Settings()
    assert s.telegram_bot_token == "123:abc"
    assert str(s.rss_feed_url) == "https://example.com/rss.xml"


def test_settings_accepts_api_key_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "alias-token")
    monkeypatch.setenv("RSS_FEED_URL", "https://example.com/rss.xml")
    s = Settings()
    assert s.telegram_bot_token == "alias-token"


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("RSS_FEED_URL", "https://example.com/rss.xml")
    s = Settings()
    assert s.telegram_chat_id is None
    assert s.database_url is None
    assert s.metrics_port is None
    assert s.database_path == Path("data/seen_posts.db")
    assert s.poll_interval_seconds == 300
