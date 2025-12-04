from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from utils.helpers import convert_objectid
from utils.email import get_email_service
from main_app.core.config import settings

router = APIRouter()


class VerifyRequest(BaseModel):
    user_id: Optional[str] = None
    email: Optional[EmailStr] = None
    verify: bool = True
    reason: Optional[str] = None


@router.get("/lawyers/pending")
async def list_pending_lawyers(request: Request):
    db = request.app.mongodb
    users = db["users"]
    cursor = users.find({"role": "lawyer", "status.is_verified": False})
    results = []
    async for doc in cursor:
        safe = convert_objectid(doc)
        safe.pop("password", None)
        results.append(safe)
    return {"lawyers": results}


@router.post("/lawyers/verify")
async def verify_lawyer(request: Request, payload: VerifyRequest):
    if not payload.user_id and not payload.email:
        raise HTTPException(status_code=400, detail="Provide either user_id or email")

    db = request.app.mongodb
    users = db["users"]

    query = {"role": "lawyer"}
    if payload.user_id:
        try:
            query["_id"] = ObjectId(payload.user_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid user_id format")
    if payload.email:
        query["email"] = payload.email

    # fetch user first
    target = await users.find_one(query)
    if not target:
        raise HTTPException(status_code=404, detail="Lawyer not found")

    if payload.verify:
        update = {
            "$set": {
                "status.is_verified": True,
                "status.verified_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        }
        result = await users.find_one_and_update(query, update, return_document=True)
        safe = convert_objectid(result)
        safe.pop("password", None)
        return {"user": safe, "verified": True}
    else:
        await users.delete_one(query)
        # Optionally clean sessions
        await request.app.mongodb["sessions"].delete_many({"user_id": str(target.get("_id"))})
        try:
            email_service = get_email_service(settings.sender_email, settings.sender_name, settings.brevo_api_key)
            email_service.send_rejection_email(target.get("email", ""), payload.reason)
        except Exception:
            pass
        return {"message": "Lawyer account rejected and removed"}
