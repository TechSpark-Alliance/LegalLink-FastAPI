from fastapi import APIRouter, Request, HTTPException, Query
from bson import ObjectId
from utils.helpers import convert_objectid

router = APIRouter()


def build_filter(role: str | None, status: str | None):
    filters: dict = {}
    if role in ("client", "lawyer"):
        filters["role"] = role
    if status:
        if status == "verified":
            filters["status.is_verified"] = True
        elif status == "pending":
            filters["status.is_verified"] = False
        elif status == "inactive":
            filters["status.is_active"] = False
    return filters


@router.get("/users")
async def list_users(
    request: Request,
    role: str | None = Query(None),
    status: str | None = Query(None),
    q: str | None = Query(None),
    page: int = 1,
    limit: int = 20,
):
    db = request.app.mongodb
    filters = build_filter(role, status)
    if q:
        filters["$or"] = [
            {"full_name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
        ]

    skip = max(0, (page - 1) * limit)
    cursor = db.users.find(filters).skip(skip).limit(limit)
    items = [convert_objectid(u) for u in await cursor.to_list(length=limit)]
    total = await db.users.count_documents(filters)
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.post("/users/{user_id}/verify")
async def verify_user(request: Request, user_id: str):
    db = request.app.mongodb
    res = await db.users.update_one(
        {"_id": ObjectId(user_id), "role": "lawyer"},
        {"$set": {"status.is_verified": True}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Verified"}


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(request: Request, user_id: str):
    db = request.app.mongodb
    res = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"status.is_active": False}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    await db.sessions.update_many({"user_id": user_id, "active": True}, {"$set": {"active": False}})
    return {"message": "Deactivated"}


@router.post("/users/{user_id}/activate")
async def activate_user(request: Request, user_id: str):
    db = request.app.mongodb
    res = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"status.is_active": True}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Activated"}


@router.delete("/users/{user_id}")
async def delete_user(request: Request, user_id: str):
    db = request.app.mongodb
    res = await db.users.delete_one({"_id": ObjectId(user_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    await db.sessions.delete_many({"user_id": user_id})
    return {"message": "Deleted"}
