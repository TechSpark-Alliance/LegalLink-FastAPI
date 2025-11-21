from fastapi import FastAPI
from main_app.api.v1.routes import router as v1_router

app = FastAPI()

app.include_router(v1_router, prefix="/api/v1", tags=["v1"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the LegalLink FastAPI application!"}