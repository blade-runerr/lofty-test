from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Post(BaseModel):
    """Доменная модель элемента RSS, готового к уведомлению и хранению."""

    title: str = Field(..., min_length=1, description="Заголовок поста")
    link: HttpUrl = Field(..., description="Каноническая ссылка на материал")
    published_at: datetime = Field(..., description="Дата публикации (UTC предпочтительно)")
    content_hash: str = Field(
        ...,
        min_length=32,
        max_length=128,
        description="SHA-256 (hex) нормализованного содержимого для дедупликации",
    )
    external_id: Optional[str] = Field(
        default=None,
        description="guid из RSS, если есть — стабильный идентификатор источника",
    )

    @field_validator("content_hash")
    @classmethod
    def hex_lower(cls, v: str) -> str:
        return v.lower()

    model_config = {
        "frozen": True,
        "str_strip_whitespace": True,
    }

    @classmethod
    def from_rss_fields(
        cls,
        *,
        title: str,
        link: str,
        published_at: datetime,
        summary_or_body: str,
        guid: Optional[str],
    ) -> "Post":
        """Фабрика для сборки из сырого RSS (хэш считается в RSSParser)."""
        from app.utils.hashing import compute_content_hash

        external_id = guid.strip() if guid and guid.strip() else None
        content_hash = compute_content_hash(
            title=title,
            link=link,
            summary_or_body=summary_or_body,
        )
        return cls(
            title=title.strip(),
            link=link,  # type: ignore[arg-type]
            published_at=published_at,
            content_hash=content_hash,
            external_id=external_id,
        )
