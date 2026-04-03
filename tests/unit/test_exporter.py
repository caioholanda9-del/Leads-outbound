"""Testes unitários do exportador CSV/Excel."""
import asyncio
from datetime import date

import pytest

from leads.filtering.exporter import EXPORT_HEADERS, _lead_to_row
from leads.filtering.schemas import LeadResult


def _make_lead(**kwargs) -> LeadResult:
    defaults = dict(
        cnpj="12345678000100",
        razao_social="EMPRESA TI LTDA",
        nome_fantasia="TI LTDA",
        porte=3,
        situacao_cadastral=2,
        data_abertura=date(2020, 1, 15),
        cnae_principal="6201500",
        cnae_secundario=None,
        uf="SP",
        municipio=3550308,
        logradouro="Rua das Flores",
        numero="100",
        complemento=None,
        bairro="Centro",
        cep="01001001",
        telefone="(11) 999999999",
        telefone2=None,
        email="contato@ti.com.br",
    )
    defaults.update(kwargs)
    return LeadResult(**defaults)


def test_lead_to_row_complete():
    lead = _make_lead()
    row = _lead_to_row(lead)
    assert len(row) == len(EXPORT_HEADERS)
    assert row[0] == "12345678000100"
    assert row[1] == "EMPRESA TI LTDA"
    assert row[3] == "ME"  # porte 3 = ME
    assert row[4] == "Ativa"  # situacao 2 = Ativa


def test_lead_to_row_none_fields():
    lead = _make_lead(nome_fantasia=None, email=None, telefone=None)
    row = _lead_to_row(lead)
    assert row[2] == ""  # nome_fantasia
    assert row[16] == ""  # telefone
    assert row[17] == ""  # email


def test_export_csv_produces_header():
    async def run():
        lead = _make_lead()

        async def gen():
            yield lead

        chunks = []
        from leads.filtering.exporter import export_csv
        async for chunk in export_csv(gen()):
            chunks.append(chunk.decode("utf-8-sig"))

        content = "".join(chunks)
        assert "CNPJ" in content
        assert "Razão Social" in content
        assert "12345678000100" in content

    asyncio.run(run())
