from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.models.post import Post
from app.storage import Storage
from app.utils.hashing import compute_content_hash


@pytest.fixture
def memory_storage() -> Storage:
    s = Storage(":memory:")
    yield s
    s.close()


def test_filter_new_posts_returns_all_when_empty_db(
    sample_post: Post,
    second_post: Post,
    memory_storage: Storage,
) -> None:
    posts = [sample_post, second_post]
    assert memory_storage.filter_new_posts(posts) == posts


def test_filter_new_posts_respects_is_new_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = Storage(":memory:")
    try:
        p = MagicMock(spec=Post)
        monkeypatch.setattr(storage, "is_new", lambda _post: False)
        assert storage.filter_new_posts([p]) == []
    finally:
        storage.close()


def test_mark_seen_then_duplicate_filtered(sample_post: Post, memory_storage: Storage) -> None:
    assert memory_storage.is_new(sample_post) is True
    memory_storage.mark_seen(sample_post)
    assert memory_storage.is_new(sample_post) is False
    assert memory_storage.filter_new_posts([sample_post]) == []


def test_same_external_id_new_hash_is_treated_as_new(
    sample_post: Post,
    memory_storage: Storage,
) -> None:
    memory_storage.mark_seen(sample_post)
    updated = sample_post.model_copy(
        update={
            "title": "Changed headline",
            "content_hash": compute_content_hash(
                title="Changed headline",
                link=str(sample_post.link),
                summary_or_body="",
            ),
        }
    )
    assert memory_storage.is_new(updated) is True
