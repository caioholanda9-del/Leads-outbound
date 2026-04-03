"""
Parse dos arquivos CSV da Receita Federal.

Os CSVs da RF têm:
- Encoding: latin-1 (iso-8859-1)
- Separador: ;
- Sem cabeçalho (colunas na ordem documentada)
- Valores de data no formato YYYYMMDD (8 dígitos) ou vazio
"""
import logging
import zipfile
from pathlib import Path
from typing import Iterator

import pandas as pd

logger = logging.getLogger(__name__)

RF_ENCODING = "latin-1"
RF_SEP = ";"
RF_CHUNK_SIZE = 100_000  # linhas por chunk

# Colunas por tipo de arquivo (ordem exata dos dados abertos da RF)
COLUMNS = {
    "empresa": [
        "cnpj_basico",
        "razao_social",
        "natureza_juridica",
        "qualificacao_responsavel",
        "capital_social",
        "porte_empresa",
        "ente_federativo",
    ],
    "estabelecimento": [
        "cnpj_basico",
        "cnpj_ordem",
        "cnpj_dv",
        "identificador_matriz_filial",
        "nome_fantasia",
        "situacao_cadastral",
        "data_situacao_cadastral",
        "motivo_situacao_cadastral",
        "nome_cidade_exterior",
        "pais",
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
    ],
    "cnae": ["codigo", "descricao"],
    "municipio": ["codigo", "descricao"],
    "natureza": ["codigo", "descricao"],
    "qualificacao": ["codigo", "descricao"],
}

DATE_COLUMNS = {
    "empresa": [],
    "estabelecimento": [
        "data_situacao_cadastral",
        "data_inicio_atividade",
        "data_situacao_especial",
    ],
}


def _normalize_file_type(zip_path: Path) -> str:
    """Detecta o tipo do arquivo pelo nome."""
    name = zip_path.stem.lower()
    for key in COLUMNS:
        if name.startswith(key):
            return key
    raise ValueError(f"Tipo de arquivo desconhecido: {zip_path.name}")


def _parse_date(series: pd.Series) -> pd.Series:
    """Converte datas no formato YYYYMMDD para datetime, tratando zeros e vazios."""
    return pd.to_datetime(
        series.replace("0", pd.NA).replace("00000000", pd.NA),
        format="%Y%m%d",
        errors="coerce",
    )


def iter_chunks(zip_path: Path, file_type: str | None = None) -> Iterator[pd.DataFrame]:
    """
    Lê um arquivo ZIP da RF e gera chunks de DataFrame.

    Args:
        zip_path: Caminho do arquivo .zip da RF.
        file_type: Tipo explícito ('empresa', 'estabelecimento', etc.).
                   Se None, detecta pelo nome do arquivo.

    Yields:
        DataFrame com as colunas padronizadas.
    """
    if file_type is None:
        file_type = _normalize_file_type(zip_path)

    columns = COLUMNS[file_type]
    date_cols = DATE_COLUMNS.get(file_type, [])

    with zipfile.ZipFile(zip_path) as zf:
        # O ZIP da RF normalmente contém um único CSV
        csv_names = [n for n in zf.namelist() if not n.startswith("__")]
        if not csv_names:
            raise ValueError(f"Nenhum CSV encontrado em {zip_path.name}")

        for csv_name in csv_names:
            logger.info(f"Parseando {zip_path.name}/{csv_name} como '{file_type}'")
            with zf.open(csv_name) as f:
                reader = pd.read_csv(
                    f,
                    sep=RF_SEP,
                    encoding=RF_ENCODING,
                    header=None,
                    names=columns,
                    dtype=str,
                    keep_default_na=False,
                    na_values=[""],
                    chunksize=RF_CHUNK_SIZE,
                    on_bad_lines="warn",
                )
                for chunk in reader:
                    # Normaliza datas
                    for col in date_cols:
                        if col in chunk.columns:
                            chunk[col] = _parse_date(chunk[col])

                    # Remove espaços extras em strings
                    str_cols = chunk.select_dtypes(include="object").columns
                    chunk[str_cols] = chunk[str_cols].apply(
                        lambda s: s.str.strip().replace("", pd.NA)
                    )

                    yield chunk


def read_lookup(zip_path: Path, file_type: str | None = None) -> pd.DataFrame:
    """Lê uma tabela de lookup completa (ex: CNAE, Municipio) em memória."""
    chunks = list(iter_chunks(zip_path, file_type))
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
