from __future__ import annotations

import hashlib

from app.utils.hashing import compute_content_hash


def test_compute_content_hash_is_deterministic() -> None:
    h1 = compute_content_hash(
        title="Hello",
        link="https://x.com/a",
        summary_or_body="Body",
    )
    h2 = compute_content_hash(
        title="Hello",
        link="https://x.com/a",
        summary_or_body="Body",
    )
    assert h1 == h2
    assert len(h1) == 64


def test_compute_content_hash_matches_expected_payload() -> None:
    title, link, body = "A", "https://e/u", "Z"
    expected = hashlib.sha256(
        "\n".join(
            [
                title.casefold(),
                link.strip(),
                body.casefold(),
            ]
        ).encode("utf-8")
    ).hexdigest()
    assert compute_content_hash(title=title, link=link, summary_or_body=body) == expected


def test_different_title_changes_hash() -> None:
    base = dict(link="https://e/u", summary_or_body="same")
    h1 = compute_content_hash(title="One", **base)
    h2 = compute_content_hash(title="Two", **base)
    assert h1 != h2


def test_casefold_normalizes_title_and_summary() -> None:
    assert compute_content_hash(
        title="NEWS",
        link="https://e/u",
        summary_or_body="TEXT",
    ) == compute_content_hash(
        title="news",
        link="https://e/u",
        summary_or_body="text",
    )
