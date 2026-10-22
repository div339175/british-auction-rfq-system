from fastapi import APIRouter
from app.api.v1.rfqs import router as rfqs_router
from app.api.v1.quotes import router as quotes_router
from app.api.v1.activity_logs import router as logs_router

api_router = APIRouter()

api_router.include_router(rfqs_router)
api_router.include_router(quotes_router)
api_router.include_router(logs_router)
