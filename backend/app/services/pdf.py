"""PDF-Generierung (Mieter-Abrechnung) mit ReportLab."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

from .. import models
from .engine import TenantLine, compute_settlement
from .prorata import year_bounds


def _g(value: Optional[Decimal] | int | float | None, digits: int = 2) -> str:
    """Deutsche Zahlformatierung (1.234,56)."""
    if value is None:
        return "—"
    s = f"{float(value):,.{digits}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _tenant_table_rows(line: TenantLine) -> list[list[str]]:
    """Zeilen der Mieter-Tabelle – entspricht exakt der Tabellen-Ansicht (line.details).

    Jede Kostenstelle erscheint als eigene Zeile (auch die einzelnen
    Verbrauchs-Kostenstellen wie Trink-/Schmutzwasser statt einer
    aggregierten "Wasserverbrauch"-Zeile).
    """
    def _unit(amount: Optional[Decimal], decimals: int = 2, suffix: str = "") -> str:
        if amount is None:
            return "—"
        return f"{_g(amount, decimals)} {suffix}".strip()

    rows: list[list[str]] = []
    for d in line.details:
        if d.allocation_key == "NONE":
            continue
        if d.allocation_key == "CONSUMPTION":
            total_units = _unit(d.basis_total, 2, "m³")
            share = _unit(d.basis_share, 2, "m³")
        elif d.allocation_key in ("WF", "NF"):
            total_units = _unit(d.basis_total, 2, "m²")
            share = _unit(d.basis_share, 2, "m²")
        else:  # WOHNUNG – keine Verteil-Basis
            total_units = "—"
            share = "—"
        rows.append(
            [
                d.name,
                _g(d.year_cost),
                d.basis_label,
                total_units,
                share,
                str(line.tenant_days),
                _g(d.amount),
            ]
        )
    return rows


def generate_tenant_pdf(session, property_id: int, year: int, tenant_id: int) -> bytes:
    """Erzeugt das Mieter-PDF für die Jahresabrechnung und liefert die Bytes."""
    result = compute_settlement(session, property_id, year)

    line = next((ln for ln in result.tenant_lines if ln.tenant_id == tenant_id), None)
    if line is None:
        raise ValueError("Mieter ist in dieser Abrechnung nicht enthalten")

    tenant = session.get(models.Tenant, tenant_id)
    if tenant is None:
        raise ValueError("Mieter nicht gefunden")

    ys, ye = year_bounds(year)
    occ_start = max(tenant.move_in, ys)
    occ_end = min(tenant.move_out, ye) if tenant.move_out else ye

    buffer = BytesIO()
    # Querformat (Tabelle ist breit); das PDF enthält nur die Tabelle.
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Nebenkostenabrechnung {year} – {tenant.name}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", parent=styles["Normal"], fontSize=12, leading=16, spaceAfter=8
    )
    story = [
        Paragraph(
            f"{tenant.name} – {result.property_name} – Abrechnung für den Zeitraum "
            f"{occ_start.strftime('%d.%m')} – {occ_end.strftime('%d.%m.%Y')}",
            title_style,
        )
    ]

    headers = [
        "Kostenart",
        "Gesamtkosten Haus",
        "Verteilerschlüssel",
        "Gesamt-Einheiten",
        "Anteil Mieter",
        "Tage",
        "Betrag Mieter",
    ]

    rows = _tenant_table_rows(line)

    rows.append(["Nebenkosten gesamt", "", "", "", "", "", _g(line.total_costs)])
    rows.append(["Vorauszahlungen", "", "", "", "", "", _g(line.advance_total)])
    if line.saldo >= 0:
        rows.append(["Nachzahlung", "", "", "", "", "", _g(line.saldo)])
    else:
        rows.append(["Gutschrift", "", "", "", "", "", _g(-line.saldo)])

    table_data = [headers, *rows]
    table = Table(table_data, colWidths=[66 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm, 24 * mm, 36 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9ecef")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("ALIGN", (3, 1), (5, -1), "RIGHT"),
                ("ALIGN", (6, 1), (6, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("FONTNAME", (0, -3), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -3), (-1, -1), colors.HexColor("#f8f9fa")),
            ]
        )
    )
    doc.build([*story, table])
    return buffer.getvalue()
