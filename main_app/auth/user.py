from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime
import bcrypt
from models.users import RegisterUser, LoginInput, UserPublic
from utils.helpers import convert_objectid
from utils.email import get_email_service
from main_app.core.config import settings
from main_app.session_utils.session_functions import create_or_get_session, deactivate_session, get_active_session
from main_app.auth.dependencies import require_lawyer, get_session
from bson import ObjectId

router = APIRouter()


def _sanitize_user(user: dict) -> dict:
  safe_user = convert_objectid(user)
  safe_user.pop("password", None)
  return safe_user


@router.post("/register")
async def register_user(request: Request, data: RegisterUser):
    db = request.app.mongodb
    users = db["users"]

    existing = await users.find_one({"$or": [{"email": data.email}, {"full_name": data.full_name}]})
    if existing:
        raise HTTPException(status_code=400, detail="Email or full name already registered")

    pw_bytes = data.password.encode("utf-8")
    if len(pw_bytes) > 72:
        raise HTTPException(status_code=400, detail="Password too long (bcrypt max 72 bytes)")

    if data.role == "lawyer":
        required_fields = {
            "sijil_certificate": data.sijil_certificate,
            "expertise": data.expertise if data.expertise else [],
            "years_of_experience": data.years_of_experience,
            "about": data.about,
        }
        missing = [k for k, v in required_fields.items() if (not v and v != 0)]
        if missing or (isinstance(required_fields["expertise"], list) and len(required_fields["expertise"]) == 0):
            raise HTTPException(status_code=400, detail=f"Missing required lawyer fields: {', '.join(missing or ['expertise'])}")

    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")

    optional_fields = {
        "sijil_certificate": data.sijil_certificate,
        "sijil_certificate_url": data.sijil_certificate_url,
        "law_firm": data.law_firm,
        "law_firm_certificate": data.law_firm_certificate,
        "law_firm_certificate_url": data.law_firm_certificate_url,
        "expertise": data.expertise,
        "years_of_experience": data.years_of_experience,
        "about": data.about,
        "state": data.state,
        "city": data.city,
        "profile_image": data.profile_image,
    }
    optional_fields = {k: v for k, v in optional_fields.items() if v not in (None, "", [])}

    doc = {
        "full_name": data.full_name,
        "email": data.email,
        "password": hashed,
        "phone": data.phone,
        "role": data.role,
        "status": {"is_verified": False, "is_active": True, "last_login": None},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        **optional_fields,
    }
    await users.insert_one(doc)

    try:
        email_service = get_email_service(settings.sender_email, settings.sender_name, settings.brevo_api_key)
        email_service.send_welcome_email(
            user_email=data.email,
            user_name=data.full_name,
            firm_name=data.law_firm or "",
            user_password=data.password,
        )
    except Exception:
        # Don't fail registration if email fails
        pass

    return {"message": "Registration successful"}


@router.post("/login")
async def login_user(request: Request, login_data: LoginInput):
    db = request.app.mongodb
    users = db["users"]
    user = await users.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not bcrypt.checkpw(login_data.password.encode("utf-8"), user["password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await users.update_one({"_id": user["_id"]}, {"$set": {"status.last_login": datetime.utcnow()}})
    session = await create_or_get_session(db, user_id=str(user["_id"]), role=user.get("role", "client"))
    safe_user = _sanitize_user(user)
    return {
        "user": UserPublic(
            id=safe_user.get("_id", ""),
            full_name=safe_user.get("full_name", ""),
            email=safe_user.get("email", ""),
            phone=safe_user.get("phone"),
            state=safe_user.get("state"),
            city=safe_user.get("city"),
            role=safe_user.get("role"),
            sijil_certificate=safe_user.get("sijil_certificate"),
            law_firm=safe_user.get("law_firm"),
            law_firm_certificate=safe_user.get("law_firm_certificate"),
            expertise=safe_user.get("expertise"),
            years_of_experience=safe_user.get("years_of_experience"),
            about=safe_user.get("about"),
            profile_image=safe_user.get("profile_image"),
            is_verified=safe_user.get("status", {}).get("is_verified", False),
            is_active=safe_user.get("status", {}).get("is_active", True),
        ),
        "session": session,
    }


@router.post("/logout")
async def logout_user(request: Request, token: str):
    db = request.app.mongodb
    await deactivate_session(db, token)
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_me(request: Request, session: dict = Depends(get_session)):
    db = request.app.mongodb
    try:
        user_id = ObjectId(session["user_id"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")
    user = await db["users"].find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": _sanitize_user(user)}


@router.put("/me")
async def update_me(request: Request, payload: dict, session: dict = Depends(get_session)):
    """
    Update editable lawyer fields. Frontend currently read-only, but kept for future.
    """
    db = request.app.mongodb
    try:
        user_id = ObjectId(session["user_id"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")

    allowed_fields = {
        "full_name",
        "phone",
        "state",
        "city",
        "about",
        "expertise",
        "years_of_experience",
        "law_firm",
        "sijil_certificate",
        "law_firm_certificate",
        "profile_image",
        "password",
    }
    update_data = {k: v for k, v in payload.items() if k in allowed_fields and v not in (None, "")}
    if "password" in update_data:
        pw_bytes = str(update_data["password"]).encode("utf-8")
        if len(pw_bytes) > 72:
            raise HTTPException(status_code=400, detail="Password too long (bcrypt max 72 bytes)")
        update_data["password"] = bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")
    if not update_data:
        user = await db["users"].find_one({"_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"user": _sanitize_user(user)}

    update_data["updated_at"] = datetime.utcnow()
    updated = await db["users"].find_one_and_update(
        {"_id": user_id},
        {"$set": update_data},
        return_document=True,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": _sanitize_user(updated)}


@router.get("/session")
async def validate_session(request: Request, token: str):
    db = request.app.mongodb
    session = await get_active_session(db, token)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return {"session": session}
