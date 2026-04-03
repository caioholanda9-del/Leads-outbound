"""Fixtures compartilhadas entre todos os testes."""
import asyncio
from datetime import date
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from leads.db.models import Base, Cnae, Empresa, Estabelecimento, Municipio, NaturezaJuridica
from leads.filtering.schemas import FilterRequest

# Banco em memória para testes (SQLite não suporta GENERATED ALWAYS, então usamos
# um esquema simplificado de fixtures diretas)
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        # SQLite não suporta GENERATED ALWAYS — criamos tabelas sem a coluna computada
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def sample_data(db_session: AsyncSession):
    """Popula o banco com dados de amostra."""
    db_session.add_all([
        NaturezaJuridica(codigo="2062", descricao="Sociedade Empresária Limitada"),
        Cnae(codigo="6201500", descricao="Desenvolvimento de programas de computador sob encomenda"),
        Cnae(codigo="6202300", descricao="Desenvolvimento e licenciamento de programas de computador"),
        Cnae(codigo="4711301", descricao="Comércio varejista de mercadorias em geral"),
        Municipio(codigo=3550308, descricao="São Paulo"),
        Municipio(codigo=3304557, descricao="Rio de Janeiro"),
    ])
    await db_session.flush()

    db_session.add_all([
        Empresa(
            cnpj_basico="12345678",
            razao_social="EMPRESA TI LTDA",
            natureza_juridica="2062",
            porte_empresa=3,
            capital_social=50000,
        ),
        Empresa(
            cnpj_basico="87654321",
            razao_social="LOJA VAREJO SA",
            natureza_juridica="2062",
            porte_empresa=5,
            capital_social=200000,
        ),
        Empresa(
            cnpj_basico="11111111",
            razao_social="SOFTWARE MEI",
            natureza_juridica="2062",
            porte_empresa=1,
            capital_social=5000,
        ),
    ])
    await db_session.flush()

    db_session.add_all([
        Estabelecimento(
            cnpj_basico="12345678",
            cnpj_ordem="0001",
            cnpj_dv="00",
            situacao_cadastral=2,
            data_inicio_atividade=date(2020, 1, 15),
            cnae_fiscal_principal="6201500",
            uf="SP",
            municipio=3550308,
            ddd1="11",
            telefone1="999999999",
            correio_eletronico="contato@empresa-ti.com.br",
        ),
        Estabelecimento(
            cnpj_basico="87654321",
            cnpj_ordem="0001",
            cnpj_dv="00",
            situacao_cadastral=2,
            data_inicio_atividade=date(2015, 6, 1),
            cnae_fiscal_principal="4711301",
            uf="RJ",
            municipio=3304557,
            ddd1="21",
            telefone1="888888888",
            correio_eletronico=None,
        ),
        Estabelecimento(
            cnpj_basico="11111111",
            cnpj_ordem="0001",
            cnpj_dv="00",
            situacao_cadastral=8,  # Baixada
            data_inicio_atividade=date(2022, 3, 10),
            cnae_fiscal_principal="6201500",
            uf="SP",
            municipio=3550308,
        ),
    ])
    await db_session.commit()
    return db_session


@pytest.fixture
def base_filter_request() -> FilterRequest:
    return FilterRequest(cnaes_principal=["6201500"])
