from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.post import Post
from app.utils.hashing import compute_content_hash


def test_post_content_hash_normalized_to_lowercase() -> None:
    upper = "A" * 64
    p = Post(
        title="t",
        link="https://example.com/",
        published_at=datetime.now(timezone.utc),
        content_hash=upper,
    )
    assert p.content_hash == upper.lower()


def test_post_rejects_short_content_hash() -> None:
    with pytest.raises(ValidationError):
        Post(
            title="t",
            link="https://example.com/",
            published_at=datetime.now(timezone.utc),
            content_hash="abc",
        )


def test_post_from_rss_fields_sets_external_id_and_hash() -> None:
    published = datetime(2025, 1, 1, tzinfo=timezone.utc)
    p = Post.from_rss_fields(
        title="  Title  ",
        link="https://example.com/item",
        published_at=published,
        summary_or_body="Summary",
        guid="  stable-id  ",
    )
    assert p.title == "Title"
    assert "example.com/item" in str(p.link)
    assert p.external_id == "stable-id"
    assert p.content_hash == compute_content_hash(
        title="Title",
        link="https://example.com/item",
        summary_or_body="Summary",
    )


def test_post_from_rss_fields_empty_guid_becomes_none() -> None:
    p = Post.from_rss_fields(
        title="T",
        link="https://example.com/",
        published_at=datetime.now(timezone.utc),
        summary_or_body="",
        guid="   ",
    )
    assert p.external_id is None
