"""Excel-Export der Jahresabrechnung (Matrix: Kostenarten × Mieter) mit openpyxl."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .engine import compute_settlement
from .prorata import year_bounds

_CENTS = Decimal("0.01")

# Umlageschlüssel → Anzeige-Label (wie in der Abrechnungsansicht)
_ALLOC_LABELS = {
    "WF": "Wohnfläche",
    "NF": "Nutzfläche",
    "CONSUMPTION": "Verbrauch",
    "WOHNUNG": "Wohnung",
    "NONE": "—",
}

_TITLE_FONT = Font(bold=True, size=14)
_HEADER_FONT = Font(bold=True)
_HEADER_FILL = PatternFill("solid", fgColor="DEE2E6")
_SUM_FILL = PatternFill("solid", fgColor="E7F5FF")
_SALDO_FILL = PatternFill("solid", fgColor="FFF3BF")
_THIN = Side(style="thin", color="B0B0B0")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_CENTER = Alignment(horizontal="center")
_RIGHT = Alignment(horizontal="right")


def _fmt_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _money(value) -> float:
    """Wert als auf 2 Nachkommastellen gerundeter float (für Excel-Zellen)."""
    if value is None:
        return 0.0
    return float(Decimal(str(value)).quantize(_CENTS))


def generate_settlement_excel(session, property_id: int, year: int) -> bytes:
    """Erzeugt die xlsx-Matrix (Kostenarten × Mieter) für ein Objekt und Jahr."""
    result = compute_settlement(session, property_id, year)
    ys, ye = year_bounds(year)

    # Zeilen: alle konfigurierten Kostenstellen in Reihenfolge, danach zusätzliche
    # Detail-Codes (z. B. automatisch je Rechnungsart angelegte WOHNUNG-Kosten).
    rows: list[dict] = []  # {code, name, year_cost, basis}
    seen: set[str] = set()
    for cl in result.category_lines:
        rows.append(
            {
                "code": cl.code,
                "name": cl.name,
                "year_cost": cl.year_cost,
                "basis": _ALLOC_LABELS.get(cl.allocation_key, cl.allocation_key),
            }
        )
        seen.add(cl.code)
    for t in result.tenant_lines:
        for d in t.details:
            if d.code not in seen:
                rows.append(
                    {"code": d.code, "name": d.name, "year_cost": d.year_cost, "basis": d.basis_label}
                )
                seen.add(d.code)

    wb = Workbook()
    ws = wb.active
    ws.title = f"Abrechnung {year}"

    # Titelblock
    ws["A1"] = f"Nebenkostenabrechnung {year}"
    ws["A1"].font = _TITLE_FONT
    ws["A2"] = f"Objekt: {result.property_name}"
    ws["A3"] = f"Zeitraum: {_fmt_date(ys)} – {_fmt_date(ye)}"
    ws["A4"] = (
        f"Gesamtwohnfläche: {_money(result.total_wf):,.2f} m²  ·  "
        f"Gesamtnutzfläche: {_money(result.total_nf):,.2f} m²"
    )

    n_tenants = len(result.tenant_lines)
    header_row = 6
    first_data_row = header_row + 1

    # Kopfzeile: Kostenart | Verteilung | Gesamtkosten (€) | Mieter …
    headers = ["Kostenart", "Verteilung", "Gesamtkosten (€)"]
    for t in result.tenant_lines:
        headers.append(t.name if not t.designation else f"{t.name} · {t.designation}")
    for col, text in enumerate(headers, start=1):
        cell = ws.cell(header_row, col, text)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.border = _BORDER
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    # Datenzeilen
    for r, row in enumerate(rows):
        excel_row = first_data_row + r
        name_cell = ws.cell(excel_row, 1, row["name"])
        name_cell.border = _BORDER
        ws.cell(excel_row, 2, row["basis"]).border = _BORDER
        cost = ws.cell(excel_row, 3, _money(row["year_cost"]))
        cost.number_format = "#,##0.00"
        cost.border = _BORDER
        cost.alignment = _RIGHT
        for i, t in enumerate(result.tenant_lines):
            amount = sum((d.amount for d in t.details if d.code == row["code"]), Decimal("0"))
            cell = ws.cell(excel_row, 4 + i, _money(amount))
            cell.number_format = "#,##0.00"
            cell.border = _BORDER
            cell.alignment = _RIGHT

    last_data_row = first_data_row + len(rows) - 1 if rows else first_data_row - 1

    # Summenzeilen: Summe Kosten, Vorauszahlung, Saldo
    def _write_summary_row(excel_row: int, label: str, values: list[Decimal], fill, bold: bool):
        cell = ws.cell(excel_row, 1, label)
        cell.font = _HEADER_FONT
        cell.fill = fill
        cell.border = _BORDER
        for i, v in enumerate(values):
            c = ws.cell(excel_row, 4 + i, _money(v))
            c.number_format = "#,##0.00"
            c.font = _HEADER_FONT if bold else None
            c.fill = fill
            c.border = _BORDER
            c.alignment = _RIGHT

    total_row = last_data_row + 1
    sum_costs = sum((row["year_cost"] for row in rows), Decimal("0"))
    ws.cell(total_row, 3, _money(sum_costs)).number_format = "#,##0.00"
    ws.cell(total_row, 3).fill = _SUM_FILL
    ws.cell(total_row, 3).border = _BORDER
    _write_summary_row(
        total_row,
        "Summe Kosten",
        [t.total_costs for t in result.tenant_lines],
        _SUM_FILL,
        True,
    )
    _write_summary_row(
        total_row + 1,
        "Vorauszahlung",
        [t.advance_total for t in result.tenant_lines],
        PatternFill(),
        False,
    )
    _write_summary_row(
        total_row + 2,
        "Saldo (Nachzahlung/Guthaben)",
        [t.saldo for t in result.tenant_lines],
        _SALDO_FILL,
        True,
    )

    # Spaltenbreiten
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 16
    for i in range(n_tenants):
        ws.column_dimensions[get_column_letter(4 + i)].width = 18

    # Kopfzeile + erste 3 Spalten fixieren, Filter aktivieren
    ws.freeze_panes = "D7"
    if last_data_row >= first_data_row:
        ws.auto_filter.ref = f"A{header_row}:{get_column_letter(3 + n_tenants)}{last_data_row}"

    # Hinweise als eigenes Blatt
    if result.warnings:
        ww = wb.create_sheet("Hinweise")
        ww["A1"] = "Hinweise zur Abrechnung"
        ww["A1"].font = _HEADER_FONT
        for i, w in enumerate(result.warnings):
            ww.cell(2 + i, 1, w)
        ww.column_dimensions["A"].width = 100

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
