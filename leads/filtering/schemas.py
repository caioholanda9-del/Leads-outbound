from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator


class FilterRequest(BaseModel):
    """Parâmetros de filtragem de leads por CNPJ/CNAE."""

    # Obrigatório: pelo menos 1 CNAE principal
    cnaes_principal: list[str] = Field(
        ...,
        min_length=1,
        description="Lista de códigos CNAE principais (ex: ['6201500', '6202300'])",
    )
    incluir_cnae_secundario: bool = Field(
        False,
        description="Se True, inclui empresas com os CNAEs nos ramos secundários",
    )

    # Localização
    ufs: list[str] | None = Field(None, description="Filtrar por UF (ex: ['SP', 'RJ'])")
    municipios: list[int] | None = Field(
        None, description="Filtrar por código de município da RF"
    )

    # Empresa
    portes: list[int] | None = Field(
        None, description="Porte: 1=MEI, 3=ME, 5=EPP, 7=Demais"
    )
    situacao_cadastral: int = Field(
        2, description="Situação: 2=Ativa (padrão), 3=Suspensa, 4=Inapta, 8=Baixada"
    )
    data_abertura_de: date | None = Field(None, description="Data de abertura mínima")
    data_abertura_ate: date | None = Field(None, description="Data de abertura máxima")

    # Contato
    apenas_com_email: bool = Field(False, description="Somente empresas com e-mail cadastrado")
    apenas_com_telefone: bool = Field(
        False, description="Somente empresas com telefone cadastrado"
    )

    # Paginação
    limit: int = Field(1000, ge=1, le=10000, description="Máximo de resultados por página")
    offset: int = Field(0, ge=0, description="Offset para paginação")

    @model_validator(mode="after")
    def validate_dates(self) -> "FilterRequest":
        if (
            self.data_abertura_de
            and self.data_abertura_ate
            and self.data_abertura_de > self.data_abertura_ate
        ):
            raise ValueError("data_abertura_de não pode ser posterior a data_abertura_ate")
        return self


class LeadResult(BaseModel):
    """Um lead resultante da filtragem."""

    cnpj: str | None
    razao_social: str | None
    nome_fantasia: str | None
    porte: int | None
    situacao_cadastral: int | None
    data_abertura: date | None
    cnae_principal: str | None
    cnae_secundario: str | None
    uf: str | None
    municipio: int | None
    logradouro: str | None
    numero: str | None
    complemento: str | None
    bairro: str | None
    cep: str | None
    telefone: str | None  # ddd1 + telefone1 concatenados
    telefone2: str | None
    email: str | None

    @classmethod
    def from_row(cls, row: Any) -> "LeadResult":
        # Constrói telefone como DDD+número
        tel1 = None
        if row.ddd1 and row.telefone1:
            tel1 = f"({row.ddd1}) {row.telefone1}"
        elif row.telefone1:
            tel1 = row.telefone1

        tel2 = None
        if row.ddd2 and row.telefone2:
            tel2 = f"({row.ddd2}) {row.telefone2}"

        return cls(
            cnpj=row.cnpj_completo,
            razao_social=row.razao_social,
            nome_fantasia=row.nome_fantasia,
            porte=row.porte_empresa,
            situacao_cadastral=row.situacao_cadastral,
            data_abertura=row.data_inicio_atividade,
            cnae_principal=row.cnae_fiscal_principal,
            cnae_secundario=row.cnae_fiscal_secundaria,
            uf=row.uf,
            municipio=row.municipio,
            logradouro=row.logradouro,
            numero=row.numero,
            complemento=row.complemento,
            bairro=row.bairro,
            cep=row.cep,
            telefone=tel1,
            telefone2=tel2,
            email=row.correio_eletronico,
        )


class FilterResponse(BaseModel):
    """Resposta paginada da filtragem."""

    total: int
    limit: int
    offset: int
    results: list[LeadResult]


class CnaeItem(BaseModel):
    codigo: str
    descricao: str


class MunicipioItem(BaseModel):
    codigo: int
    descricao: str
