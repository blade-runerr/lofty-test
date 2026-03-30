from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.models.post import Post


def _dedup_key(post: Post) -> str:
    if post.external_id:
        return post.external_id
    return str(post.link)


_CREATE_SEEN_SQL = """
CREATE TABLE IF NOT EXISTS seen_items (
    dedup_key TEXT PRIMARY KEY NOT NULL,
    content_hash TEXT NOT NULL
);
"""


class Storage:
    """Дедупликация: SQLite (файл / :memory:) или PostgreSQL по DATABASE_URL."""

    def __init__(
        self,
        database_path: Optional[str] = None,
        database_url: Optional[str] = None,
    ) -> None:
        url = (database_url or "").strip()
        self._pg: Any = None
        self._sqlite: Any = None

        if url:
            import psycopg

            self._pg = psycopg.connect(url, connect_timeout=10)
            self._pg.autocommit = False
            with self._pg.cursor() as cur:
                cur.execute(_CREATE_SEEN_SQL)
            self._pg.commit()
            return

        path = database_path or "data/seen_posts.db"
        self._database_path = path
        if path != ":memory:":
            parent = Path(path).parent
            if str(parent) not in (".", ""):
                parent.mkdir(parents=True, exist_ok=True)
        self._sqlite = sqlite3.connect(path)
        self._sqlite.execute("PRAGMA journal_mode=WAL;")
        self._sqlite.execute(_CREATE_SEEN_SQL)
        self._sqlite.commit()

    def close(self) -> None:
        if self._pg is not None:
            self._pg.close()
            self._pg = None
        if self._sqlite is not None:
            self._sqlite.close()
            self._sqlite = None

    def is_new(self, post: Post) -> bool:
        """True, если пост ещё не видели или изменился content_hash."""
        key = _dedup_key(post)
        if self._pg is not None:
            with self._pg.cursor() as cur:
                cur.execute(
                    "SELECT content_hash FROM seen_items WHERE dedup_key = %s",
                    (key,),
                )
                row = cur.fetchone()
        else:
            cur = self._sqlite.execute(
                "SELECT content_hash FROM seen_items WHERE dedup_key = ?",
                (key,),
            )
            row = cur.fetchone()
        if row is None:
            return True
        return row[0] != post.content_hash

    def mark_seen(self, post: Post) -> None:
        """Сохранить после успешной доставки уведомления."""
        key = _dedup_key(post)
        if self._pg is not None:
            with self._pg.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO seen_items (dedup_key, content_hash)
                    VALUES (%s, %s)
                    ON CONFLICT (dedup_key) DO UPDATE
                    SET content_hash = EXCLUDED.content_hash;
                    """,
                    (key, post.content_hash),
                )
            self._pg.commit()
        else:
            self._sqlite.execute(
                """
                INSERT INTO seen_items (dedup_key, content_hash)
                VALUES (?, ?)
                ON CONFLICT(dedup_key) DO UPDATE SET content_hash = excluded.content_hash;
                """,
                (key, post.content_hash),
            )
            self._sqlite.commit()

    def filter_new_posts(self, posts: list[Post]) -> list[Post]:
        """Удобный батч: вернуть только те, что нужно отправить."""
        return [p for p in posts if self.is_new(p)]
