"""
Orquestrador do pipeline de ingestão:
  download → parse → load → (re)índices
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from leads.config import settings
from leads.ingestion import downloader, loader, parser

logger = logging.getLogger(__name__)


@dataclass
class PipelineStatus:
    stage: str = "idle"
    current_file: str = ""
    files_done: int = 0
    files_total: int = 0
    rows_loaded: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def done(self) -> bool:
        return self.stage in ("completed", "failed")

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "current_file": self.current_file,
            "files_done": self.files_done,
            "files_total": self.files_total,
            "rows_loaded": self.rows_loaded,
            "errors": self.errors,
        }


# Status global (simples para uso com FastAPI background tasks)
_status = PipelineStatus()


def get_status() -> PipelineStatus:
    return _status


def run_full_pipeline(
    period: str | None = None,
    skip_download: bool = False,
    data_dir: Path | None = None,
    db_url: str | None = None,
    on_progress: Callable[[PipelineStatus], None] | None = None,
) -> PipelineStatus:
    """
    Executa o pipeline completo de ingestão.

    Args:
        period: Período RF no formato 'YYYY-MM'. Detecta automaticamente se None.
        skip_download: Se True, usa arquivos já existentes em data_dir/raw/.
        data_dir: Diretório base. Padrão: settings.data_dir.
        db_url: URL do banco. Padrão: settings.database_url.
        on_progress: Callback chamado a cada atualização de status.
    """
    global _status
    _status = PipelineStatus()
    data_dir = data_dir or settings.data_dir
    raw_dir = data_dir / "raw"

    def _update(stage: str, **kwargs):
        _status.stage = stage
        for k, v in kwargs.items():
            setattr(_status, k, v)
        if on_progress:
            on_progress(_status)

    try:
        # ── 1. Download ──────────────────────────────────────────────────────
        if not skip_download:
            _update("downloading")
            zip_files = downloader.download_rf_files(period=period, data_dir=data_dir)
        else:
            zip_files = sorted(raw_dir.glob("*.zip"))
            logger.info(f"Usando {len(zip_files)} ZIPs já existentes em {raw_dir}")

        _status.files_total = len(zip_files)

        # ── 2. Lookups (Cnae, Municipios, Natureza) ──────────────────────────
        _update("loading_lookups")
        for zip_path in zip_files:
            name = zip_path.stem.lower()
            if name.startswith("cnae"):
                df = parser.read_lookup(zip_path, "cnae")
                loader.load_lookup_table(df, "cnae", db_url)
                _status.rows_loaded += len(df)
            elif name.startswith("municipio"):
                df = parser.read_lookup(zip_path, "municipio")
                loader.load_lookup_table(df, "municipio", db_url)
                _status.rows_loaded += len(df)
            elif name.startswith("natureza"):
                df = parser.read_lookup(zip_path, "natureza")
                loader.load_lookup_table(df, "natureza_juridica", db_url)
                _status.rows_loaded += len(df)

        # ── 3. Empresa ───────────────────────────────────────────────────────
        _update("loading_empresa")
        empresa_zips = [z for z in zip_files if z.stem.lower().startswith("empresa")]
        for zip_path in empresa_zips:
            _update("loading_empresa", current_file=zip_path.name)
            chunks = parser.iter_chunks(zip_path, "empresa")
            n = loader.load_empresa_chunks(chunks, db_url)
            _status.rows_loaded += n
            _status.files_done += 1
            logger.info(f"Empresa: {zip_path.name} → {n} linhas")

        # ── 4. Estabelecimento ───────────────────────────────────────────────
        _update("loading_estabelecimento")
        estab_zips = [z for z in zip_files if z.stem.lower().startswith("estabelecimento")]
        for zip_path in estab_zips:
            _update("loading_estabelecimento", current_file=zip_path.name)
            chunks = parser.iter_chunks(zip_path, "estabelecimento")
            n = loader.load_estabelecimento_chunks(chunks, db_url)
            _status.rows_loaded += n
            _status.files_done += 1
            logger.info(f"Estabelecimento: {zip_path.name} → {n} linhas")

        _update("completed")
        logger.info(f"Pipeline concluído. Total: {_status.rows_loaded} linhas carregadas.")

    except Exception as e:
        logger.exception(f"Erro no pipeline: {e}")
        _status.stage = "failed"
        _status.errors.append(str(e))

    return _status
