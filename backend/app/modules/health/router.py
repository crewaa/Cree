from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_db
from app.core.logging import logger

router = APIRouter()


@router.get("/health")
async def health(response: Response, db: AsyncSession = Depends(get_db)):
    """
    Liveness + readiness check.

    This deliberately touches the database. A health check that only returns a
    static payload will report healthy during a total outage, which is worse
    than having no check at all.
    """
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Health check failed: database unreachable ({})", e)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "database": "unreachable"}

    return {"status": "ok", "database": "ok"}
