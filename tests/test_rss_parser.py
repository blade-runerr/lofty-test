from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from app.rss_parser import RSSParser

MINIMAL_RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><item>
<title>Hello</title>
<link>https://example.com/p/1</link>
<description>Body text</description>
<pubDate>Mon, 15 Jun 2024 10:30:00 GMT</pubDate>
<guid isPermaLink="false">g-1</guid>
</item></channel></rss>"""


def test_parse_posts_uses_fetched_xml() -> None:
    parser = RSSParser("https://example.com/feed.xml")
    with patch.object(parser, "fetch_raw_feed", return_value=MINIMAL_RSS):
        posts = parser.parse_posts()
    assert len(posts) == 1
    assert posts[0].title == "Hello"
    assert "example.com/p/1" in str(posts[0].link)
    assert posts[0].external_id == "g-1"


def test_parse_posts_skips_items_without_link() -> None:
    bad = MINIMAL_RSS.replace("<link>https://example.com/p/1</link>", "")
    parser = RSSParser("https://example.com/feed.xml")
    with patch.object(parser, "fetch_raw_feed", return_value=bad):
        assert parser.parse_posts() == []


def test_parse_posts_returns_empty_on_http_error() -> None:
    parser = RSSParser("https://example.com/feed.xml")
    with patch.object(
        parser,
        "fetch_raw_feed",
        side_effect=httpx.RequestError("fail"),
    ):
        assert parser.parse_posts() == []


def test_fetch_raw_feed_calls_httpx() -> None:
    parser = RSSParser("https://example.com/feed.xml")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = MINIMAL_RSS

    mock_cm = MagicMock()
    mock_cm.get.return_value = mock_response
    mock_cm.__enter__.return_value = mock_cm
    mock_cm.__exit__.return_value = None

    with patch("app.rss_parser.httpx.Client", return_value=mock_cm):
        body = parser.fetch_raw_feed()

    assert "Hello" in body
    mock_cm.get.assert_called_once_with("https://example.com/feed.xml")
