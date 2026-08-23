"""Orchestrierung der Jahresabrechnung: Flächenumlage + Wasser + Saldo."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..models.enums import InvoiceKind
from . import prorata
from .prorata import ZERO, days_in_year, pro_rata_amount, year_bounds
from .water import WaterResult, compute_water_consumption, unit_water_consumption

CENTS = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    """Rundet auf 2 Nachkommastellen (kaufmännisch)."""
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


@dataclass
class CategoryLine:
    code: str
    name: str
    allocation_key: str
    year_cost: Decimal


@dataclass
class CategoryShare:
    """Eine Kostenzeile in der Mieteransicht (Gesamt/Basis/Ihr Anteil/Betrag)."""

    code: str
    name: str
    allocation_key: str
    year_cost: Decimal  # Gesamtkosten der Kostenart
    basis_label: str  # z. B. "Wohnfläche", "Nutzfläche", "Verbrauch", "Wohnung"
    basis_total: Optional[Decimal]  # Gesamt-Basis (z. B. m² gesamt)
    basis_share: Optional[Decimal]  # Anteil des Mieters an der Basis
    days: int  # bewohnte Tage im Abrechnungsjahr
    amount: Decimal  # Kostenanteil des Mieters


@dataclass
class TenantLine:
    tenant_id: int
    name: str
    lease_unit_id: int
    designation: str
    living_area: Decimal
    utility_area: Decimal
    tenant_days: int
    time_factor: Decimal
    advance_months: Decimal
    # Für den Mieter relevanter Zeitraum im Abrechnungsjahr (bei Auszug/Wechsel anteilig)
    period_start: date
    period_end: date
    breakdown: dict[str, Decimal] = field(default_factory=dict)
    details: list[CategoryShare] = field(default_factory=list)
    # Vorauszahlungs-Zeiträume im Jahr (für Tooltip/Hover)
    advance_breakdown: list[dict] = field(default_factory=list)
    total_costs: Decimal = ZERO
    advance_total: Decimal = ZERO
    saldo: Decimal = ZERO


@dataclass
class SettlementResult:
    property_id: int
    property_name: str
    year: int
    days_in_year: int
    total_wf: Decimal
    total_nf: Decimal
    category_lines: list[CategoryLine] = field(default_factory=list)
    tenant_lines: list[TenantLine] = field(default_factory=list)
    water: Optional[WaterResult] = None
    water_total_cost: Decimal = ZERO
    water_price_per_m3: Optional[Decimal] = None
    garden_water_cost: Decimal = ZERO
    unallocated_water: Decimal = ZERO
    warnings: list[str] = field(default_factory=list)


def _months_between(start: date, end: date) -> Decimal:
    """Anzahl Kalendermonate zwischen start und end (inklusive).

    Volle Kalendermonate zählen als 1, Teilmonate anteilig (Tage im Monat).
    Z. B. 01.07.–31.12. = 6 Monate, 15.03.–30.06. = 3 + 17/31 Monate.
    """
    total = ZERO
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        m_start = date(y, m, 1)
        m_end = date(y, m, monthrange(y, m)[1])
        seg_start = max(start, m_start)
        seg_end = min(end, m_end)
        if seg_start <= seg_end:
            days_in_month = monthrange(y, m)[1]
            total += Decimal((seg_end - seg_start).days + 1) / Decimal(days_in_month)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return total


def _advance_total(
    tenant: models.Tenant, year: int, occ_start: date, occ_end: date
) -> Decimal:
    """Monatliche Vorauszahlung für das Abrechnungsjahr.

    Berechnung nach KALENDERMONATEN (nicht nach Tagen): ein voller Monat zählt
    als 1 Monat, Teilmonate anteilig. Ohne Vorauszahlungs-Zeiträume wird die
    Einzel-Vorauszahlung (monthly_advance) über die Mietdauer angesetzt.
    """
    payments = sorted(tenant.advance_payments or [], key=lambda p: p.valid_from)
    if not payments:
        return tenant.monthly_advance * _months_between(occ_start, occ_end)
    total = ZERO
    for i, p in enumerate(payments):
        seg_end = (
            payments[i + 1].valid_from - timedelta(days=1) if i + 1 < len(payments) else None
        )
        start = max(p.valid_from, occ_start)
        end = min(seg_end or occ_end, occ_end)
        if start <= end:
            total += p.amount * _months_between(start, end)
    return total


def _advance_breakdown(
    tenant: models.Tenant, year: int, occ_start: date, occ_end: date
) -> list[dict]:
    """Vorauszahlungs-Zeiträume im Abrechnungsjahr (für die Hover-Anzeige).

    Gleiche Segmentierung wie `_advance_total`: ein Eintrag je Vorauszahlungs-
    Zeitraum (gültig ab) mit Start/Ende, Monatsbetrag und Monatsanteilen.
    """
    payments = sorted(tenant.advance_payments or [], key=lambda p: p.valid_from)
    if not payments:
        return [
            {
                "valid_from": occ_start,
                "valid_to": occ_end,
                "amount": tenant.monthly_advance,
                "days": (occ_end - occ_start).days + 1,
                "months": _months_between(occ_start, occ_end),
            }
        ]
    segs: list[dict] = []
    for i, p in enumerate(payments):
        seg_end = (
            payments[i + 1].valid_from - timedelta(days=1) if i + 1 < len(payments) else None
        )
        start = max(p.valid_from, occ_start)
        end = min(seg_end or occ_end, occ_end)
        if start <= end:
            segs.append(
                {
                    "valid_from": start,
                    "valid_to": end,
                    "amount": p.amount,
                    "days": (end - start).days + 1,
                    "months": _months_between(start, end),
                }
            )
    return segs


def _recurring_year_cost(invoices: list, year: int) -> Decimal:
    """Jahreskosten für wiederkehrende Rechnungen (Grundsteuer).

    Grundsteuer gilt ab dem Bescheidsdatum (valid_from) mit einem Jahresbetrag,
    bis ein neuer Bescheid erfasst wird. Mehrere Bescheide teilen das Jahr an
    ihren Stichtagen; der jeweils jüngste Bescheid ist bis zum nächsten gültig.
    """
    ys, ye = year_bounds(year)
    diy = days_in_year(year)
    recs = sorted(
        (inv for inv in invoices if inv.valid_from is not None),
        key=lambda i: i.valid_from,
    )
    if not recs:
        return ZERO

    bounds = sorted(
        {ys}
        | {inv.valid_from for inv in recs if ys <= inv.valid_from <= ye}
        | {ye + timedelta(days=1)}
    )
    total = ZERO
    for i in range(len(bounds) - 1):
        seg_start = bounds[i]
        seg_end = bounds[i + 1] - timedelta(days=1)
        if seg_start > seg_end:
            continue
        active = None
        for inv in recs:
            if inv.valid_from <= seg_start:
                active = inv
        if active is None or active.annual_amount is None:
            continue
        days = (seg_end - seg_start).days + 1
        total += active.annual_amount * (Decimal(days) / Decimal(diy))
    return total


def _category_year_cost(invoices: list, year: int) -> Decimal:
    """Jahreskosten einer Kostenart aus den (objektweiten) Rechnungen.

    Wiederkehrende Grundsteuer über valid_from/Jahresbetrag; alle übrigen
    Rechnungen anteilig über ihre Positionen.
    """
    total = _recurring_year_cost(invoices, year)
    for inv in invoices:
        if inv.kind == InvoiceKind.GRUNDSTEUER and inv.valid_from is not None:
            continue
        for item in inv.items:
            total += pro_rata_amount(item.gross_amount, item.from_date, item.to_date, year)
    return total


def compute_settlement(session: Session, property_id: int, year: int) -> SettlementResult:
    """Berechnet die komplette Nebenkostenabrechnung für ein Objekt und Jahr."""
    prop = session.get(models.Property, property_id)
    if prop is None:
        raise ValueError(f"Property {property_id} nicht gefunden")

    ys, ye = year_bounds(year)
    diy = days_in_year(year)
    warnings: list[str] = []

    units = session.execute(
        select(models.LeaseUnit).where(models.LeaseUnit.property_id == property_id)
    ).scalars().all()
    total_wf = sum((u.living_area for u in units), ZERO)
    total_nf = sum((u.utility_area for u in units), ZERO)

    tenants = session.execute(
        select(models.Tenant)
        .join(models.LeaseUnit)
        .where(models.LeaseUnit.property_id == property_id)
    ).scalars().all()

    active: list[tuple[models.Tenant, int]] = []
    for t in tenants:
        start = max(t.move_in, ys)
        end = min(t.move_out, ye) if t.move_out else ye
        if start <= end:
            active.append((t, (end - start).days + 1))

    configs = session.execute(
        select(models.AllocationConfig)
        .where(models.AllocationConfig.property_id == property_id)
        .order_by(models.AllocationConfig.sort_order)
    ).scalars().all()

    invoices = session.execute(
        select(models.Invoice).where(models.Invoice.property_id == property_id)
    ).scalars().all()
    # Objektweite Rechnungen je Kostenart + wohneinheitenbezogene Kosten je Einheit
    invoices_by_cat: dict[int, list[models.Invoice]] = {}
    unit_costs: dict[tuple[int, int], Decimal] = {}  # (lease_unit_id, cost_category_id) -> Betrag
    for inv in invoices:
        if inv.lease_unit_id is not None:
            for item in inv.items:
                val = pro_rata_amount(item.gross_amount, item.from_date, item.to_date, year)
                key = (inv.lease_unit_id, inv.cost_category_id)
                unit_costs[key] = unit_costs.get(key, ZERO) + val
        else:
            invoices_by_cat.setdefault(inv.cost_category_id, []).append(inv)

    category_lines: list[CategoryLine] = []
    # Code-/Namens-Zuordnung über ALLE Kostenarten des Objekts (auch ohne Umlage-Konfig,
    # z. B. automatisch per Rechnungsart angelegt → wohneinheitenbezogene Kosten).
    all_cats = session.execute(
        select(models.CostCategory).where(models.CostCategory.property_id == property_id)
    ).scalars().all()
    category_code_by_id: dict[int, str] = {cat.id: cat.code for cat in all_cats}
    category_name_by_id: dict[int, str] = {cat.id: cat.name for cat in all_cats}
    water_configured = False
    for cfg in configs:
        cat = cfg.cost_category
        invs = invoices_by_cat.get(cat.id, [])
        year_cost = _category_year_cost(invs, year)
        category_lines.append(CategoryLine(cat.code, cat.name, cfg.allocation_key.value, year_cost))
        if cfg.allocation_key == models.AllocationKey.CONSUMPTION:
            water_configured = True

    water_total_cost = sum(
        (cl.year_cost for cl in category_lines if cl.allocation_key == "CONSUMPTION"), ZERO
    )

    water = compute_water_consumption(session, property_id, year) if water_configured else None
    if water is not None:
        warnings.extend(water.warnings)

    cbm_price: Optional[Decimal] = None
    garden_water_cost = ZERO
    if water is not None:
        if water.total_consumption > 0:
            cbm_price = water_total_cost / water.total_consumption
        else:
            warnings.append("Gesamtwasserverbrauch ist 0 – cbm-Preis kann nicht berechnet werden.")
        if cbm_price is not None:
            garden_water_cost = water.garden_consumption * cbm_price

    tenant_lines: list[TenantLine] = []
    occupied_unit_ids = {t.lease_unit_id for t, _ in active}
    unit_count = len(occupied_unit_ids)
    for t, tenant_days in active:
        unit = t.lease_unit
        occ_start = max(t.move_in, ys)
        occ_end = min(t.move_out, ye) if t.move_out else ye
        time_factor = Decimal(tenant_days) / Decimal(diy)
        advance_months = time_factor * Decimal(12)
        breakdown: dict[str, Decimal] = {}
        details: list[CategoryShare] = []

        for cl in category_lines:
            if cl.allocation_key == "WF":
                area, area_total = unit.living_area, total_wf
                basis_label, basis_total = "Wohnfläche", total_wf
                basis_share = unit.living_area
            elif cl.allocation_key == "NF":
                area, area_total = unit.utility_area, total_nf
                basis_label, basis_total = "Nutzfläche", total_nf
                basis_share = unit.utility_area
            elif cl.allocation_key == "WOHNUNG":
                # Kosten gehen 1:1 gleichmäßig auf jede belegte Wohnung
                area, area_total = None, unit_count
                basis_label, basis_total = "Wohnung", Decimal(unit_count)
                basis_share = Decimal(1)
            else:
                continue  # CONSUMPTION/NONE

            if area_total > 0:
                if area is None:
                    # je Wohnung: gleicher Anteil, zeitanteilig (Miet-Tage/Jahrestage)
                    amount = (cl.year_cost / Decimal(area_total)) * time_factor
                else:
                    amount = cl.year_cost * (area / area_total) * time_factor
            else:
                amount = ZERO
                warnings.append(f"Gesamtfläche 0 für {cl.name} – Anteil 0 gesetzt.")
            breakdown[cl.code] = amount
            details.append(
                CategoryShare(
                    code=cl.code,
                    name=cl.name,
                    allocation_key=cl.allocation_key,
                    year_cost=cl.year_cost,
                    basis_label=basis_label,
                    basis_total=basis_total,
                    basis_share=basis_share,
                    days=tenant_days,
                    amount=amount,
                )
            )

        if water is not None:
            if cbm_price is not None and total_wf > 0:
                breakdown["WASSER_GARTEN"] = (
                    garden_water_cost * (unit.living_area / total_wf) * time_factor
                )
                details.append(
                    CategoryShare(
                        code="WASSER_GARTEN",
                        name="Wasserverbrauch Garten",
                        allocation_key="WF",
                        year_cost=garden_water_cost,
                        basis_label="Wohnfläche",
                        basis_total=total_wf,
                        basis_share=unit.living_area,
                        days=tenant_days,
                        amount=breakdown["WASSER_GARTEN"],
                    )
                )
            else:
                breakdown["WASSER_GARTEN"] = ZERO

            if cbm_price is not None:
                unit_consumption, missing_meters = unit_water_consumption(
                    session, unit.id, occ_start, occ_end
                )
                if missing_meters:
                    warnings.append(
                        f"Mieter {t.name}: Zählerstand zu Ein-/Auszug fehlt "
                        f"({', '.join(missing_meters)})."
                    )
                elif tenant_days < diy:
                    warnings.append(
                        f"Mieter {t.name}: Mietdauer {tenant_days}/{diy} Tage – für exakte "
                        f"Wasserkosten Zählerstände zu Ein-/Auszug erfassen."
                    )
                breakdown["WASSER_VERBRAUCH"] = unit_consumption * cbm_price
                details.append(
                    CategoryShare(
                        code="WASSER_VERBRAUCH",
                        name="Wasserkosten (Verbrauch)",
                        allocation_key="CONSUMPTION",
                        year_cost=water_total_cost,
                        basis_label="Verbrauch",
                        basis_total=water.total_consumption,
                        basis_share=unit_consumption,
                        days=tenant_days,
                        amount=breakdown["WASSER_VERBRAUCH"],
                    )
                )

        # Wohneinheitenbezogene Kosten (z. B. Schornsteinfeger je Wohnung)
        for (uid, cat_id), val in unit_costs.items():
            if uid != unit.id:
                continue
            code = category_code_by_id.get(cat_id)
            if code is None:
                continue
            amount = val * time_factor
            breakdown[code] = breakdown.get(code, ZERO) + amount
            details.append(
                CategoryShare(
                    code=code,
                    name=category_name_by_id.get(cat_id, code),
                    allocation_key="WOHNEINHEIT",
                    year_cost=val,
                    basis_label="Wohneinheit",
                    basis_total=Decimal(1),
                    basis_share=Decimal(1),
                    days=tenant_days,
                    amount=amount,
                )
            )

        total_costs = sum(breakdown.values(), ZERO)
        advance_total = money(_advance_total(t, year, occ_start, occ_end))
        saldo = total_costs - advance_total
        tenant_lines.append(
            TenantLine(
                tenant_id=t.id,
                name=t.name,
                lease_unit_id=unit.id,
                designation=unit.designation,
                living_area=unit.living_area,
                utility_area=unit.utility_area,
                tenant_days=tenant_days,
                time_factor=time_factor,
                advance_months=advance_months,
                period_start=occ_start,
                period_end=occ_end,
                breakdown=breakdown,
                details=details,
                advance_breakdown=_advance_breakdown(t, year, occ_start, occ_end),
                total_costs=total_costs,
                advance_total=advance_total,
                saldo=saldo,
            )
        )

    unallocated_water = ZERO
    if water is not None and cbm_price is not None:
        individual_total = sum(
            (ln.breakdown.get("WASSER_VERBRAUCH", ZERO) for ln in tenant_lines), ZERO
        )
        unallocated_water = money(water_total_cost - garden_water_cost - individual_total)
        if abs(unallocated_water) > CENTS:
            warnings.append(
                f"Restwasser (Leerstand/Abweichung) nicht umgelegt: {unallocated_water} EUR."
            )

    return SettlementResult(
        property_id=property_id,
        property_name=prop.name,
        year=year,
        days_in_year=diy,
        total_wf=total_wf,
        total_nf=total_nf,
        category_lines=category_lines,
        tenant_lines=tenant_lines,
        water=water,
        water_total_cost=water_total_cost,
        water_price_per_m3=cbm_price,
        garden_water_cost=garden_water_cost,
        unallocated_water=unallocated_water,
        warnings=warnings,
    )
