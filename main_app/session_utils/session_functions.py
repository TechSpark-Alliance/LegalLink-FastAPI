from datetime import datetime, timedelta
from typing import Optional
import secrets
from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.helpers import convert_objectid

SESSION_DURATION_HOURS = 12


async def create_or_get_session(db: AsyncIOMotorDatabase, user_id: str, role: str) -> dict:
    now = datetime.utcnow()
    existing = await db.sessions.find_one(
        {"user_id": user_id, "role": role, "active": True, "expires_at": {"$gt": now}}
    )
    if existing:
        existing["id"] = str(existing.pop("_id"))
        return convert_objectid(existing)

    await db.sessions.update_many(
        {"user_id": user_id, "role": role, "active": True, "expires_at": {"$lt": now}},
        {"$set": {"active": False}},
    )

    token = secrets.token_urlsafe(32)
    expires_at = now + timedelta(hours=SESSION_DURATION_HOURS)
    session = {
        "user_id": user_id,
        "role": role,
        "token": token,
        "expires_at": expires_at,
        "active": True,
        "created_at": now,
        "deactivated_at": None,
    }
    result = await db.sessions.insert_one(session)
    session["id"] = str(result.inserted_id)
    return convert_objectid(session)


async def deactivate_session(db: AsyncIOMotorDatabase, token: str):
    await db.sessions.update_one(
        {"token": token, "active": True},
        {"$set": {"active": False, "deactivated_at": datetime.utcnow()}},
    )


async def get_active_session(db: AsyncIOMotorDatabase, token: str) -> Optional[dict]:
    now = datetime.utcnow()
    session = await db.sessions.find_one({"token": token, "active": True, "expires_at": {"$gt": now}})
    if session:
        session["id"] = str(session.pop("_id"))
        return convert_objectid(session)
    return None
