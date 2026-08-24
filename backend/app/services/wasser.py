"""Wasserberechnung (Plan B): Interpolation des Hauptzählers, Tarifkosten.

Die Tarifbestandteile werden je Gültigkeitszeitraum anteilig berechnet:
- TRINKWASSER/SCHMUTZWASSER (€/m³): verbrauchsanteilig (Hauptzähler)
- NIEDERSCHLAGSWASSER (€/m²/Jahr): versiegelte Fläche am Objekt, kalenderjahresgenau zeitanteilig
- GRUNDGEBUEHR (€/Jahr): kalenderjahresgenau zeitanteilig
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..models.enums import AllocationKey
from .prorata import ZERO, days_in_year, zaehlerwechsel_consumption
from .water import unit_water_consumption

WASSER_KINDS = ("TRINKWASSER", "SCHMUTZWASSER", "NIEDERSCHLAGSWASSER", "GRUNDGEBUEHR")

# Einheit je Art für Menge (Anzeige)
WASSER_EINHEIT = {
    "TRINKWASSER": "m³",
    "SCHMUTZWASSER": "m³",
    "NIEDERSCHLAGSWASSER": "m²",
    "GRUNDGEBUEHR": "Jahr",
}

# Satz-Einheit je Art (Anzeige)
WASSER_SATZ_EINHEIT = {
    "TRINKWASSER": "€/m³",
    "SCHMUTZWASSER": "€/m³",
    "NIEDERSCHLAGSWASSER": "€/m²/Jahr",
    "GRUNDGEBUEHR": "€/Jahr",
}


def _interpolate(readings: list, d: date) -> Decimal | None:
    """Linear interpoliert den Zählerstand am Datum d (vor dem ersten → erster Wert,
    nach dem letzten → letzter Wert, dazwischen lineare Interpolation)."""
    vals = [(r.reading_date, r.value) for r in readings]
    if not vals:
        return None
    if d <= vals[0][0]:
        return vals[0][1]
    if d >= vals[-1][0]:
        return vals[-1][1]
    lo = max((v for v in vals if v[0] <= d), key=lambda v: v[0])
    hi = min((v for v in vals if v[0] >= d), key=lambda v: v[0])
    if lo[0] == hi[0]:
        return lo[1]
    frac = Decimal((d - lo[0]).days) / Decimal((hi[0] - lo[0]).days)
    return lo[1] + (hi[1] - lo[1]) * frac


def is_plan_a(session: Session, property_id: int) -> bool:
    """Plan A: mindestens eine zugeordnete Wasser-Kostenstelle (Trink/Schmutz/Niederschlag)
    hat 'Verbrauch' (CONSUMPTION) als Umlageschlüssel → Verteilung über Wohnungszähler."""
    prop = session.get(models.Property, property_id)
    if prop is None:
        return False
    cat_ids = [
        c
        for c in (
            prop.wasser_trinkwasser_category_id,
            prop.wasser_schmutzwasser_category_id,
            prop.wasser_niederschlag_category_id,
        )
        if c
    ]
    if not cat_ids:
        return False
    return (
        session.execute(
            select(models.AllocationConfig).where(
                models.AllocationConfig.property_id == property_id,
                models.AllocationConfig.cost_category_id.in_(cat_ids),
                models.AllocationConfig.allocation_key == AllocationKey.CONSUMPTION,
            )
        ).scalars().first()
        is not None
    )


def _apartment_consumption(session: Session, property_id: int, von: date, bis: date) -> Decimal:
    """Summe aller Wohnungsverbräuche (Wohnung + ggf. Waschmaschinen-Zähler) im Zeitraum (Plan A)."""
    prop = session.get(models.Property, property_id)
    include_wm = bool(prop.wasser_waschmaschinen_aktiv) if prop is not None else True
    units = session.execute(
        select(models.LeaseUnit).where(models.LeaseUnit.property_id == property_id)
    ).scalars().all()
    total = ZERO
    for unit in units:
        cons, _ = unit_water_consumption(session, unit.id, von, bis, include_wm)
        total += cons
    return total


def _meter_consumption(session: Session, property_id: int, von: date, bis: date) -> dict | None:
    readings = session.execute(
        select(models.WasserReading)
        .where(models.WasserReading.property_id == property_id)
        .order_by(models.WasserReading.reading_date)
    ).scalars().all()
    if not readings:
        return None
    # Zählerwechsel-sichere Berechnung (Wert-vor-Wechsel + Startwert des neuen Zählers);
    # interpolierte Randwerte mit Clamping (Zeitraum kann über die letzte Ablesung hinausgehen)
    consumption, start, end = zaehlerwechsel_consumption(readings, von, bis, clamp=True)
    if consumption is None:
        return None
    return {
        "start_reading": float(start),
        "end_reading": float(end),
        "consumption": float(consumption),
    }


def _prorate_annual(amount: Decimal, seg_start: date, seg_end: date) -> Decimal:
    """Jahresbetrag anteilig über ggf. mehrere Kalenderjahre (tagegenau)."""
    total = ZERO
    year = seg_start.year
    while year <= seg_end.year:
        y_start = date(year, 1, 1)
        y_end = date(year, 12, 31)
        start = max(seg_start, y_start)
        end = min(seg_end, y_end)
        if start <= end:
            days = (end - start).days + 1
            total += amount * Decimal(days) / Decimal(days_in_year(year))
        year += 1
    return total


def berechnung(session: Session, property_id: int, von: date, bis: date) -> dict:
    """Berechnet Verbrauch und Kosten für Wasser im Zeitraum [von, bis]."""
    if von > bis:
        raise ValueError("Zeitraum ungültig: von darf nicht nach bis liegen")

    plan_a = is_plan_a(session, property_id)
    if plan_a:
        # Plan A: keine Hauptzählerstände – Verbrauch = Summe der Wohnungszähler
        haupt = None
        verbrauch = _apartment_consumption(session, property_id, von, bis)
    else:
        haupt = _meter_consumption(session, property_id, von, bis)
        verbrauch = Decimal(haupt["consumption"]) if haupt else ZERO

    prop = session.get(models.Property, property_id)
    versiegelt = prop.wasser_versiegelte_flaeche if prop is not None else None
    versiegelt_dec = Decimal(versiegelt) if versiegelt is not None else ZERO

    total_days = (bis - von).days + 1
    positionen: list[dict] = []
    sum_netto = sum_vat = ZERO
    for kind in WASSER_KINDS:
        prices = session.execute(
            select(models.WasserPrice)
            .where(
                models.WasserPrice.property_id == property_id,
                models.WasserPrice.kind == kind,
            )
            .order_by(models.WasserPrice.valid_from)
        ).scalars().all()
        for p in prices:
            seg_start = max(von, p.valid_from)
            seg_end = min(bis, p.valid_to)
            if seg_start > seg_end:
                continue
            days = (seg_end - seg_start).days + 1
            if kind == "GRUNDGEBUEHR":
                # €/Jahr → kalenderjahresgenau zeitanteilig
                jahres_anteil = _prorate_annual(Decimal("1"), seg_start, seg_end)
                netto = p.amount * jahres_anteil
                menge = float(jahres_anteil)
            elif kind == "NIEDERSCHLAGSWASSER":
                # €/m²/Jahr → versiegelte Fläche × Satz, kalenderjahresgenau zeitanteilig
                jahres_anteil = _prorate_annual(Decimal("1"), seg_start, seg_end)
                menge = float(versiegelt_dec)
                netto = p.amount * versiegelt_dec * jahres_anteil
            else:
                # €/m³ → verbrauchsanteilig
                menge = float(verbrauch * (Decimal(days) / Decimal(total_days)))
                netto = p.amount * (verbrauch * Decimal(days) / Decimal(total_days))
            vat = netto * p.vat_rate / Decimal(100)
            sum_netto += netto
            sum_vat += vat
            positionen.append(
                {
                    "art": kind,
                    "von": seg_start.isoformat(),
                    "bis": seg_end.isoformat(),
                    "einheit": WASSER_EINHEIT[kind],
                    "satz_einheit": WASSER_SATZ_EINHEIT[kind],
                    "menge": menge,
                    "satz": float(p.amount),
                    "vat_rate": float(p.vat_rate),
                    "netto": float(netto),
                    "vat": float(vat),
                    "brutto": float(netto + vat),
                }
            )

    return {
        "property_id": property_id,
        "von": von.isoformat(),
        "bis": bis.isoformat(),
        "plan": "A" if plan_a else "B",
        "hauptzaehler": haupt,
        "verbrauch": float(verbrauch),
        "versiegelte_flaeche": float(versiegelt_dec) if versiegelt is not None else None,
        "positionen": positionen,
        "summen": {
            "netto": float(sum_netto),
            "vat": float(sum_vat),
            "brutto": float(sum_netto + sum_vat),
        },
    }
