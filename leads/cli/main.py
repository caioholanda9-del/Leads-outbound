import logging

import typer

from leads.cli import export as export_module
from leads.cli import ingest as ingest_module

app = typer.Typer(
    name="leads",
    help="Plataforma de filtragem de CNPJ por CNAE para prospecção outbound.",
    no_args_is_help=True,
)

app.add_typer(ingest_module.app, name="ingest")
app.add_typer(export_module.app, name="export", invoke_without_command=True)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Ativa log DEBUG"),
):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


if __name__ == "__main__":
    app()
