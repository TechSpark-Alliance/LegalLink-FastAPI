from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request

from main_app.auth.dependencies import get_session, require_lawyer
from models.appointments import (
    AppointmentOut,
    AppointmentUpdate,
    AvailabilitySlotIn,
    AvailabilitySlotOut,
    BulkAvailabilityResponse,
    AppointmentCreate,
)
from utils.helpers import convert_objectid

router = APIRouter(prefix="/lawyers", tags=["lawyers:appointments"])


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


def _to_out(doc: dict, *, id_key: str = "_id") -> dict:
    if not doc:
        return doc
    doc = convert_objectid(doc)
    if id_key in doc:
        doc["id"] = doc.pop(id_key)
    if isinstance(doc.get("status"), str):
        doc["status"] = doc["status"].capitalize()
    return doc


@router.get("/availability", response_model=List[AvailabilitySlotOut])
async def list_availability(request: Request, session: dict = Depends(require_lawyer)):
    db = request.app.mongodb
    lawyer_id = _oid(session["user_id"])
    cursor = db.lawyers_availability.find({"lawyer_id": lawyer_id}).sort([("date", 1), ("start", 1)])
    results = []
    async for doc in cursor:
        results.append(_to_out(doc))
    return results


@router.post("/availability", response_model=BulkAvailabilityResponse)
async def add_availability(
    request: Request,
    payload: List[AvailabilitySlotIn],
    session: dict = Depends(require_lawyer),
):
    if not payload:
        raise HTTPException(status_code=400, detail="No slots provided")
    db = request.app.mongodb
    lawyer_id = _oid(session["user_id"])
    created_docs = []
    skipped: list[str] = []
    to_insert = []

    for slot in payload:
        date_str = str(slot.date)
        duplicate = await db.lawyers_availability.find_one(
            {
                "lawyer_id": lawyer_id,
                "date": date_str,
                "start": slot.start,
                "end": slot.end,
            }
        )
        if duplicate:
            skipped.append(date_str)
            continue
        to_insert.append(
            {
                "lawyer_id": lawyer_id,
                "date": date_str,
                "start": slot.start,
                "end": slot.end,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

    if to_insert:
        result = await db.lawyers_availability.insert_many(to_insert)
        for raw, ins_id in zip(to_insert, result.inserted_ids):
            raw["_id"] = ins_id
            created_docs.append(_to_out(raw))

    return BulkAvailabilityResponse(created=created_docs, skipped=skipped)


@router.delete("/availability/{slot_id}")
async def delete_availability(slot_id: str, request: Request, session: dict = Depends(require_lawyer)):
    db = request.app.mongodb
    lawyer_id = _oid(session["user_id"])
    deleted = await db.lawyers_availability.find_one_and_delete(
        {"_id": _oid(slot_id), "lawyer_id": lawyer_id}
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Slot not found")
    return {"message": "Deleted", "slot": _to_out(deleted)}


@router.get("/{lawyer_id}/availability", response_model=List[AvailabilitySlotOut], include_in_schema=True)
async def list_availability_public(lawyer_id: str, request: Request):
    """
    Public endpoint for clients to view a lawyer's published availability.
    """
    db = request.app.mongodb
    lawyer_oid = _oid(lawyer_id)
    cursor = db.lawyers_availability.find({"lawyer_id": lawyer_oid}).sort([("date", 1), ("start", 1)])
    results = []
    async for doc in cursor:
        results.append(_to_out(doc))
    return results


@router.get("/{lawyer_id}/appointments/public", response_model=List[AppointmentOut], include_in_schema=True)
async def list_appointments_public(
    lawyer_id: str,
    request: Request,
    status: Optional[str] = "accepted",
    date: Optional[str] = None,
):
    """
    Public read-only endpoint so clients can see taken slots for a lawyer.
    Defaults to accepted appointments; optional date filter (YYYY-MM-DD).
    """
    db = request.app.mongodb
    lawyer_oid = _oid(lawyer_id)
    query: dict = {"lawyer_id": lawyer_oid}
    if status:
        query["status"] = status.lower()
    if date:
        query["date"] = date
    cursor = db.appointments.find(query).sort([("date", 1), ("time", 1)])
    results = []
    async for doc in cursor:
        results.append(_to_out(doc))
    return results


@router.post("/appointments", response_model=AppointmentOut, include_in_schema=True)
async def create_appointment(
    request: Request,
    payload: AppointmentCreate,
    session: dict = Depends(get_session),
):
    """
    Client creates an appointment with a lawyer.
    """
    db = request.app.mongodb
    lawyer_oid = _oid(payload.lawyer_id)
    client_id = _oid(session["user_id"])

    doc = {
        "lawyer_id": lawyer_oid,
        "client_id": client_id,
        "date": payload.date,
        "time": payload.time,
        "duration_minutes": payload.duration_minutes or 60,
        "client_name": payload.client_name or session.get("full_name") or "",
        "client_email": payload.client_email or session.get("email") or "",
        "client_phone": payload.client_phone or session.get("phone") or "",
        "mode": (payload.mode or "").lower() or "in-person",
        "appointment_type": payload.appointment_type or "Initial consultation",
        "location": {
            "name": payload.location_name or "",
            "address": payload.location_address or "",
        },
        "meeting_link": payload.meeting_link,
        "notes": payload.notes,
        "status": "pending",
        "reason": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await db.appointments.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.get("/appointments", response_model=List[AppointmentOut])
async def list_appointments(
    request: Request,
    status: Optional[str] = None,
    session: dict = Depends(require_lawyer),
):
    db = request.app.mongodb
    lawyer_id = _oid(session["user_id"])
    query: dict = {"lawyer_id": lawyer_id}
    if status:
        query["status"] = status.lower()
    cursor = db.appointments.find(query).sort([("date", 1), ("time", 1)])
    results = []
    async for doc in cursor:
        results.append(_to_out(doc))
    return results


@router.delete("/appointments/{appointment_id}", include_in_schema=True)
async def delete_appointment(
    appointment_id: str,
    request: Request,
    session: dict = Depends(get_session),
):
    """
    Allow the owning client to delete their appointment (cancels and removes it).
    """
    db = request.app.mongodb
    client_id = _oid(session["user_id"])
    deleted = await db.appointments.find_one_and_delete({"_id": _oid(appointment_id), "client_id": client_id})
    if not deleted:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"message": "Deleted", "id": str(appointment_id)}


@router.patch("/appointments/{appointment_id}", response_model=AppointmentOut)
async def update_appointment(
    appointment_id: str,
    request: Request,
    payload: AppointmentUpdate,
    session: dict = Depends(require_lawyer),
):
    db = request.app.mongodb
    lawyer_id = _oid(session["user_id"])
    allowed_status = {"pending", "accepted", "rejected", "cancelled"}
    if payload.status.lower() not in allowed_status:
        raise HTTPException(status_code=400, detail="Invalid status")

    appointment = await db.appointments.find_one({"_id": _oid(appointment_id), "lawyer_id": lawyer_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    update_doc = {
        "status": payload.status.lower(),
        "updated_at": datetime.utcnow(),
    }
    if payload.reason is not None:
        update_doc["reason"] = payload.reason

    updated = await db.appointments.find_one_and_update(
        {"_id": _oid(appointment_id), "lawyer_id": lawyer_id},
        {"$set": update_doc},
        return_document=True,
    )
    return _to_out(updated)


@router.get("/appointments/client", response_model=List[AppointmentOut], include_in_schema=True)
async def list_client_appointments(
    request: Request,
    session: dict = Depends(get_session),
):
    """
    List appointments for the logged-in client (most recent first).
    """
    db = request.app.mongodb
    client_id_raw = session.get("user_id")
    try:
        client_id = ObjectId(client_id_raw)
    except Exception:
        # Session is invalid/stale or user_id is not a Mongo ObjectId; treat as unauthorized.
        raise HTTPException(status_code=401, detail="Invalid session")
    cursor = db.appointments.find({"client_id": client_id}).sort([("updated_at", -1)])
    results = []
    async for doc in cursor:
        results.append(_to_out(doc))
    return results


@router.get("/appointments/{appointment_id}", response_model=AppointmentOut, include_in_schema=True)
async def get_appointment_for_client(
    appointment_id: str,
    request: Request,
    session: dict = Depends(get_session),
):
    """
    Allow the owning client to fetch their appointment details (used for status refresh).
    """
    db = request.app.mongodb
    client_id = _oid(session["user_id"])
    doc = await db.appointments.find_one({"_id": _oid(appointment_id), "client_id": client_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return _to_out(doc)
