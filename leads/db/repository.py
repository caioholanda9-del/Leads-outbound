from typing import Any

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from leads.db.models import Cnae, Empresa, Estabelecimento, Municipio
from leads.filtering.schemas import FilterRequest, LeadResult


async def get_cnae_list(session: AsyncSession) -> list[dict]:
    """Retorna todos os CNAEs ordenados pelo código."""
    result = await session.execute(select(Cnae).order_by(Cnae.codigo))
    return [{"codigo": c.codigo, "descricao": c.descricao} for c in result.scalars()]


async def get_municipio_list(session: AsyncSession, uf: str | None = None) -> list[dict]:
    """Retorna municípios, opcionalmente filtrados por UF via join."""
    stmt = select(Municipio).order_by(Municipio.descricao)
    if uf:
        stmt = (
            select(Municipio)
            .join(
                Estabelecimento,
                Estabelecimento.municipio == Municipio.codigo,
            )
            .where(Estabelecimento.uf == uf)
            .distinct()
            .order_by(Municipio.descricao)
        )
    result = await session.execute(stmt)
    return [{"codigo": m.codigo, "descricao": m.descricao} for m in result.scalars()]


def _build_query(req: FilterRequest):
    """Constrói a query SQLAlchemy base a partir de um FilterRequest."""
    stmt = (
        select(
            Estabelecimento.cnpj_completo,
            Empresa.razao_social,
            Estabelecimento.nome_fantasia,
            Empresa.porte_empresa,
            Estabelecimento.situacao_cadastral,
            Estabelecimento.data_inicio_atividade,
            Estabelecimento.cnae_fiscal_principal,
            Estabelecimento.cnae_fiscal_secundaria,
            Estabelecimento.uf,
            Estabelecimento.municipio,
            Estabelecimento.logradouro,
            Estabelecimento.numero,
            Estabelecimento.complemento,
            Estabelecimento.bairro,
            Estabelecimento.cep,
            Estabelecimento.ddd1,
            Estabelecimento.telefone1,
            Estabelecimento.ddd2,
            Estabelecimento.telefone2,
            Estabelecimento.correio_eletronico,
        )
        .join(Empresa, Empresa.cnpj_basico == Estabelecimento.cnpj_basico)
    )

    # CNAE principal (obrigatório)
    cnae_conditions = [
        Estabelecimento.cnae_fiscal_principal.in_(req.cnaes_principal)
    ]

    # CNAE secundário (opcional)
    if req.incluir_cnae_secundario:
        secondary_conditions = [
            Estabelecimento.cnae_fiscal_secundaria.contains(code)
            for code in req.cnaes_principal
        ]
        stmt = stmt.where(
            or_(Estabelecimento.cnae_fiscal_principal.in_(req.cnaes_principal), *secondary_conditions)
        )
    else:
        stmt = stmt.where(Estabelecimento.cnae_fiscal_principal.in_(req.cnaes_principal))

    # Situação cadastral
    stmt = stmt.where(Estabelecimento.situacao_cadastral == req.situacao_cadastral)

    # UFs
    if req.ufs:
        stmt = stmt.where(Estabelecimento.uf.in_(req.ufs))

    # Municípios
    if req.municipios:
        stmt = stmt.where(Estabelecimento.municipio.in_(req.municipios))

    # Porte
    if req.portes:
        stmt = stmt.where(Empresa.porte_empresa.in_(req.portes))

    # Data de abertura
    if req.data_abertura_de:
        stmt = stmt.where(Estabelecimento.data_inicio_atividade >= req.data_abertura_de)
    if req.data_abertura_ate:
        stmt = stmt.where(Estabelecimento.data_inicio_atividade <= req.data_abertura_ate)

    # Apenas com e-mail
    if req.apenas_com_email:
        stmt = stmt.where(
            Estabelecimento.correio_eletronico.is_not(None),
            Estabelecimento.correio_eletronico != "",
        )

    # Apenas com telefone
    if req.apenas_com_telefone:
        stmt = stmt.where(
            Estabelecimento.telefone1.is_not(None),
            Estabelecimento.telefone1 != "",
        )

    return stmt


async def count_leads(session: AsyncSession, req: FilterRequest) -> int:
    """Conta o total de leads que correspondem ao filtro."""
    subq = _build_query(req).subquery()
    result = await session.execute(select(func.count()).select_from(subq))
    return result.scalar_one()


async def filter_leads(
    session: AsyncSession, req: FilterRequest
) -> list[LeadResult]:
    """Retorna leads paginados com base no FilterRequest."""
    stmt = _build_query(req).offset(req.offset).limit(req.limit)
    result = await session.execute(stmt)
    rows = result.fetchall()
    return [LeadResult.from_row(row) for row in rows]


async def stream_leads(session: AsyncSession, req: FilterRequest):
    """Gerador assíncrono para exportação em streaming sem limit/offset."""
    # Remove paginação para export completo
    export_req = req.model_copy(update={"limit": 0, "offset": 0})
    stmt = _build_query(export_req)
    result = await session.stream(stmt)
    async for row in result:
        yield LeadResult.from_row(row)
