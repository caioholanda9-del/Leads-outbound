# Leads Outbound — Filtragem de CNPJ por CNAE

Plataforma para filtrar empresas brasileiras (CNPJ) por atividade econômica (CNAE) usando os dados públicos da Receita Federal, voltada para estratégia de prospecção outbound.

## Início Rápido

### Pré-requisitos
- Docker + Docker Compose
- Python 3.12+ (para uso via CLI)

### Com Docker
```bash
cp .env.example .env
docker-compose up -d
# Aguardar DB subir, então rodar migração:
docker-compose exec app alembic upgrade head
```

### Com uv (desenvolvimento local)
```bash
pip install uv
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
# Ajuste DATABASE_URL no .env conforme seu PostgreSQL local
alembic upgrade head
```

## Ingestão dos Dados

Baixa e carrega os dados da Receita Federal (~40-80 GB descomprimido):

```bash
# Baixar e carregar tudo (demora horas na primeira vez)
leads ingest all

# Apenas carregar CSVs já baixados em data/
leads ingest load --skip-download
```

## Uso via CLI

```bash
# Filtrar empresas de TI (CNAE 6201500) em SP — exportar Excel
leads export --cnae 6201500 --uf SP --output leads_ti_sp.xlsx

# Múltiplos CNAEs, apenas com e-mail, somente MEI e ME
leads export --cnae 6201500 --cnae 6202300 --porte 1 --porte 3 --apenas-email --output leads.csv

# Ver todos os filtros disponíveis
leads export --help
```

## Uso via API

```bash
uvicorn leads.api.main:app --reload
```

Acesse `http://localhost:8000/docs` para a interface Swagger interativa.

### Exemplo de filtro
```bash
curl -X POST http://localhost:8000/leads/filter \
  -H "Content-Type: application/json" \
  -d '{
    "cnaes_principal": ["6201500", "6202300"],
    "ufs": ["SP", "RJ"],
    "portes": [3, 5],
    "apenas_com_email": true,
    "limit": 100
  }'
```

### Exportar CSV/Excel
```
GET /leads/export?cnaes_principal=6201500&uf=SP&format=xlsx
```

## Estrutura do Projeto

```
leads/
├── config.py          # Configurações via variáveis de ambiente
├── db/                # ORM SQLAlchemy, engine, repositório de queries
├── ingestion/         # Download, parse e carga dos dados da RF
├── filtering/         # Schemas de filtro, lógica de query, exportação
├── api/               # FastAPI — endpoints REST
└── cli/               # Typer — interface de linha de comando
```

## Filtros Disponíveis

| Filtro | Descrição | Exemplo |
|---|---|---|
| `cnaes_principal` | Códigos CNAE principais (obrigatório) | `["6201500"]` |
| `incluir_cnae_secundario` | Buscar também no CNAE secundário | `true` |
| `ufs` | Filtrar por estados | `["SP", "MG"]` |
| `municipios` | Filtrar por código de município RF | `[3550308]` |
| `portes` | Porte: 1=MEI, 3=ME, 5=EPP, 7=Demais | `[3, 5]` |
| `situacao_cadastral` | 2=Ativa (padrão), 3=Suspensa | `2` |
| `data_abertura_de` | Abertura a partir de (YYYY-MM-DD) | `"2020-01-01"` |
| `data_abertura_ate` | Abertura até (YYYY-MM-DD) | `"2024-12-31"` |
| `apenas_com_email` | Somente empresas com e-mail cadastrado | `true` |
| `apenas_com_telefone` | Somente empresas com telefone cadastrado | `true` |

## Fonte dos Dados

Dados Abertos da Receita Federal: https://dados.gov.br/dados/conjuntos-dados/cnpj

Atualização mensal. Encoding: latin-1. Separador: `;`.
