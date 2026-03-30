"""Метрики в формате Prometheus (текстовый exposition на /metrics)."""

from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

from prometheus_client import Counter, Histogram, start_http_server

logger = logging.getLogger(__name__)

poll_runs_total = Counter(
    "rss_poll_runs_total",
    "Запусков цикла опроса RSS (включая неуспешные)",
)
rss_items_parsed_total = Counter(
    "rss_items_parsed_total",
    "Записей, вернувшихся из парсера RSS за все опросы",
)
rss_items_new_total = Counter(
    "rss_items_new_total",
    "Записей, прошедших дедупликацию (кандидаты на отправку)",
)
telegram_sent_total = Counter(
    "rss_telegram_sent_total",
    "Успешно отправленных сообщений в Telegram",
)
telegram_skipped_total = Counter(
    "rss_telegram_skipped_total",
    "Пропусков отправки (нет chat_id или send вернул False)",
)
telegram_errors_total = Counter(
    "rss_telegram_errors_total",
    "Ошибок при вызове Telegram API",
)
poll_duration_seconds = Histogram(
    "rss_poll_duration_seconds",
    "Длительность одного цикла опроса, сек",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)


def start_metrics_server(port: int) -> None:
    """HTTP-сервер на `port` с путём GET /metrics (в отдельном потоке)."""
    start_http_server(port)
    logger.info("Метрики Prometheus: http://0.0.0.0:%s/metrics", port)


T = TypeVar("T")


def observe_poll_cycle(run: Callable[[], T]) -> T:
    """Обёртка: счётчик опросов + гистограмма длительности."""
    poll_runs_total.inc()
    t0 = time.perf_counter()
    try:
        return run()
    finally:
        poll_duration_seconds.observe(time.perf_counter() - t0)
