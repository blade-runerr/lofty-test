from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from email.utils import mktime_tz, parsedate_tz
from typing import TYPE_CHECKING, Any, Optional

import feedparser
import httpx

if TYPE_CHECKING:
    from app.models.post import Post

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "RSS-Telegram-Notifier/0.1 (RSS reader; +https://github.com/)"
)


def _normalize_guid(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw.strip() or None
    if isinstance(raw, dict):
        val = raw.get("value")
        if val is None:
            return None
        return str(val).strip() or None
    return str(raw).strip() or None


def _entry_published_at(entry: Any) -> datetime:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        t = entry.get(key)
        if t:
            return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
    for key in ("published", "updated", "date"):
        raw = entry.get(key)
        if isinstance(raw, str) and raw.strip():
            tt = parsedate_tz(raw.strip())
            if tt is not None:
                return datetime.fromtimestamp(mktime_tz(tt), tz=timezone.utc)
    return datetime.now(timezone.utc)


class RSSParser:
    """Загрузка и разбор RSS в список доменных Post"""

    def __init__(self, feed_url: str, timeout: float = 30.0) -> None:
        self._feed_url = feed_url
        self._timeout = timeout

    def fetch_raw_feed(self) -> str:
        """HTTP GET тела ленты"""
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": (
                "application/rss+xml, application/atom+xml, "
                "application/xml, text/xml;q=0.9, */*;q=0.8"
            ),
        }
        with httpx.Client(
            timeout=self._timeout,
            headers=headers,
            follow_redirects=True,
        ) as client:
            response = client.get(self._feed_url)
            response.raise_for_status()
        return response.text

    def parse_posts(self) -> list[Post]:
        """Вернуть элементы ленты как валидированные Pydantic-модели """
        try:
            raw = self.fetch_raw_feed()
        except httpx.HTTPError as exc:
            logger.warning("Не удалось загрузить RSS %s: %s", self._feed_url, exc)
            return []

        parsed = feedparser.parse(raw)
        if parsed.bozo and not parsed.entries:
            logger.warning(
                "Проблема разбора RSS: %s",
                getattr(parsed, "bozo_exception", "unknown"),
            )

        posts: list[Post] = []
        for entry in parsed.entries:
            post = self._entry_to_post(entry)
            if post is not None:
                posts.append(post)
        return posts

    @staticmethod
    def _entry_to_post(entry: Any) -> Optional[Post]:
        from app.models.post import Post

        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link:
            return None

        summary = (
            entry.get("summary") or entry.get("description") or ""
        ).strip()
        guid = _normalize_guid(entry.get("id")) or _normalize_guid(
            entry.get("guid")
        )
        published_at = _entry_published_at(entry)

        try:
            return Post.from_rss_fields(
                title=title,
                link=link,
                published_at=published_at,
                summary_or_body=summary,
                guid=guid,
            )
        except Exception as exc:
            logger.debug("Пропуск записи RSS: %s", exc)
            return None
