"""Download dos arquivos ZIP da Receita Federal com suporte a retomada (resume)."""
import logging
from pathlib import Path

import httpx
from tqdm import tqdm

from leads.config import settings

logger = logging.getLogger(__name__)

# Arquivos disponíveis no portal de dados abertos da RF
RF_FILES = [
    "Cnae.zip",
    "Municipios.zip",
    "Natureza.zip",
    "Qualificacoes.zip",
    "Simples.zip",
    # Empresa0-9 (10 arquivos)
    *[f"Empresa{i}.zip" for i in range(10)],
    # Estabelecimento0-9 (10 arquivos)
    *[f"Estabelecimento{i}.zip" for i in range(10)],
    # Socios0-9 (10 arquivos)
    *[f"Socios{i}.zip" for i in range(10)],
]

# Subconjunto mínimo para funcionar (lookup tables + dados principais)
RF_FILES_ESSENTIAL = [
    "Cnae.zip",
    "Municipios.zip",
    "Natureza.zip",
    *[f"Empresa{i}.zip" for i in range(10)],
    *[f"Estabelecimento{i}.zip" for i in range(10)],
]


def _get_latest_period(base_url: str) -> str:
    """Descobre o período mais recente disponível (ex: '2025-03')."""
    # A RF organiza por diretórios YYYY-MM — tentamos os últimos 3 meses
    from datetime import date, timedelta

    today = date.today()
    for delta in range(0, 90, 30):
        candidate = today - timedelta(days=delta)
        period = candidate.strftime("%Y-%m")
        url = f"{base_url}/{period}/Cnae.zip"
        try:
            with httpx.Client(timeout=10, follow_redirects=True) as client:
                resp = client.head(url)
                if resp.status_code == 200:
                    logger.info(f"Período RF mais recente encontrado: {period}")
                    return period
        except httpx.RequestError:
            continue
    raise RuntimeError("Não foi possível determinar o período mais recente da RF.")


def download_file(url: str, dest: Path, chunk_size: int = 1024 * 1024) -> Path:
    """
    Baixa um arquivo com suporte a retomada via Range header.
    Retorna o caminho do arquivo baixado.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    existing_size = dest.stat().st_size if dest.exists() else 0
    headers = {"Range": f"bytes={existing_size}-"} if existing_size > 0 else {}

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        with client.stream("GET", url, headers=headers) as resp:
            if resp.status_code == 416:
                # Arquivo já completo
                logger.info(f"Arquivo já completo: {dest.name}")
                return dest

            if resp.status_code not in (200, 206):
                resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0)) + existing_size
            mode = "ab" if existing_size > 0 else "wb"

            with (
                open(dest, mode) as f,
                tqdm(
                    total=total,
                    initial=existing_size,
                    unit="B",
                    unit_scale=True,
                    desc=dest.name,
                ) as bar,
            ):
                for chunk in resp.iter_bytes(chunk_size):
                    f.write(chunk)
                    bar.update(len(chunk))

    logger.info(f"Download concluído: {dest}")
    return dest


def download_rf_files(
    period: str | None = None,
    files: list[str] | None = None,
    data_dir: Path | None = None,
) -> list[Path]:
    """
    Baixa os arquivos ZIP da Receita Federal para `data_dir/raw/`.

    Args:
        period: Período no formato 'YYYY-MM'. Se None, detecta automaticamente.
        files: Lista de arquivos a baixar. Se None, usa RF_FILES_ESSENTIAL.
        data_dir: Diretório base de dados. Padrão: settings.data_dir.

    Returns:
        Lista de Paths dos arquivos baixados.
    """
    base_url = settings.rf_base_url
    data_dir = data_dir or settings.data_dir
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    if period is None:
        period = _get_latest_period(base_url)

    files = files or RF_FILES_ESSENTIAL
    downloaded = []

    for filename in files:
        url = f"{base_url}/{period}/{filename}"
        dest = raw_dir / filename
        logger.info(f"Baixando {url} → {dest}")
        try:
            path = download_file(url, dest)
            downloaded.append(path)
        except Exception as e:
            logger.error(f"Erro ao baixar {filename}: {e}")
            raise

    return downloaded
