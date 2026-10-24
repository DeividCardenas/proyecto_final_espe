from fastapi import APIRouter

from app.api.v1.endpoints import analytics, crashes, health, permits, predict, risk

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(crashes.router, prefix="/crashes", tags=["crashes"])
api_router.include_router(permits.router, prefix="/permits", tags=["permits"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(predict.router, prefix="/predict", tags=["predict"])
