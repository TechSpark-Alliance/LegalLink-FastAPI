from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from main_app.api.v1.routes import router as v1_router
from main_app.core.config import settings
from main_app.db.mongo import connect_to_mongo, close_mongo

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS for frontend (adjust origins as needed)
origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await connect_to_mongo(settings.mongodb_uri, settings.mongodb_db_name, app)


@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo()


app.include_router(v1_router, prefix="/api/v1", tags=["v1"])


@app.get("/")
def read_root():
    return {"message": "Welcome to the LegalLink FastAPI application!"}
