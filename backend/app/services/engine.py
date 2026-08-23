"""Orchestrierung der Jahresabrechnung: Flächenumlage + Wasser + Saldo."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
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
    breakdown: dict[str, Decimal] = field(default_factory=dict)
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
    items_by_cat: dict[int, list[models.InvoiceItem]] = {}
    for inv in invoices:
        for item in inv.items:
            items_by_cat.setdefault(inv.cost_category_id, []).append(item)

    category_lines: list[CategoryLine] = []
    water_configured = False
    for cfg in configs:
        cat = cfg.cost_category
        items = items_by_cat.get(cat.id, [])
        year_cost = sum(
            (pro_rata_amount(item.gross_amount, item.from_date, item.to_date, year) for item in items),
            ZERO,
        )
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
    for t, tenant_days in active:
        unit = t.lease_unit
        time_factor = Decimal(tenant_days) / Decimal(diy)
        advance_months = time_factor * Decimal(12)
        breakdown: dict[str, Decimal] = {}

        for cl in category_lines:
            if cl.allocation_key == "WF":
                area, area_total = unit.living_area, total_wf
            elif cl.allocation_key == "NF":
                area, area_total = unit.utility_area, total_nf
            else:
                continue  # CONSUMPTION/NONE

            if area_total > 0:
                breakdown[cl.code] = money(cl.year_cost * (area / area_total) * time_factor)
            else:
                breakdown[cl.code] = ZERO
                warnings.append(f"Gesamtfläche 0 für {cl.name} – Anteil 0 gesetzt.")

        if water is not None:
            if cbm_price is not None and total_wf > 0:
                breakdown["WASSER_GARTEN"] = money(
                    garden_water_cost * (unit.living_area / total_wf) * time_factor
                )
            else:
                breakdown["WASSER_GARTEN"] = ZERO

            if cbm_price is not None:
                occ_start = max(t.move_in, ys)
                occ_end = min(t.move_out, ye) if t.move_out else ye
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
                breakdown["WASSER_VERBRAUCH"] = money(unit_consumption * cbm_price)

        total_costs = money(sum(breakdown.values(), ZERO))
        advance_total = money(t.monthly_advance * advance_months)
        saldo = money(total_costs - advance_total)

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
                breakdown=breakdown,
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
