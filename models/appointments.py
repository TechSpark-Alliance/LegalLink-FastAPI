from typing import List, Optional

from pydantic import BaseModel, Field


class AvailabilitySlotIn(BaseModel):
    date: str = Field(..., description="ISO date (YYYY-MM-DD)")
    start: str = Field(..., description="Start time, e.g. 09:00")
    end: str = Field(..., description="End time, e.g. 17:00")


class AvailabilitySlotOut(BaseModel):
    id: str
    date: str
    start: str
    end: str


class BulkAvailabilityResponse(BaseModel):
    created: List[AvailabilitySlotOut]
    skipped: List[str] = Field(default_factory=list, description="Dates skipped due to duplicates")


class AppointmentUpdate(BaseModel):
    status: str = Field(..., description="pending | accepted | rejected | cancelled")
    reason: Optional[str] = None


class AppointmentOut(BaseModel):
    id: str
    lawyer_id: str
    client_id: Optional[str] = None
    date: str
    time: str
    duration_minutes: Optional[int] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    status: str
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AppointmentCreate(BaseModel):
    lawyer_id: str = Field(..., description="Target lawyer ID")
    date: str = Field(..., description="ISO date (YYYY-MM-DD)")
    time: str = Field(..., description="Start time, e.g. 09:00")
    duration_minutes: Optional[int] = Field(default=60)
    mode: Optional[str] = None
    appointment_type: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None
    meeting_link: Optional[str] = None
    notes: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None


class CancelAppointment(BaseModel):
    reason: Optional[str] = None
