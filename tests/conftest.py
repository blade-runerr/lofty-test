from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.post import Post


@pytest.fixture
def sample_post() -> Post:
    return Post(
        title="Test headline",
        link="https://example.com/news/1",
        published_at=datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc),
        content_hash="a" * 64,
        external_id="guid-1",
    )


@pytest.fixture
def second_post() -> Post:
    return Post(
        title="Other",
        link="https://example.com/news/2",
        published_at=datetime(2024, 6, 15, 11, 0, 0, tzinfo=timezone.utc),
        content_hash="b" * 64,
    )
