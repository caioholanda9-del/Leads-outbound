"""Comando CLI para exportação de leads filtrados."""
import asyncio
import csv
import logging
from datetime import date
from pathlib import Path
from typing import Optional

import typer

from leads.filtering.schemas import FilterRequest

app = typer.Typer(help="Exporta leads filtrados para CSV ou Excel.")
logger = logging.getLogger(__name__)


def _run_export(req: FilterRequest, output: Path, fmt: str) -> None:
    """Executa a exportação de forma síncrona via asyncio.run."""
    import asyncio

    asyncio.run(_async_export(req, output, fmt))


async def _async_export(req: FilterRequest, output: Path, fmt: str) -> None:
    from leads.db.engine import AsyncSessionLocal
    from leads.db.repository import stream_leads
    from leads.filtering.exporter import export_csv, export_excel

    async with AsyncSessionLocal() as session:
        leads_gen = stream_leads(session, req)

        if fmt == "xlsx":
            data = await export_excel(leads_gen)
            output.write_bytes(data)
            typer.echo(f"Excel exportado: {output} ({len(data):,} bytes)")
        else:
            count = 0
            async for chunk in export_csv(leads_gen):
                output.open("ab").write(chunk)
                count += 1
            typer.echo(f"CSV exportado: {output} ({count} linhas)")


@app.command()
def export(
    cnae: list[str] = typer.Option(
        ..., "--cnae", "-c", help="Código CNAE principal (pode repetir para múltiplos)"
    ),
    uf: Optional[list[str]] = typer.Option(None, "--uf", "-u", help="UF (pode repetir)"),
    porte: Optional[list[int]] = typer.Option(
        None, "--porte", help="Porte: 1=MEI 3=ME 5=EPP 7=Demais (pode repetir)"
    ),
    situacao: int = typer.Option(2, "--situacao", "-s", help="Situação cadastral (2=Ativa)"),
    data_de: Optional[date] = typer.Option(None, "--data-de", help="Data abertura mínima YYYY-MM-DD"),
    data_ate: Optional[date] = typer.Option(None, "--data-ate", help="Data abertura máxima YYYY-MM-DD"),
    apenas_email: bool = typer.Option(False, "--apenas-email", help="Somente com e-mail"),
    apenas_telefone: bool = typer.Option(False, "--apenas-telefone", help="Somente com telefone"),
    incluir_secundario: bool = typer.Option(
        False, "--incluir-secundario", help="Incluir CNAE secundário na busca"
    ),
    output: Path = typer.Option(
        Path("leads_export.csv"), "--output", "-o", help="Arquivo de saída (.csv ou .xlsx)"
    ),
    limit: int = typer.Option(
        0, "--limit", "-l", help="Limitar número de resultados (0 = sem limite)"
    ),
):
    """
    Exporta leads filtrados para CSV ou Excel.

    Exemplos:

    \b
    leads export --cnae 6201500 --uf SP --output leads_ti_sp.xlsx
    leads export --cnae 6201500 --cnae 6202300 --porte 3 --apenas-email -o leads.csv
    """
    fmt = output.suffix.lstrip(".").lower()
    if fmt not in ("csv", "xlsx"):
        typer.echo("Formato não suportado. Use .csv ou .xlsx", err=True)
        raise typer.Exit(code=1)

    req = FilterRequest(
        cnaes_principal=cnae,
        incluir_cnae_secundario=incluir_secundario,
        ufs=uf or None,
        portes=porte or None,
        situacao_cadastral=situacao,
        data_abertura_de=data_de,
        data_abertura_ate=data_ate,
        apenas_com_email=apenas_email,
        apenas_com_telefone=apenas_telefone,
        limit=limit if limit > 0 else 100_000,
        offset=0,
    )

    typer.echo(f"Filtrando CNAEs {cnae} → {output}")
    _run_export(req, output, fmt)
