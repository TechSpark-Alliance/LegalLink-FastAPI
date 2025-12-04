from datetime import datetime
from pydantic import BaseModel


class SessionCreate(BaseModel):
    user_id: str
    role: str
    token: str
    expires_at: datetime
    active: bool = True
    created_at: datetime
    deactivated_at: datetime | None = None


class SessionInDB(SessionCreate):
    id: str
