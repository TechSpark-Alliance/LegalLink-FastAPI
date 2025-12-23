from datetime import datetime, timedelta
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request

from main_app.auth.dependencies import get_session
from models.chat import (
    ClearHistoryInput,
    ConversationOut,
    MessageOut,
    PresenceOut,
    PresenceUpdate,
    SendMessageInput,
)
from utils.helpers import convert_objectid

router = APIRouter(prefix="/chat", tags=["chat"])

MESSAGE_LIMIT = 15  # per user per conversation
PRESENCE_TTL_SECONDS = 90


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


def _conv_out(doc: dict) -> ConversationOut:
    doc = convert_objectid(doc)
    doc["id"] = doc.pop("_id")
    participants = [str(pid) for pid in doc.get("participants", [])]
    unread_map = doc.get("unread", {})
    unread_total = sum(int(v) for v in unread_map.values()) if isinstance(unread_map, dict) else 0
    return ConversationOut(
        id=doc["id"],
        participants=participants,
        last_message=doc.get("last_message"),
        last_message_at=doc.get("last_message_at"),
        unread_count=unread_total,
    )


def _msg_out(doc: dict) -> MessageOut:
    doc = convert_objectid(doc)
    doc["id"] = doc.pop("_id")
    return MessageOut(
        id=doc["id"],
        conversation_id=str(doc.get("conversation_id")),
        sender_id=str(doc.get("sender_id")),
        text=doc.get("text", ""),
        created_at=doc.get("created_at"),
    )


@router.post("/presence/heartbeat", response_model=PresenceOut)
async def heartbeat(request: Request, payload: PresenceUpdate, session: dict = Depends(get_session)):
    db = request.app.mongodb
    user_id = _oid(session["user_id"])
    now = datetime.utcnow()
    await db.presence.update_one(
        {"_id": user_id},
        {"$set": {"last_seen": now, "status": payload.status or "online"}},
        upsert=True,
    )
    return PresenceOut(user_id=str(user_id), online=True, last_seen=now.isoformat())


@router.get("/presence", response_model=List[PresenceOut])
async def presence(request: Request, user_ids: str, session: dict = Depends(get_session)):
    """
    Query presence for a comma-separated list of user ids.
    """
    db = request.app.mongodb
    ids = [uid.strip() for uid in user_ids.split(",") if uid.strip()]
    oid_map = {}
    for uid in ids:
        try:
            oid_map[uid] = _oid(uid)
        except HTTPException:
            continue
    cursor = db.presence.find({"_id": {"$in": list(oid_map.values())}})
    results = []
    now = datetime.utcnow()
    async for doc in cursor:
        last_seen = doc.get("last_seen")
        online = False
        if isinstance(last_seen, datetime):
          online = (now - last_seen) <= timedelta(seconds=PRESENCE_TTL_SECONDS)
        results.append(PresenceOut(user_id=str(doc["_id"]), online=online, last_seen=last_seen.isoformat() if last_seen else None))
    # Fill missing as offline
    present_ids = {p.user_id for p in results}
    for uid in ids:
        if uid not in present_ids:
            results.append(PresenceOut(user_id=uid, online=False, last_seen=None))
    return results


@router.get("/conversations", response_model=List[ConversationOut])
async def list_conversations(request: Request, session: dict = Depends(get_session)):
    db = request.app.mongodb
    user_id = _oid(session["user_id"])
    cursor = db.conversations.find({"participants": user_id}).sort("last_message_at", -1)
    items = []
    async for doc in cursor:
        items.append(_conv_out(doc))
    return items


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageOut])
async def list_messages(conversation_id: str, request: Request, session: dict = Depends(get_session)):
    db = request.app.mongodb
    user_id = _oid(session["user_id"])
    conv = await db.conversations.find_one({"_id": _oid(conversation_id), "participants": user_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    cleared_at_map = conv.get("cleared_at", {}) or {}
    cleared_at = cleared_at_map.get(str(user_id))
    cutoff = cleared_at if isinstance(cleared_at, datetime) else None
    query: dict = {"conversation_id": conv["_id"], "deleted_for": {"$ne": str(user_id)}}
    if cutoff:
        query["created_at"] = {"$gt": cutoff}
    cursor = db.messages.find(query).sort("created_at", 1)
    msgs = []
    async for doc in cursor:
        msgs.append(_msg_out(doc))
    return msgs


@router.post("/messages", response_model=MessageOut)
async def send_message(request: Request, payload: SendMessageInput, session: dict = Depends(get_session)):
    db = request.app.mongodb
    user_id = _oid(session["user_id"])
    conv_id = None
    participants = []

    if payload.conversation_id:
        conv = await db.conversations.find_one({"_id": _oid(payload.conversation_id), "participants": user_id})
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conv_id = conv["_id"]
        participants = conv.get("participants", [])
    else:
        if not payload.to_user_id:
            raise HTTPException(status_code=400, detail="to_user_id is required when no conversation_id")
        other_id = _oid(payload.to_user_id)
        participants = sorted([user_id, other_id], key=lambda x: str(x))
        conv = await db.conversations.find_one({"participants": participants})
        if not conv:
            now = datetime.utcnow()
            conv_doc = {
                "participants": participants,
                "created_at": now,
                "updated_at": now,
                "last_message": None,
                "last_message_at": None,
                "unread": {},
                "message_counts": {},
                "cleared_at": {},
            }
            conv_id = (await db.conversations.insert_one(conv_doc)).inserted_id
            conv = {**conv_doc, "_id": conv_id}
        else:
            conv_id = conv["_id"]

    # message limit check
    msg_counts = conv.get("message_counts", {}) or {}
    sender_count = int(msg_counts.get(str(user_id), 0))
    if sender_count >= MESSAGE_LIMIT:
        raise HTTPException(status_code=403, detail="Message limit reached for this conversation")

    now = datetime.utcnow()
    msg_doc = {
        "conversation_id": conv_id,
        "sender_id": user_id,
        "text": payload.text,
        "created_at": now,
        "deleted_for": [],
    }
    inserted = await db.messages.insert_one(msg_doc)

    msg_counts[str(user_id)] = sender_count + 1
    unread = conv.get("unread", {}) or {}
    for pid in participants:
        pid_str = str(pid)
        unread[pid_str] = 0 if pid == user_id else int(unread.get(pid_str, 0)) + 1

    await db.conversations.update_one(
        {"_id": conv_id},
        {
            "$set": {
                "last_message": payload.text,
                "last_message_at": now,
                "updated_at": now,
                "message_counts": msg_counts,
                "unread": unread,
            }
        },
    )

    msg_doc["_id"] = inserted.inserted_id
    return _msg_out(msg_doc)


@router.post("/conversations/clear")
async def clear_history(request: Request, payload: ClearHistoryInput, session: dict = Depends(get_session)):
    db = request.app.mongodb
    user_id = _oid(session["user_id"])
    conv = await db.conversations.find_one({"_id": _oid(payload.conversation_id), "participants": user_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    now = datetime.utcnow()
    cleared_at = conv.get("cleared_at", {}) or {}
    cleared_at[str(user_id)] = now
    await db.conversations.update_one({"_id": conv["_id"]}, {"$set": {"cleared_at": cleared_at}})
    return {"message": "Cleared"}
