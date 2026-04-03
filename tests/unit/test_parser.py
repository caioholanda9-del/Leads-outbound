"""Testes unitários do parser de CSV da Receita Federal."""
import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from leads.ingestion.parser import _normalize_file_type, _parse_date, COLUMNS


def test_normalize_file_type_empresa():
    assert _normalize_file_type(Path("Empresa0.zip")) == "empresa"


def test_normalize_file_type_estabelecimento():
    assert _normalize_file_type(Path("Estabelecimento3.zip")) == "estabelecimento"


def test_normalize_file_type_cnae():
    assert _normalize_file_type(Path("Cnae.zip")) == "cnae"


def test_normalize_file_type_municipio():
    assert _normalize_file_type(Path("Municipios.zip")) == "municipio"


def test_normalize_file_type_unknown():
    with pytest.raises(ValueError, match="Tipo de arquivo desconhecido"):
        _normalize_file_type(Path("Unknown.zip"))


def test_parse_date_valid():
    series = pd.Series(["20200115", "20151231"])
    result = _parse_date(series)
    assert result.iloc[0].year == 2020
    assert result.iloc[0].month == 1
    assert result.iloc[0].day == 15


def test_parse_date_empty():
    series = pd.Series(["", "0", "00000000"])
    result = _parse_date(series)
    assert result.isna().all()


def _make_zip(csv_content: str, filename: str = "data.csv") -> Path:
    """Helper: cria um ZIP em memória com um CSV."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, csv_content.encode("latin-1"))
    buf.seek(0)
    return buf


def test_iter_chunks_cnae(tmp_path):
    from leads.ingestion.parser import iter_chunks

    csv_content = "6201500;Desenvolvimento de programas de computador\n"
    zip_path = tmp_path / "Cnae.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Cnae.csv", csv_content.encode("latin-1"))
    zip_path.write_bytes(buf.getvalue())

    chunks = list(iter_chunks(zip_path, "cnae"))
    assert len(chunks) == 1
    df = chunks[0]
    assert "codigo" in df.columns
    assert "descricao" in df.columns
    assert df.iloc[0]["codigo"] == "6201500"


def test_columns_have_expected_keys():
    for key in ("empresa", "estabelecimento", "cnae", "municipio"):
        assert key in COLUMNS
        assert len(COLUMNS[key]) > 0
