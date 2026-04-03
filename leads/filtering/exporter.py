"""Exportação de leads para CSV e Excel."""
import csv
import io
import logging
from typing import AsyncIterator

from leads.filtering.schemas import LeadResult

logger = logging.getLogger(__name__)

EXPORT_HEADERS = [
    "CNPJ",
    "Razão Social",
    "Nome Fantasia",
    "Porte",
    "Situação",
    "Data Abertura",
    "CNAE Principal",
    "CNAE Secundário",
    "UF",
    "Município",
    "Logradouro",
    "Número",
    "Complemento",
    "Bairro",
    "CEP",
    "Telefone",
    "Telefone 2",
    "E-mail",
]

PORTE_LABELS = {1: "MEI", 3: "ME", 5: "EPP", 7: "Demais", 0: "N/A"}
SITUACAO_LABELS = {2: "Ativa", 3: "Suspensa", 4: "Inapta", 8: "Baixada"}


def _lead_to_row(lead: LeadResult) -> list:
    return [
        lead.cnpj or "",
        lead.razao_social or "",
        lead.nome_fantasia or "",
        PORTE_LABELS.get(lead.porte, str(lead.porte) if lead.porte else ""),
        SITUACAO_LABELS.get(lead.situacao_cadastral, str(lead.situacao_cadastral) if lead.situacao_cadastral else ""),
        str(lead.data_abertura) if lead.data_abertura else "",
        lead.cnae_principal or "",
        lead.cnae_secundario or "",
        lead.uf or "",
        str(lead.municipio) if lead.municipio else "",
        lead.logradouro or "",
        lead.numero or "",
        lead.complemento or "",
        lead.bairro or "",
        lead.cep or "",
        lead.telefone or "",
        lead.telefone2 or "",
        lead.email or "",
    ]


async def export_csv(leads: AsyncIterator[LeadResult]) -> AsyncIterator[bytes]:
    """
    Gerador assíncrono que produz o CSV em chunks de linhas.
    Adequado para StreamingResponse do FastAPI.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXPORT_HEADERS)
    buf.seek(0)
    yield buf.read().encode("utf-8-sig")  # BOM para compatibilidade com Excel

    async for lead in leads:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(_lead_to_row(lead))
        buf.seek(0)
        yield buf.read().encode("utf-8-sig")


async def export_excel(leads: AsyncIterator[LeadResult]) -> bytes:
    """
    Exporta todos os leads para Excel em memória.
    AVISO: carrega todos os dados em RAM — use apenas para resultados paginados.
    Para exportações grandes, prefira CSV streaming.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Leads"

    # Cabeçalho com estilo
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(color="FFFFFF", bold=True)
    ws.append(EXPORT_HEADERS)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font

    # Dados
    async for lead in leads:
        ws.append(_lead_to_row(lead))

    # Ajusta largura das colunas
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
