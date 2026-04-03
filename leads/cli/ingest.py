import logging
from pathlib import Path
from typing import Optional

import typer

from leads.ingestion.pipeline import PipelineStatus, run_full_pipeline

app = typer.Typer(help="Comandos de ingestão dos dados da Receita Federal.")
logger = logging.getLogger(__name__)


def _progress_callback(status: PipelineStatus) -> None:
    typer.echo(
        f"[{status.stage}] {status.current_file or ''} "
        f"({status.files_done}/{status.files_total} arquivos, "
        f"{status.rows_loaded:,} linhas)"
    )


@app.command("all")
def ingest_all(
    period: Optional[str] = typer.Option(
        None,
        "--period",
        "-p",
        help="Período RF no formato YYYY-MM (ex: 2025-03). Detecta automaticamente se omitido.",
    ),
    data_dir: Optional[Path] = typer.Option(
        None,
        "--data-dir",
        "-d",
        help="Diretório base para downloads. Padrão: ./data",
    ),
    skip_download: bool = typer.Option(
        False,
        "--skip-download",
        help="Usa ZIPs já existentes em data-dir/raw/ sem baixar novamente.",
    ),
    db_url: Optional[str] = typer.Option(
        None,
        "--db-url",
        envvar="DATABASE_URL",
        help="URL de conexão com o PostgreSQL.",
    ),
):
    """Baixa e carrega todos os dados da Receita Federal no banco."""
    typer.echo("Iniciando pipeline de ingestão...")
    status = run_full_pipeline(
        period=period,
        skip_download=skip_download,
        data_dir=data_dir,
        db_url=db_url,
        on_progress=_progress_callback,
    )
    if status.stage == "completed":
        typer.echo(
            typer.style(
                f"✓ Concluído! {status.rows_loaded:,} linhas carregadas.",
                fg=typer.colors.GREEN,
                bold=True,
            )
        )
    else:
        typer.echo(
            typer.style(
                f"✗ Falha no stage '{status.stage}': {status.errors}",
                fg=typer.colors.RED,
                bold=True,
            )
        )
        raise typer.Exit(code=1)


@app.command("load")
def ingest_load(
    data_dir: Optional[Path] = typer.Option(None, "--data-dir", "-d"),
    db_url: Optional[str] = typer.Option(None, "--db-url", envvar="DATABASE_URL"),
):
    """Carrega ZIPs já existentes em data-dir/raw/ sem baixar novamente."""
    ingest_all(period=None, data_dir=data_dir, skip_download=True, db_url=db_url)
