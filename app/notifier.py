from __future__ import annotations

import html
import logging
from typing import TYPE_CHECKING, Optional

import httpx

if TYPE_CHECKING:
    from app.models.post import Post

logger = logging.getLogger(__name__)


class Notifier:
    """Отправка уведомлений в телегу"""

    def __init__(
        self,
        bot_token: str,
        chat_id: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._timeout = timeout
        self._api_base = f"https://api.telegram.org/bot{bot_token}"

    def _format_message(self, post: Post) -> str:
        title = html.escape(post.title)
        link = html.escape(str(post.link))
        when = post.published_at.strftime("%Y-%m-%d %H:%M UTC")
        return (
            f"<b>{title}</b>\n"
            f"<code>{when}</code>\n"
            f'<a href="{link}">Открыть</a>'
        )

    def send_post_notification(self, post: Post) -> bool:
        """Отправить одно сообщение. Возвращает True, если ушло в Telegram"""
        if not self._chat_id:
            logger.warning("TELEGRAM_CHAT_ID не задан — сообщение не отправлено")
            return False

        url = f"{self._api_base}/sendMessage"
        payload = {
            "chat_id": self._chat_id,
            "text": self._format_message(post),
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(url, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError:
                logger.error(
                    "Telegram API %s: %s",
                    response.status_code,
                    response.text,
                )
                raise
        return True

    def notify_batch(self, posts: list[Post]) -> None:
        
        if not posts:
            return
        if not self._chat_id:
            logger.warning(
                "TELEGRAM_CHAT_ID не задан — пропущено уведомлений: %s",
                len(posts),
            )
            return
        for p in posts:
            self.send_post_notification(p)
