from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from database import CacheEntry


def _hash_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_get(db: Session, namespace: str, text: str) -> dict | None:
    key = f"{namespace}:{_hash_key(text)}"
    row = db.get(CacheEntry, key)
    if not row:
        return None
    now = datetime.now(timezone.utc)
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        db.delete(row)
        db.commit()
        return None
    try:
        return json.loads(row.cache_value)
    except json.JSONDecodeError:
        return None


def cache_set(db: Session, namespace: str, text: str, value: dict, ttl_hours: int = 24) -> str:
    key = f"{namespace}:{_hash_key(text)}"
    expires = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    row = db.get(CacheEntry, key)
    payload = json.dumps(value, ensure_ascii=False)
    if row:
        row.cache_value = payload
        row.expires_at = expires
    else:
        db.add(CacheEntry(cache_key=key, cache_value=payload, expires_at=expires))
    db.commit()
    return key
