"""Vollständigkeits-Check: welche Daten fehlen für die Erstellung einer Abrechnung."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..models.enums import InvoiceKind
from . import prorata
from .prorata import year_bounds
from .water import WATER_METER_TYPES


@dataclass
class MissingItem:
    kind: str  # "INVOICE" | "METER_READING"
    label: str
    detail: str = ""
    category_id: Optional[int] = None


def check_completeness(session: Session, property_id: int, year: int) -> list[MissingItem]:
    """Liefert die Liste fehlender Daten (Rechnungen, Zählerstände) für ein Abrechnungsjahr."""
    ys, ye = year_bounds(year)
    missing: list[MissingItem] = []

    configs = session.execute(
        select(models.AllocationConfig)
        .where(models.AllocationConfig.property_id == property_id)
        .order_by(models.AllocationConfig.sort_order)
    ).scalars().all()

    # Kostenarten, die je Jahr als "bewusst keine Rechnung" markiert sind
    no_invoice = {
        (f.property_id, f.cost_category_id)
        for f in session.execute(
            select(models.CategoryNoInvoice).where(models.CategoryNoInvoice.year == year)
        ).scalars()
    }
    # Kostenart, die als Strom-Ziel verknüpft ist (wird über das Strom-Modul abgedeckt)
    prop = session.get(models.Property, property_id)
    strom_cat_id = prop.strom_allocation_category_id if prop else None

    invoices = session.execute(
        select(models.Invoice).where(models.Invoice.property_id == property_id)
    ).scalars().all()
    items_by_cat: dict[int, list[models.InvoiceItem]] = {}
    # Kostenarten, die durch eine wiederkehrende Rechnung (Grundsteuer mit gültig ab +
    # Jahresbetrag, ohne Positionen) im Jahr abgedeckt sind.
    recurring_cats: set[int] = set()
    for inv in invoices:
        for item in inv.items:
            items_by_cat.setdefault(inv.cost_category_id, []).append(item)
        if (
            inv.kind == InvoiceKind.GRUNDSTEUER.value
            and inv.valid_from is not None
            and inv.valid_from <= ye
        ):
            recurring_cats.add(inv.cost_category_id)

    for cfg in configs:
        if cfg.allocation_key == models.AllocationKey.NONE:
            continue
        cat = cfg.cost_category
        if (property_id, cat.id) in no_invoice or cat.id == strom_cat_id:
            continue
        has_overlap = cat.id in recurring_cats or any(
            prorata.overlap_days(item.from_date, item.to_date, ys, ye) > 0
            for item in items_by_cat.get(cat.id, [])
        )
        if not has_overlap:
            missing.append(
                MissingItem(
                    kind="INVOICE",
                    label=f"Rechnung fehlt: {cat.name}",
                    detail=f"Umlage {cfg.allocation_key.value}",
                    category_id=cat.id,
                )
            )

    unit_id_sub = (
        select(models.LeaseUnit.id)
        .where(models.LeaseUnit.property_id == property_id)
        .scalar_subquery()
    )
    meters = session.execute(
        select(models.Meter).where(
            sa.or_(
                models.Meter.property_id == property_id,
                models.Meter.lease_unit_id.in_(unit_id_sub),
            )
        )
    ).scalars().all()

    for meter in meters:
        if meter.meter_type not in WATER_METER_TYPES:
            continue
        readings = session.execute(
            select(models.MeterReading).where(models.MeterReading.meter_id == meter.id)
        ).scalars().all()
        if not any(r.reading_date <= ys for r in readings):
            missing.append(
                MissingItem(
                    kind="METER_READING",
                    label=f"Zählerstand Jahresanfang fehlt: {meter.name}",
                    detail=f"Stand ≤ {ys.isoformat()}",
                )
            )
        if not any(r.reading_date >= ye for r in readings):
            missing.append(
                MissingItem(
                    kind="METER_READING",
                    label=f"Zählerstand Jahresende fehlt: {meter.name}",
                    detail=f"Stand ≥ {ye.isoformat()}",
                )
            )

    return missing
