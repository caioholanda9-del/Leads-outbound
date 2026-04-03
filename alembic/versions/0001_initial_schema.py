"""Schema inicial: natureza_juridica, cnae, municipio, empresa, estabelecimento

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "natureza_juridica",
        sa.Column("codigo", sa.CHAR(4), primary_key=True),
        sa.Column("descricao", sa.String(200), nullable=False),
    )

    op.create_table(
        "cnae",
        sa.Column("codigo", sa.String(10), primary_key=True),
        sa.Column("descricao", sa.Text(), nullable=False),
    )

    op.create_table(
        "municipio",
        sa.Column("codigo", sa.BigInteger(), primary_key=True),
        sa.Column("descricao", sa.String(100), nullable=False),
    )

    op.create_table(
        "empresa",
        sa.Column("cnpj_basico", sa.CHAR(8), primary_key=True),
        sa.Column("razao_social", sa.String(200), nullable=False),
        sa.Column(
            "natureza_juridica",
            sa.CHAR(4),
            sa.ForeignKey("natureza_juridica.codigo"),
            nullable=True,
        ),
        sa.Column("qualificacao_responsavel", sa.SmallInteger(), nullable=True),
        sa.Column("capital_social", sa.Numeric(18, 2), nullable=True),
        sa.Column("porte_empresa", sa.SmallInteger(), nullable=True),
        sa.Column("ente_federativo", sa.String(50), nullable=True),
    )

    op.create_table(
        "estabelecimento",
        sa.Column("cnpj_basico", sa.CHAR(8), sa.ForeignKey("empresa.cnpj_basico"), nullable=False),
        sa.Column("cnpj_ordem", sa.CHAR(4), nullable=False),
        sa.Column("cnpj_dv", sa.CHAR(2), nullable=False),
        sa.Column(
            "cnpj_completo",
            sa.CHAR(14),
            sa.Computed("cnpj_basico || cnpj_ordem || cnpj_dv", persisted=True),
        ),
        sa.Column("matriz_filial", sa.SmallInteger(), nullable=True),
        sa.Column("nome_fantasia", sa.String(200), nullable=True),
        sa.Column("situacao_cadastral", sa.SmallInteger(), nullable=True),
        sa.Column("data_situacao_cadastral", sa.Date(), nullable=True),
        sa.Column("data_inicio_atividade", sa.Date(), nullable=True),
        sa.Column(
            "cnae_fiscal_principal",
            sa.String(10),
            sa.ForeignKey("cnae.codigo"),
            nullable=True,
        ),
        sa.Column("cnae_fiscal_secundaria", sa.Text(), nullable=True),
        sa.Column("tipo_logradouro", sa.String(20), nullable=True),
        sa.Column("logradouro", sa.String(200), nullable=True),
        sa.Column("numero", sa.String(10), nullable=True),
        sa.Column("complemento", sa.String(100), nullable=True),
        sa.Column("bairro", sa.String(100), nullable=True),
        sa.Column("cep", sa.CHAR(8), nullable=True),
        sa.Column("uf", sa.CHAR(2), nullable=True),
        sa.Column("municipio", sa.BigInteger(), sa.ForeignKey("municipio.codigo"), nullable=True),
        sa.Column("ddd1", sa.String(4), nullable=True),
        sa.Column("telefone1", sa.String(10), nullable=True),
        sa.Column("ddd2", sa.String(4), nullable=True),
        sa.Column("telefone2", sa.String(10), nullable=True),
        sa.Column("ddd_fax", sa.String(4), nullable=True),
        sa.Column("fax", sa.String(10), nullable=True),
        sa.Column("correio_eletronico", sa.String(150), nullable=True),
        sa.Column("situacao_especial", sa.String(100), nullable=True),
        sa.Column("data_situacao_especial", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("cnpj_basico", "cnpj_ordem", "cnpj_dv"),
    )

    # Índices de performance
    op.create_index("idx_estab_cnae_principal", "estabelecimento", ["cnae_fiscal_principal"])
    op.create_index("idx_estab_situacao", "estabelecimento", ["situacao_cadastral"])
    op.create_index("idx_estab_uf", "estabelecimento", ["uf"])
    op.create_index("idx_estab_municipio", "estabelecimento", ["municipio"])
    op.create_index("idx_estab_data_abertura", "estabelecimento", ["data_inicio_atividade"])
    op.create_index("idx_estab_cnpj_completo", "estabelecimento", ["cnpj_completo"])

    # Índice parcial para empresas ativas (caso de uso mais frequente)
    op.execute(
        """
        CREATE INDEX idx_estab_ativas_cnae_uf
        ON estabelecimento (cnae_fiscal_principal, uf)
        WHERE situacao_cadastral = 2
        """
    )

    # Índice GIN para busca em CNAE secundário
    op.execute(
        """
        CREATE INDEX idx_estab_cnae_secundaria_gin
        ON estabelecimento USING gin(to_tsvector('simple', coalesce(cnae_fiscal_secundaria, '')))
        """
    )


def downgrade() -> None:
    op.drop_table("estabelecimento")
    op.drop_table("empresa")
    op.drop_table("municipio")
    op.drop_table("cnae")
    op.drop_table("natureza_juridica")
