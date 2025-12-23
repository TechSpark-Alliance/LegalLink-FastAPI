from fastapi import APIRouter, Request
from bson import ObjectId
from utils.helpers import convert_objectid

router = APIRouter(prefix="/lawyers", tags=["lawyers:public"])


@router.get("")
async def list_verified_lawyers(request: Request):
    """
    Public listing of verified lawyers.
    """
    db = request.app.mongodb
    cursor = db.users.find({"role": "lawyer", "status.is_verified": True})
    results = []
    async for doc in cursor:
        safe = convert_objectid(doc)
        safe.pop("password", None)
        results.append(safe)
    return {"lawyers": results}


@router.get("/{lawyer_id}")
async def get_lawyer(request: Request, lawyer_id: str):
    """
    Public detail for a verified lawyer.
    """
    try:
        oid = ObjectId(lawyer_id)
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid id")

    db = request.app.mongodb
    doc = await db.users.find_one({"_id": oid, "role": "lawyer"})
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Lawyer not found")
    safe = convert_objectid(doc)
    safe.pop("password", None)
    return {"lawyer": safe}
