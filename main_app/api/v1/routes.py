from fastapi import APIRouter
from main_app.auth.user import router as user_router
from main_app.auth.admin_lawyers import router as admin_lawyers_router
from main_app.files import router as files_router
from main_app.auth.admin_users import router as admin_users_router
from main_app.cases import router as cases_router, clients_router

router = APIRouter()

router.include_router(user_router, prefix="/auth/user", tags=["auth:user"])
router.include_router(admin_lawyers_router, prefix="/auth/admin", tags=["auth:admin"])
router.include_router(admin_users_router, prefix="/auth/admin", tags=["auth:admin"])
router.include_router(files_router, tags=["files"])
router.include_router(cases_router, tags=["cases"])
router.include_router(clients_router, tags=["clients"])


@router.get("/health")
async def health_check():
    return {"status": "healthy"}
