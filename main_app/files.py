import os
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
  try:
    suffix = Path(file.filename).suffix
    safe_name = Path(file.filename).stem.replace(" ", "_")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    new_name = f"{safe_name}_{timestamp}{suffix}"
    dest = UPLOAD_DIR / new_name

    with dest.open("wb") as buffer:
      buffer.write(await file.read())

    url = f"/uploads/{new_name}"
    return {"filename": file.filename, "stored_name": new_name, "url": url}
  except Exception as e:
    raise HTTPException(status_code=500, detail="File upload failed")
