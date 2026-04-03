"""Testes unitários dos schemas de filtragem."""
from datetime import date

import pytest
from pydantic import ValidationError

from leads.filtering.schemas import FilterRequest


def test_filter_request_requires_cnae():
    with pytest.raises(ValidationError):
        FilterRequest(cnaes_principal=[])


def test_filter_request_valid():
    req = FilterRequest(cnaes_principal=["6201500"])
    assert req.situacao_cadastral == 2
    assert req.limit == 1000
    assert req.offset == 0
    assert not req.apenas_com_email


def test_filter_request_date_validation():
    with pytest.raises(ValidationError):
        FilterRequest(
            cnaes_principal=["6201500"],
            data_abertura_de=date(2024, 1, 1),
            data_abertura_ate=date(2020, 1, 1),
        )


def test_filter_request_multiple_cnaes():
    req = FilterRequest(cnaes_principal=["6201500", "6202300", "6209100"])
    assert len(req.cnaes_principal) == 3


def test_filter_request_all_filters():
    req = FilterRequest(
        cnaes_principal=["6201500"],
        ufs=["SP", "RJ"],
        portes=[3, 5],
        situacao_cadastral=2,
        data_abertura_de=date(2020, 1, 1),
        data_abertura_ate=date(2024, 12, 31),
        apenas_com_email=True,
        apenas_com_telefone=True,
        incluir_cnae_secundario=True,
        limit=500,
        offset=100,
    )
    assert req.ufs == ["SP", "RJ"]
    assert req.portes == [3, 5]
    assert req.apenas_com_email is True
