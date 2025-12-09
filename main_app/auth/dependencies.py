from fastapi import Depends, HTTPException, Request, status
from typing import Optional
from main_app.session_utils.session_functions import get_active_session


async def get_session(request: Request) -> dict:
    """
    Resolve an active session from Authorization header.
    Accepts: Authorization: Bearer <token>
    """
    auth_header: Optional[str] = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid auth header")

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    session = await get_active_session(request.app.mongodb, token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")
    return session


async def require_lawyer(session: dict = Depends(get_session)) -> dict:
    """
    Ensure the active session belongs to a lawyer.
    """
    if session.get("role") != "lawyer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return session
