from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = Field(
        ...,
        validation_alias=AliasChoices("TELEGRAM_BOT_TOKEN", "API_KEY"),
        description="Токен Telegram Bot API",
    )
    telegram_chat_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("TELEGRAM_CHAT_ID", "CHAT_ID"),
        description="Куда слать- user id, группа или @channelusername",
    )
    rss_feed_url: HttpUrl = Field(
        ...,
        validation_alias="RSS_FEED_URL",
        description="URL RSS-ленты",
    )
    database_url: Optional[str] = Field(
        default=None,
        validation_alias="DATABASE_URL",
        description="Если задан — PostgreSQL Иначе SQLite по DATABASE_PATH",
    )
    database_path: Path = Field(
        default=Path("data/seen_posts.db"),
        validation_alias="DATABASE_PATH",
    )
    poll_interval_seconds: int = Field(
        default=300,
        ge=30,
        validation_alias="POLL_INTERVAL_SECONDS",
    )
    metrics_port: Optional[int] = Field(
        default=None,
        validation_alias="METRICS_PORT",
        ge=1,
        le=65535,
        description="Если задан — слушать /metrics для Prometheus на этом порту",
    )

    @field_validator("metrics_port", mode="before")
    @classmethod
    def metrics_port_empty_to_none(cls, v: object) -> Optional[int]:
        if v is None or v == "":
            return None
        return int(v)

    @field_validator("database_url", mode="before")
    @classmethod
    def empty_database_url_to_none(cls, v: Optional[str]) -> Optional[str]:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return str(v).strip()
