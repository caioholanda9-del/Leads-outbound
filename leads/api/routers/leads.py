from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from leads.db.engine import get_async_session
from leads.db.repository import count_leads, filter_leads, get_cnae_list, get_municipio_list, stream_leads
from leads.filtering.exporter import export_csv, export_excel
from leads.filtering.schemas import (
    CnaeItem,
    FilterRequest,
    FilterResponse,
    MunicipioItem,
)

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/cnaes", response_model=list[CnaeItem])
async def list_cnaes(session: AsyncSession = Depends(get_async_session)):
    """Retorna todos os códigos CNAE disponíveis."""
    return await get_cnae_list(session)


@router.get("/municipios", response_model=list[MunicipioItem])
async def list_municipios(
    uf: str | None = Query(None, description="Filtrar municípios por UF"),
    session: AsyncSession = Depends(get_async_session),
):
    """Retorna municípios, opcionalmente filtrados por UF."""
    return await get_municipio_list(session, uf)


@router.post("/filter", response_model=FilterResponse)
async def filter_leads_endpoint(
    req: FilterRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Filtra leads por CNAE e demais critérios. Retorna resultados paginados.
    """
    total = await count_leads(session, req)
    results = await filter_leads(session, req)
    return FilterResponse(
        total=total,
        limit=req.limit,
        offset=req.offset,
        results=results,
    )


@router.get("/export")
async def export_leads(
    cnaes_principal: list[str] = Query(..., description="Códigos CNAE principais"),
    ufs: list[str] | None = Query(None),
    portes: list[int] | None = Query(None),
    situacao_cadastral: int = Query(2),
    apenas_com_email: bool = Query(False),
    apenas_com_telefone: bool = Query(False),
    incluir_cnae_secundario: bool = Query(False),
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Exporta leads filtrados como CSV ou Excel (streaming).
    """
    req = FilterRequest(
        cnaes_principal=cnaes_principal,
        ufs=ufs,
        portes=portes,
        situacao_cadastral=situacao_cadastral,
        apenas_com_email=apenas_com_email,
        apenas_com_telefone=apenas_com_telefone,
        incluir_cnae_secundario=incluir_cnae_secundario,
        limit=100_000,
        offset=0,
    )

    if format == "xlsx":
        leads_gen = stream_leads(session, req)
        data = await export_excel(leads_gen)
        return StreamingResponse(
            iter([data]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=leads.xlsx"},
        )
    else:
        leads_gen = stream_leads(session, req)
        return StreamingResponse(
            export_csv(leads_gen),
            media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": "attachment; filename=leads.csv"},
        )
