from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.notifier import Notifier


def test_notify_batch_calls_send_for_each_post(sample_post, second_post) -> None:
    n = Notifier(bot_token="dummy", chat_id="1")
    with patch.object(n, "send_post_notification") as send:
        n.notify_batch([sample_post, second_post])
    assert send.call_count == 2
    send.assert_any_call(sample_post)
    send.assert_any_call(second_post)


def test_notifier_stores_token_and_chat_id() -> None:
    n = Notifier(bot_token="tok", chat_id="99")
    assert n._bot_token == "tok"
    assert n._chat_id == "99"


def test_notifier_accepts_none_chat_id() -> None:
    n = Notifier(bot_token="tok", chat_id=None)
    assert n._chat_id is None


def test_send_post_notification_calls_telegram_api(sample_post) -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    mock_cm = MagicMock()
    mock_cm.post.return_value = mock_resp
    mock_cm.__enter__.return_value = mock_cm
    mock_cm.__exit__.return_value = None

    with patch("app.notifier.httpx.Client", return_value=mock_cm):
        n = Notifier("MYTOKEN", "888")
        assert n.send_post_notification(sample_post) is True

    url = mock_cm.post.call_args[0][0]
    assert "MYTOKEN" in url and "sendMessage" in url
    payload = mock_cm.post.call_args[1]["json"]
    assert payload["chat_id"] == "888"
    assert payload["parse_mode"] == "HTML"
    assert sample_post.title in payload["text"]


def test_notify_batch_does_not_call_http_without_chat_id(sample_post) -> None:
    n = Notifier("token", chat_id=None)
    with patch("app.notifier.httpx.Client") as client_cls:
        n.notify_batch([sample_post])
    client_cls.assert_not_called()


def test_send_post_notification_returns_false_without_chat_id(sample_post) -> None:
    n = Notifier("token", chat_id=None)
    with patch("app.notifier.httpx.Client") as client_cls:
        assert n.send_post_notification(sample_post) is False
    client_cls.assert_not_called()
