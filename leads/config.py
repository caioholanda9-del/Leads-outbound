from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://leads:leads@localhost:5432/leads"
    data_dir: Path = Path("./data")
    log_level: str = "INFO"
    rf_base_url: str = (
        "https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj"
    )

    @property
    def sync_database_url(self) -> str:
        """URL síncrona para uso no Alembic (sem +asyncpg)."""
        return self.database_url.replace("+asyncpg", "").replace(
            "postgresql+psycopg", "postgresql+psycopg"
        )


settings = Settings()
