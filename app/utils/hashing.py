from __future__ import annotations

import hashlib


def compute_content_hash(*, title: str, link: str, summary_or_body: str) -> str:
    """Детерминированный SHA-256 по полям, влияющим на «содержание» уведомления."""
    normalized = "\n".join(
        part.strip()
        for part in (
            title.strip().casefold(),
            link.strip(),
            summary_or_body.strip().casefold(),
        )
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
