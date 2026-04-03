from fastapi import APIRouter, BackgroundTasks

from leads.ingestion.pipeline import PipelineStatus, get_status, run_full_pipeline

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/trigger", status_code=202)
async def trigger_ingestion(
    background_tasks: BackgroundTasks,
    period: str | None = None,
    skip_download: bool = False,
):
    """
    Inicia o pipeline de ingestão dos dados da Receita Federal em background.
    Retorna imediatamente com status 202 Accepted.
    """
    status = get_status()
    if not status.done and status.stage != "idle":
        return {"message": "Pipeline já em execução.", "status": status.to_dict()}

    background_tasks.add_task(
        run_full_pipeline,
        period=period,
        skip_download=skip_download,
    )
    return {"message": "Pipeline iniciado.", "period": period}


@router.get("/status", response_model=dict)
async def ingestion_status():
    """Retorna o status atual do pipeline de ingestão."""
    return get_status().to_dict()
