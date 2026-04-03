from fastapi import APIRouter
from sqlalchemy import text

from leads.db.engine import AsyncSessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Verifica se a API e o banco estão acessíveis."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        return {"status": "degraded", "db": str(e)}
