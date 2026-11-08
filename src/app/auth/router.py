from fastapi import APIRouter

from app.auth.routes import account, email, password, registration, session

router = APIRouter(prefix="/auth", tags=["auth"])
router.include_router(registration.router)
router.include_router(session.router)
router.include_router(account.router)
router.include_router(email.router)
router.include_router(password.router)
