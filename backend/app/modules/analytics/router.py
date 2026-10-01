from fastapi import APIRouter

from app.core.db import DB
from app.core.deps import CurrentUser
from app.modules.analytics import service
from app.modules.analytics.schemas import DashboardData

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardData, response_model_exclude_none=True)
async def dashboard(db: DB, user: CurrentUser) -> DashboardData:
    """KPI cards, ECharts series and lists for the caller's role (cached in Redis for 60 s per user)."""
    return await service.get_dashboard(db, user)
