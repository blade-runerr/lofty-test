from __future__ import annotations

import signal
from unittest.mock import MagicMock, patch

from app.main import register_scheduler_shutdown, run_poll_cycle


def test_run_poll_cycle_order_and_mark_seen(sample_post) -> None:
    parser = MagicMock()
    parser.parse_posts.return_value = [sample_post]
    storage = MagicMock()
    storage.filter_new_posts.return_value = [sample_post]
    notifier = MagicMock()

    run_poll_cycle(parser, storage, notifier)

    parser.parse_posts.assert_called_once()
    storage.filter_new_posts.assert_called_once_with([sample_post])
    notifier.send_post_notification.assert_called_once_with(sample_post)
    storage.mark_seen.assert_called_once_with(sample_post)


def test_run_poll_cycle_no_mark_seen_if_send_skipped(sample_post) -> None:
    parser = MagicMock()
    parser.parse_posts.return_value = [sample_post]
    storage = MagicMock()
    storage.filter_new_posts.return_value = [sample_post]
    notifier = MagicMock()
    notifier.send_post_notification.return_value = False

    run_poll_cycle(parser, storage, notifier)

    notifier.send_post_notification.assert_called_once_with(sample_post)
    storage.mark_seen.assert_not_called()


def test_run_poll_cycle_no_mark_when_nothing_new(sample_post) -> None:
    parser = MagicMock()
    parser.parse_posts.return_value = [sample_post]
    storage = MagicMock()
    storage.filter_new_posts.return_value = []
    notifier = MagicMock()

    run_poll_cycle(parser, storage, notifier)

    notifier.send_post_notification.assert_not_called()
    storage.mark_seen.assert_not_called()


def test_register_scheduler_shutdown_wires_signals() -> None:
    scheduler = MagicMock()
    with patch("app.main.signal.signal") as mock_signal:
        register_scheduler_shutdown(scheduler)

    assert mock_signal.call_count == 2
    signums = {call.args[0] for call in mock_signal.call_args_list}
    assert signums == {signal.SIGINT, signal.SIGTERM}


def test_signal_handler_shuts_down_scheduler() -> None:
    scheduler = MagicMock()
    with patch("app.main.signal.signal") as mock_signal, patch("app.main.sys.exit") as mock_exit:
        register_scheduler_shutdown(scheduler)
        handler = mock_signal.call_args_list[0][0][1]
        handler(signal.SIGINT, None)
        scheduler.shutdown.assert_called_once_with(wait=False)
        mock_exit.assert_called_once_with(0)
