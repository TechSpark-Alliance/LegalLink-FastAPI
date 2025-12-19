from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from utils.helpers import convert_objectid
from main_app.auth.dependencies import require_lawyer

router = APIRouter()
clients_router = APIRouter()


def _clean_optional(value: Optional[str]) -> Optional[str]:
    """
    Standardize optional string fields: treat empty strings as None.
    """
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


class CaseCreate(BaseModel):
    client_name: str
    phone: str
    email: str
    nric: Optional[str] = None
    company_reg: Optional[str] = None
    address: Optional[str] = None
    matter_type: str
    matter_type_other: Optional[str] = None
    sub_category: Optional[str] = None
    matter_title: str
    file_code: str
    description: Optional[str] = None
    open_date: Optional[str] = None
    close_date: Optional[str] = None
    opposing_party: Optional[str] = None
    opposing_firm: Optional[str] = None
    additional_parties: Optional[int] = None
    additional_party1: Optional[str] = None
    additional_party2: Optional[str] = None
    additional_party3: Optional[str] = None
    additional_party4: Optional[str] = None
    additional_party5: Optional[str] = None
    lawyer_id: Optional[str] = None
    status: str = Field(default="Active")


@router.get("/cases")
async def list_cases(
    request: Request,
    q: Optional[str] = Query(None),
    matter_type: Optional[str] = Query(None),
    session: dict = Depends(require_lawyer),
):
    db = request.app.mongodb
    filters = {}
    if q:
        filters["$or"] = [
            {"client_name": {"$regex": q, "$options": "i"}},
            {"matter_title": {"$regex": q, "$options": "i"}},
            {"file_code": {"$regex": q, "$options": "i"}},
        ]
    if matter_type:
        filters["matter_type"] = matter_type

    cursor = db["cases"].find(filters).sort("created_at", -1)
    items = [convert_objectid(c) for c in await cursor.to_list(length=500)]
    return {"items": items, "total": len(items)}


@router.post("/cases")
async def create_case(request: Request, payload: CaseCreate, session: dict = Depends(require_lawyer)):
    db = request.app.mongodb
    # Ensure client exists (upsert by email + name)
    clients = db["clients"]
    client_query = {"email": payload.email, "full_name": payload.client_name}
    existing_client = await clients.find_one(client_query)
    if not existing_client:
        client_doc = {
            "full_name": payload.client_name,
            "email": payload.email,
            "phone": payload.phone,
            "nric": _clean_optional(payload.nric),
            "company_reg": _clean_optional(payload.company_reg),
            "address": _clean_optional(payload.address),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "role": "client",
        }
        client_result = await clients.insert_one(client_doc)
        client_id = str(client_result.inserted_id)
    else:
        client_id = str(existing_client.get("_id"))

    raw = payload.model_dump(exclude_none=False)
    doc = {
        **raw,
        "nric": _clean_optional(raw.get("nric")),
        "company_reg": _clean_optional(raw.get("company_reg")),
        "address": _clean_optional(raw.get("address")),
        "matter_type_other": _clean_optional(raw.get("matter_type_other")),
        "sub_category": _clean_optional(raw.get("sub_category")),
        "description": _clean_optional(raw.get("description")),
        "open_date": _clean_optional(raw.get("open_date")),
        "close_date": _clean_optional(raw.get("close_date")),
        "opposing_party": _clean_optional(raw.get("opposing_party")),
        "opposing_firm": _clean_optional(raw.get("opposing_firm")),
        "additional_party1": _clean_optional(raw.get("additional_party1")),
        "additional_party2": _clean_optional(raw.get("additional_party2")),
        "additional_party3": _clean_optional(raw.get("additional_party3")),
        "additional_party4": _clean_optional(raw.get("additional_party4")),
        "additional_party5": _clean_optional(raw.get("additional_party5")),
    }
    doc["created_at"] = datetime.utcnow()
    doc["updated_at"] = datetime.utcnow()
    doc["client_id"] = client_id
    result = await db["cases"].insert_one(doc)
    created = await db["cases"].find_one({"_id": result.inserted_id})
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create case")
    return {"case": convert_objectid(created)}


@router.get("/cases/{case_id}")
async def get_case(request: Request, case_id: str, session: dict = Depends(require_lawyer)):
    db = request.app.mongodb
    try:
        _id = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid case id")
    doc = await db["cases"].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"case": convert_objectid(doc)}


class CaseUpdate(BaseModel):
    client_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    nric: Optional[str] = None
    company_reg: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None
    matter_title: Optional[str] = None
    file_code: Optional[str] = None
    open_date: Optional[str] = None
    close_date: Optional[str] = None
    matter_type: Optional[str] = None
    matter_type_other: Optional[str] = None
    sub_category: Optional[str] = None
    description: Optional[str] = None
    opposing_party: Optional[str] = None
    opposing_firm: Optional[str] = None
    additional_parties: Optional[int] = None
    additional_party1: Optional[str] = None
    additional_party2: Optional[str] = None
    additional_party3: Optional[str] = None
    additional_party4: Optional[str] = None
    additional_party5: Optional[str] = None


@router.put("/cases/{case_id}")
async def update_case(request: Request, case_id: str, payload: CaseUpdate, session: dict = Depends(require_lawyer)):
    db = request.app.mongodb
    try:
        _id = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid case id")

    existing = await db["cases"].find_one({"_id": _id})
    if not existing:
        raise HTTPException(status_code=404, detail="Case not found")

    update_data = {
        k: (_clean_optional(v) if k in {
            "nric", "company_reg", "address", "matter_type_other", "sub_category",
            "description", "open_date", "close_date", "opposing_party", "opposing_firm",
            "additional_party1", "additional_party2", "additional_party3",
            "additional_party4", "additional_party5"
        } else v)
        for k, v in payload.model_dump(exclude_none=True).items()
    }
    if not update_data:
        return {"case": convert_objectid(existing)}

    # Optional: update client record if client fields are provided and case has a client_id
    if existing.get("client_id") and any(
        f in update_data for f in ["client_name", "email", "phone", "nric", "company_reg", "address"]
    ):
        try:
            await db["clients"].update_one(
                {"_id": ObjectId(existing["client_id"])},
                {
                    "$set": {
                        "full_name": update_data.get("client_name", existing.get("client_name")),
                        "email": update_data.get("email", existing.get("email")),
                        "phone": update_data.get("phone", existing.get("phone")),
                        "nric": update_data.get("nric", existing.get("nric")),
                        "company_reg": update_data.get("company_reg", existing.get("company_reg")),
                        "address": update_data.get("address", existing.get("address")),
                        "updated_at": datetime.utcnow(),
                    }
                },
                upsert=False,
            )
        except Exception:
            pass

    update_data["updated_at"] = datetime.utcnow()
    result = await db["cases"].find_one_and_update(
        {"_id": _id},
        {"$set": update_data},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"case": convert_objectid(result)}


@router.delete("/cases/{case_id}")
async def delete_case(request: Request, case_id: str, session: dict = Depends(require_lawyer)):
    db = request.app.mongodb
    try:
        _id = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid case id")
    res = await db["cases"].delete_one({"_id": _id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"deleted": True}


class ProgressCreate(BaseModel):
    note: Optional[str] = None
    status: Optional[str] = None
    event_date: Optional[str] = None


@router.get("/cases/{case_id}/progress")
async def list_progress(request: Request, case_id: str, session: dict = Depends(require_lawyer)):
    db = request.app.mongodb
    try:
        _id = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid case id")
    cursor = db["case_progress"].find({"case_id": case_id}).sort("created_at", -1)
    items = [convert_objectid(p) for p in await cursor.to_list(length=200)]
    return {"items": items}


@router.post("/cases/{case_id}/progress")
async def add_progress(request: Request, case_id: str, payload: ProgressCreate, session: dict = Depends(require_lawyer)):
    db = request.app.mongodb
    try:
        _id = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid case id")
    case = await db["cases"].find_one({"_id": _id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    entry = {
        "case_id": case_id,
        "note": payload.note or "",
        "status": payload.status,
        "event_date": payload.event_date,
        "created_at": datetime.utcnow(),
    }
    await db["case_progress"].insert_one(entry)

    if payload.status:
        await db["cases"].update_one(
            {"_id": _id},
            {"$set": {"status": payload.status, "updated_at": datetime.utcnow()}},
        )

    return {"progress": convert_objectid(entry)}


class ClientCreate(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    nric: Optional[str] = None
    company_reg: Optional[str] = None
    address: Optional[str] = None


class ClientUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    nric: Optional[str] = None
    company_reg: Optional[str] = None
    address: Optional[str] = None


@clients_router.post("/clients")
async def create_client(request: Request, payload: ClientCreate, session: dict = Depends(require_lawyer)):
    db = request.app.mongodb
    existing = await db["clients"].find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Client with this email already exists")
    raw = payload.model_dump(exclude_none=False)
    doc = {
        **raw,
        "nric": _clean_optional(raw.get("nric")),
        "company_reg": _clean_optional(raw.get("company_reg")),
        "address": _clean_optional(raw.get("address")),
    }
    doc["role"] = "client"
    doc["created_at"] = datetime.utcnow()
    doc["updated_at"] = datetime.utcnow()
    res = await db["clients"].insert_one(doc)
    created = await db["clients"].find_one({"_id": res.inserted_id})
    return {"client": convert_objectid(created)}


@clients_router.put("/clients/{client_id}")
async def update_client(request: Request, client_id: str, payload: ClientUpdate, session: dict = Depends(require_lawyer)):
    db = request.app.mongodb
    try:
        _id = ObjectId(client_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client id")
    update_data = {
        k: (_clean_optional(v) if k in {"nric", "company_reg", "address"} else v)
        for k, v in payload.model_dump(exclude_none=True).items()
    }
    if not update_data:
        doc = await db["clients"].find_one({"_id": _id})
        if not doc:
            raise HTTPException(status_code=404, detail="Client not found")
        return {"client": convert_objectid(doc)}
    update_data["updated_at"] = datetime.utcnow()
    updated = await db["clients"].find_one_and_update(
        {"_id": _id},
        {"$set": update_data},
        return_document=True
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"client": convert_objectid(updated)}


@clients_router.delete("/clients/{client_id}")
async def delete_client(request: Request, client_id: str, session: dict = Depends(require_lawyer)):
    db = request.app.mongodb
    try:
        _id = ObjectId(client_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client id")
    res = await db["clients"].delete_one({"_id": _id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"deleted": True}


@clients_router.get("/clients")
async def list_clients(request: Request, q: Optional[str] = Query(None), session: dict = Depends(require_lawyer)):
    db = request.app.mongodb
    filters: dict = {"role": "client"}
    if q:
        filters["$or"] = [
            {"full_name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
            {"phone": {"$regex": q, "$options": "i"}},
        ]
    cursor = db["clients"].find(filters).sort("created_at", -1)
    items = [convert_objectid(c) for c in await cursor.to_list(length=500)]
    return {"items": items, "total": len(items)}


@clients_router.get("/clients/{client_id}")
async def get_client(request: Request, client_id: str, session: dict = Depends(require_lawyer)):
    db = request.app.mongodb
    try:
        _id = ObjectId(client_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client id")
    doc = await db["clients"].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"client": convert_objectid(doc)}
