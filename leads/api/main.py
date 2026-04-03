import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from leads.api.routers import health, ingestion, leads
from leads.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)

app = FastAPI(
    title="Leads Outbound — Filtragem CNPJ/CNAE",
    description=(
        "API para filtrar empresas brasileiras por atividade econômica (CNAE) "
        "usando os dados públicos da Receita Federal. Voltada para estratégia de "
        "prospecção outbound."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(leads.router)
app.include_router(ingestion.router)


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Leads Outbound API. Acesse /docs para documentação interativa."}
