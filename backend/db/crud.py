from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Message, Session


async def get_or_create_session(db: AsyncSession, session_id: str) -> Session:
    existing = await db.get(Session, session_id)
    if existing:
        return existing

    s = Session(id=session_id)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def create_message(
    db: AsyncSession,
    *,
    session_id: str,
    role: str,
    content: str,
    tool_calls: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Message:
    await get_or_create_session(db, session_id)

    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        extra=extra,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def list_messages(db: AsyncSession, session_id: str) -> List[Message]:
    stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def delete_history(db: AsyncSession, session_id: str) -> None:
    await db.execute(delete(Message).where(Message.session_id == session_id))
    await db.execute(delete(Session).where(Session.id == session_id))
    await db.commit()
