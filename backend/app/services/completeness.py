"""Vollständigkeits-Check: welche Daten fehlen für die Erstellung einer Abrechnung."""

from __future__ import annotations

from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from . import prorata
from .prorata import year_bounds
from .water import WATER_METER_TYPES


@dataclass
class MissingItem:
    kind: str  # "INVOICE" | "METER_READING"
    label: str
    detail: str = ""


def check_completeness(session: Session, property_id: int, year: int) -> list[MissingItem]:
    """Liefert die Liste fehlender Daten (Rechnungen, Zählerstände) für ein Abrechnungsjahr."""
    ys, ye = year_bounds(year)
    missing: list[MissingItem] = []

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

    for cfg in configs:
        if cfg.allocation_key == models.AllocationKey.NONE:
            continue
        cat = cfg.cost_category
        has_overlap = any(
            prorata.overlap_days(item.from_date, item.to_date, ys, ye) > 0
            for item in items_by_cat.get(cat.id, [])
        )
        if not has_overlap:
            missing.append(
                MissingItem(
                    kind="INVOICE",
                    label=f"Rechnung fehlt: {cat.name}",
                    detail=f"Umlage {cfg.allocation_key.value}",
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
