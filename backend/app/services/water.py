"""Wasserberechnung (Objekt 1): Verbrauch aus Zählerständen, cbm-Preis, Garten-/Mieter-Umlage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from .prorata import ZERO, year_bounds, zaehlerwechsel_consumption

# Zählertypen, die in die Wasserberechnung einfließen.
# Gartenwasser-Zähler (GARDEN) werden NICHT mehr berücksichtigt.
WATER_METER_TYPES = (
    models.MeterType.APARTMENT_WATER,
    models.MeterType.WASHING_MACHINE,
)

# Zählertypen, die den individuellen Mieter-Verbrauch bilden.
UNIT_WATER_METER_TYPES = (
    models.MeterType.APARTMENT_WATER,
    models.MeterType.WASHING_MACHINE,
)


@dataclass
class MeterConsumption:
    meter_id: int
    name: str
    meter_type: str
    lease_unit_id: Optional[int]
    start_reading: Optional[Decimal]
    end_reading: Optional[Decimal]
    consumption: Decimal
    missing: bool = False


@dataclass
class WaterResult:
    total_consumption: Decimal = ZERO
    garden_consumption: Decimal = ZERO
    meter_consumptions: list[MeterConsumption] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def meter_consumption(
    session: Session, meter_id: int, start_date: date, end_date: date
) -> MeterConsumption:
    """Verbrauch eines Zählers im Zeitfenster [start_date, end_date].

    Start = letzter Stand ≤ start_date; Ende = erster Stand ≥ end_date.
    Fehlt eine Randablesung, wird der Zähler als fehlend markiert (konservativ).
    """
    meter = session.get(models.Meter, meter_id)
    readings = session.execute(
        select(models.MeterReading)
        .where(models.MeterReading.meter_id == meter_id)
        .order_by(models.MeterReading.reading_date)
    ).scalars().all()

    if meter is None or not readings:
        return MeterConsumption(
            meter_id=meter_id,
            name=meter.name if meter else f"Zähler {meter_id}",
            meter_type=meter.meter_type.value if meter else "",
            lease_unit_id=meter.lease_unit_id if meter else None,
            start_reading=None,
            end_reading=None,
            consumption=ZERO,
            missing=True,
        )

    before = [r for r in readings if r.reading_date <= start_date]
    after = [r for r in readings if r.reading_date >= end_date]
    missing = not before or not after

    # Zählerwechsel-sichere Berechnung (Wert-vor-Wechsel + Startwert des neuen Zählers)
    consumption, start, end = zaehlerwechsel_consumption(readings, start_date, end_date)
    if missing or consumption is None:
        missing = True
        consumption = ZERO
        start = end = None

    return MeterConsumption(
        meter_id=meter_id,
        name=meter.name,
        meter_type=meter.meter_type.value,
        lease_unit_id=meter.lease_unit_id,
        start_reading=start,
        end_reading=end,
        consumption=consumption,
        missing=missing,
    )


def _property_water_meters(session: Session, property_id: int):
    unit_id_sub = (
        select(models.LeaseUnit.id)
        .where(models.LeaseUnit.property_id == property_id)
        .scalar_subquery()
    )
    return session.execute(
        select(models.Meter).where(
            sa.or_(
                models.Meter.property_id == property_id,
                models.Meter.lease_unit_id.in_(unit_id_sub),
            )
        )
    ).scalars().all()


def compute_water_consumption(
    session: Session, property_id: int, year: int, include_washing_machine: bool = True
) -> WaterResult:
    """Jahres-Gesamtverbrauch für den cbm-Preis (Nenner).

    Gartenwasser wird nicht mehr berücksichtigt (kein Einfluss auf den
    Gesamtverbrauch und damit den cbm-Preis).
    """
    ys, ye = year_bounds(year)
    result = WaterResult()

    for meter in _property_water_meters(session, property_id):
        if meter.meter_type not in WATER_METER_TYPES:
            continue
        if meter.meter_type == models.MeterType.WASHING_MACHINE and not include_washing_machine:
            continue

        mc = meter_consumption(session, meter.id, ys, ye)
        result.meter_consumptions.append(mc)

        if mc.missing:
            result.warnings.append(f"Zählerstand fehlt (Jahresgrenze): {meter.name}")
            continue

        result.total_consumption += mc.consumption

    return result


def unit_water_consumption(
    session: Session,
    unit_id: int,
    start_date: date,
    end_date: date,
    include_washing_machine: bool = True,
) -> tuple[Decimal, list[str]]:
    """Individueller Verbrauch einer Mieteinheit (Wohnungs- + Waschmaschinen-Zähler).

    Liefert (Verbrauch, fehlende Zählernamen). Der Verbrauch summiert nur Zähler
    mit vollständiger Randablesung; fehlende werden separat gemeldet. Ohne
    Waschmaschinen-Zähler (include_washing_machine=False) zählen nur die
    Wohnungs-Wasserzähler.
    """
    meter_types = UNIT_WATER_METER_TYPES
    if not include_washing_machine:
        meter_types = (models.MeterType.APARTMENT_WATER,)
    meters = session.execute(
        select(models.Meter).where(
            models.Meter.lease_unit_id == unit_id,
            models.Meter.meter_type.in_(meter_types),
        )
    ).scalars().all()

    total = ZERO
    missing: list[str] = []
    for meter in meters:
        mc = meter_consumption(session, meter.id, start_date, end_date)
        if mc.missing:
            missing.append(meter.name)
            continue
        total += mc.consumption

    return total, missing
