from __future__ import annotations

import os
from typing import AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def _normalize_database_url(raw_url: str) -> tuple[str, dict]:
    """Normalize DATABASE_URL for SQLAlchemy async + asyncpg.

    Accepts common Postgres URLs (e.g. from Neon) like:
      - postgresql://user:pass@host/db?sslmode=require
      - postgres://...

    Returns:
      - url rewritten to use postgresql+asyncpg://
      - connect_args with SSL enabled when sslmode indicates it's required

    This avoids SQLAlchemy selecting the psycopg2 dialect and avoids passing
    unsupported query args like `sslmode` directly to asyncpg.
    """

    url = (raw_url or "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    parsed = urlparse(url)

    scheme = parsed.scheme
    if scheme in ("postgresql", "postgresql+psycopg2", "postgresql+psycopg"):
        scheme = "postgresql+asyncpg"
    elif scheme == "postgresql+asyncpg":
        scheme = "postgresql+asyncpg"

    sslmode: str | None = None
    filtered_pairs = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=True):
        if k.lower() == "sslmode":
            sslmode = v
            continue
        filtered_pairs.append((k, v))

    connect_args: dict = {}
    if sslmode and sslmode.lower() not in ("disable", "allow", "prefer"):
        connect_args["ssl"] = True

    normalized = parsed._replace(scheme=scheme, query=urlencode(filtered_pairs))
    return urlunparse(normalized), connect_args


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    normalized, _ = _normalize_database_url(url)
    return normalized


def create_engine() -> AsyncEngine:
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url:
        raise RuntimeError("DATABASE_URL is not set")
    url, connect_args = _normalize_database_url(raw_url)
    return create_async_engine(
        url,
        echo=False,
        pool_pre_ping=True,
        connect_args=connect_args or None,
    )

_ENGINE: AsyncEngine | None = None
_SESSIONMAKER: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine()
    return _ENGINE


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _SESSIONMAKER
    if _SESSIONMAKER is None:
        _SESSIONMAKER = async_sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SESSIONMAKER


async def get_session() -> AsyncIterator[AsyncSession]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session
