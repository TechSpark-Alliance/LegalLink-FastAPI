from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal, List
from models.billing import SubscriptionInfo


class RegisterUser(BaseModel):
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    password: str
    phone: str
    state: Optional[str] = None
    city: Optional[str] = None
    role: Literal["client", "lawyer"] = "client"
    profile_image: Optional[str] = None
    # Lawyer-specific (optional for clients)
    sijil_certificate: Optional[str] = None  # file ref or name (required for lawyers)
    sijil_certificate_url: Optional[str] = None
    law_firm: Optional[str] = None  # optional for lawyers
    law_firm_certificate: Optional[str] = None  # optional for lawyers
    law_firm_certificate_url: Optional[str] = None
    expertise: Optional[List[str]] = None  # required for lawyers
    years_of_experience: Optional[float] = None  # required for lawyers
    about: Optional[str] = None  # required for lawyers


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    role: Optional[str] = None
    profile_image: Optional[str] = None
    sijil_certificate: Optional[str] = None
    sijil_certificate_url: Optional[str] = None
    law_firm: Optional[str] = None
    law_firm_certificate: Optional[str] = None
    law_firm_certificate_url: Optional[str] = None
    expertise: Optional[List[str]] = None
    years_of_experience: Optional[float] = None
    about: Optional[str] = None
    is_verified: bool = False
    is_active: bool = True
    subscription: Optional[SubscriptionInfo] = None
