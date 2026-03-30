from __future__ import annotations

import logging
import signal
import sys
from typing import Optional

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import Settings
from app.notifier import Notifier
from app.rss_parser import RSSParser
from app.storage import Storage


def register_scheduler_shutdown(scheduler: BlockingScheduler) -> None:
    """Вешает SIGINT/SIGTERM: корректно гасит APScheduler и выходит из процесса."""

    def on_signal(signum: int, _frame: Optional[object]) -> None:
        print(f"\n[main] Сигнал {signum}, останавливаем планировщик...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)


def run_poll_cycle(
    parser: RSSParser,
    storage: Storage,
    notifier: Notifier,
) -> None:
    """Один проход: парсинг → дедуп → по одному: отправка и сразу mark_seen."""
    posts = parser.parse_posts()
    new_posts = storage.filter_new_posts(posts)
    for post in new_posts:
        if notifier.send_post_notification(post):
            storage.mark_seen(post)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )
    settings = Settings()
    parser = RSSParser(str(settings.rss_feed_url))
    storage = Storage(
        database_path=str(settings.database_path),
        database_url=settings.database_url,
    )
    notifier = Notifier(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )

    print(
        "[main] Старт. Интервал опроса:",
        f"{settings.poll_interval_seconds}s, RSS:",
        str(settings.rss_feed_url),
    )

    run_poll_cycle(parser, storage, notifier)

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_poll_cycle,
        "interval",
        seconds=settings.poll_interval_seconds,
        args=[parser, storage, notifier],
        id="rss_poll",
        replace_existing=True,
    )

    register_scheduler_shutdown(scheduler)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        storage.close()


if __name__ == "__main__":
    main()
