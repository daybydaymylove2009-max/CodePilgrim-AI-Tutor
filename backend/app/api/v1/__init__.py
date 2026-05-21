from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.learning import router as learning_router
from app.api.v1.ws import router as ws_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(knowledge_router)
api_router.include_router(learning_router)
api_router.include_router(ws_router)
