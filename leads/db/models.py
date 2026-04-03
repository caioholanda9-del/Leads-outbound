from sqlalchemy import (
    CHAR,
    BigInteger,
    Column,
    Computed,
    Date,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class NaturezaJuridica(Base):
    __tablename__ = "natureza_juridica"

    codigo = Column(CHAR(4), primary_key=True)
    descricao = Column(String(200), nullable=False)


class Cnae(Base):
    __tablename__ = "cnae"

    codigo = Column(String(10), primary_key=True)  # ex: '6201500'
    descricao = Column(Text, nullable=False)


class Municipio(Base):
    __tablename__ = "municipio"

    codigo = Column(BigInteger, primary_key=True)
    descricao = Column(String(100), nullable=False)


class Empresa(Base):
    __tablename__ = "empresa"

    cnpj_basico = Column(CHAR(8), primary_key=True)
    razao_social = Column(String(200), nullable=False)
    natureza_juridica = Column(CHAR(4), ForeignKey("natureza_juridica.codigo"))
    qualificacao_responsavel = Column(SmallInteger)
    capital_social = Column(Numeric(18, 2))
    # 1=MEI, 3=ME, 5=EPP, 7=Demais (médio/grande), 0=N/A
    porte_empresa = Column(SmallInteger)
    ente_federativo = Column(String(50))

    estabelecimentos = relationship("Estabelecimento", back_populates="empresa")


class Estabelecimento(Base):
    __tablename__ = "estabelecimento"

    cnpj_basico = Column(CHAR(8), ForeignKey("empresa.cnpj_basico"), primary_key=True)
    cnpj_ordem = Column(CHAR(4), primary_key=True)
    cnpj_dv = Column(CHAR(2), primary_key=True)
    # coluna computada para conveniência
    cnpj_completo = Column(
        CHAR(14),
        Computed("cnpj_basico || cnpj_ordem || cnpj_dv", persisted=True),
    )
    # 1=Matriz, 2=Filial
    matriz_filial = Column(SmallInteger)
    nome_fantasia = Column(String(200))
    # 2=Ativa, 3=Suspensa, 4=Inapta, 8=Baixada
    situacao_cadastral = Column(SmallInteger)
    data_situacao_cadastral = Column(Date)
    data_inicio_atividade = Column(Date)
    cnae_fiscal_principal = Column(String(10), ForeignKey("cnae.codigo"))
    # lista de CNAEs secundários separados por pipe: '6202300|6311900'
    cnae_fiscal_secundaria = Column(Text)
    tipo_logradouro = Column(String(20))
    logradouro = Column(String(200))
    numero = Column(String(10))
    complemento = Column(String(100))
    bairro = Column(String(100))
    cep = Column(CHAR(8))
    uf = Column(CHAR(2))
    municipio = Column(BigInteger, ForeignKey("municipio.codigo"))
    ddd1 = Column(String(4))
    telefone1 = Column(String(10))
    ddd2 = Column(String(4))
    telefone2 = Column(String(10))
    ddd_fax = Column(String(4))
    fax = Column(String(10))
    correio_eletronico = Column(String(150))
    situacao_especial = Column(String(100))
    data_situacao_especial = Column(Date)

    empresa = relationship("Empresa", back_populates="estabelecimentos")

    __table_args__ = (
        # índice composto para empresas ativas por CNAE + UF (caso de uso principal)
        Index(
            "idx_estab_ativas_cnae_uf",
            "cnae_fiscal_principal",
            "uf",
            postgresql_where=(situacao_cadastral == 2),
        ),
        Index("idx_estab_cnae_principal", "cnae_fiscal_principal"),
        Index("idx_estab_situacao", "situacao_cadastral"),
        Index("idx_estab_uf", "uf"),
        Index("idx_estab_municipio", "municipio"),
        Index("idx_estab_data_abertura", "data_inicio_atividade"),
        Index("idx_estab_cnpj_completo", "cnpj_completo"),
    )
