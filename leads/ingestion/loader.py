"""
Carga em massa no PostgreSQL via COPY (psycopg3).
Significativamente mais rápido que INSERT em lote.
"""
import io
import logging
from pathlib import Path
from typing import Iterator

import pandas as pd
import psycopg

from leads.config import settings

logger = logging.getLogger(__name__)


def _sync_db_url(url: str) -> str:
    """Converte a URL SQLAlchemy para formato psycopg nativo."""
    return (
        url.replace("postgresql+psycopg://", "postgresql://")
        .replace("postgresql+asyncpg://", "postgresql://")
    )


def bulk_copy(
    df: pd.DataFrame,
    table: str,
    columns: list[str],
    db_url: str | None = None,
    conflict_action: str = "DO NOTHING",
) -> int:
    """
    Carrega um DataFrame no PostgreSQL usando COPY + INSERT ... ON CONFLICT.

    Args:
        df: DataFrame com os dados.
        table: Nome da tabela destino.
        columns: Lista de colunas na ordem do DataFrame.
        db_url: URL de conexão. Padrão: settings.database_url.
        conflict_action: Ação em conflito de PK (DO NOTHING ou DO UPDATE ...).

    Returns:
        Número de linhas carregadas.
    """
    db_url = db_url or settings.database_url
    native_url = _sync_db_url(db_url)

    # Filtra apenas colunas existentes
    df_cols = [c for c in columns if c in df.columns]
    df_subset = df[df_cols].copy()

    # Converte NaN para None (NULL)
    df_subset = df_subset.where(pd.notna(df_subset), None)

    # Serializa para CSV em memória
    buf = io.StringIO()
    df_subset.to_csv(buf, index=False, header=False, na_rep="\\N")
    buf.seek(0)

    cols_str = ", ".join(f'"{c}"' for c in df_cols)
    staging = f"_stage_{table}"

    with psycopg.connect(native_url) as conn:
        with conn.cursor() as cur:
            # Cria tabela temporária com mesma estrutura
            cur.execute(
                f"""
                CREATE TEMP TABLE {staging} (LIKE {table} INCLUDING DEFAULTS)
                ON COMMIT DROP
                """
            )
            # COPY para staging
            with cur.copy(f"COPY {staging} ({cols_str}) FROM STDIN CSV NULL '\\N'") as copy:
                copy.write(buf.read())

            # Upsert para tabela principal
            cur.execute(
                f"""
                INSERT INTO {table} ({cols_str})
                SELECT {cols_str} FROM {staging}
                ON CONFLICT {conflict_action}
                """
            )
            count = cur.rowcount
        conn.commit()

    logger.info(f"Carregadas {count} linhas em '{table}'")
    return count


def load_lookup_table(
    df: pd.DataFrame,
    table: str,
    db_url: str | None = None,
) -> int:
    """Carrega tabela de lookup (cnae, municipio, natureza_juridica)."""
    return bulk_copy(df, table, list(df.columns), db_url)


def load_empresa_chunks(
    chunks: Iterator[pd.DataFrame],
    db_url: str | None = None,
) -> int:
    """Carrega todos os chunks de Empresa."""
    columns = [
        "cnpj_basico",
        "razao_social",
        "natureza_juridica",
        "qualificacao_responsavel",
        "capital_social",
        "porte_empresa",
        "ente_federativo",
    ]
    total = 0
    for chunk in chunks:
        total += bulk_copy(chunk, "empresa", columns, db_url)
    return total


def load_estabelecimento_chunks(
    chunks: Iterator[pd.DataFrame],
    db_url: str | None = None,
) -> int:
    """Carrega todos os chunks de Estabelecimento."""
    columns = [
        "cnpj_basico",
        "cnpj_ordem",
        "cnpj_dv",
        "matriz_filial",
        "nome_fantasia",
        "situacao_cadastral",
        "data_situacao_cadastral",
        "data_inicio_atividade",
        "cnae_fiscal_principal",
        "cnae_fiscal_secundaria",
        "tipo_logradouro",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cep",
        "uf",
        "municipio",
        "ddd1",
        "telefone1",
        "ddd2",
        "telefone2",
        "ddd_fax",
        "fax",
        "correio_eletronico",
        "situacao_especial",
        "data_situacao_especial",
    ]
    # Mapeamento entre colunas do CSV e colunas do banco
    RENAME = {"identificador_matriz_filial": "matriz_filial"}
    total = 0
    for chunk in chunks:
        chunk = chunk.rename(columns=RENAME)
        total += bulk_copy(chunk, "estabelecimento", columns, db_url)
    return total
