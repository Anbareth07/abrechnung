"""Stromberechnung: Interpolation der Zählerstände, Unterzähler-Abzug, Tarifkosten.

Der Verbrauch des Hauptzählers wird im Zeitraum linear interpoliert. Vom
ermittelten Verbrauch wird der (ebenfalls interpolierte) Verbrauch eines
Unterzählers abgezogen. Die Tarifbestandteile (Grundgebühr €/Jahr,
Arbeitspreis €/kWh, Stromsteuer €/kWh) werden je Gültigkeitszeitraum anteilig
berechnet; Grundgebühr kalenderjahresgenau zeitanteilig,
Arbeitspreis/Stromsteuer verbrauchsanteilig.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from .prorata import ZERO, days_in_year, zaehlerwechsel_consumption

STROM_KINDS = ("GRUNDGEBUEHR", "ARBEITSPREIS", "STROMSTEUER")


def _interpolate(readings: list, d: date) -> Decimal | None:
    """Linear interpoliert den Zählerstand am Datum d.

    Vor dem ersten Stand → erster Wert, nach dem letzten → letzter Wert,
    dazwischen lineare Interpolation zwischen den umgebenden Ständen.
    """
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


def _meter_consumption(
    session: Session, property_id: int, role: str, von: date, bis: date
) -> dict | None:
    readings = session.execute(
        select(models.StromReading)
        .where(
            models.StromReading.property_id == property_id,
            models.StromReading.role == role,
        )
        .order_by(models.StromReading.reading_date)
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


def _strom_readings(session: Session, property_id: int, role: str) -> list:
    return session.execute(
        select(models.StromReading)
        .where(
            models.StromReading.property_id == property_id,
            models.StromReading.role == role,
        )
        .order_by(models.StromReading.reading_date)
    ).scalars().all()


def _coverage_warnings(name: str, readings: list, von: date, bis: date) -> list[str]:
    """Warnungen, wenn die Zählerstände den Zeitraum [von, bis] nicht abdecken."""
    if not readings:
        return [f"{name}: keine Zählerstände – Berechnung für den Zeitraum unvollständig."]
    first, last = readings[0].reading_date, readings[-1].reading_date
    out: list[str] = []
    if first > von:
        out.append(
            f"{name}: Zählerstand zum Jahresanfang ({von.isoformat()}) fehlt "
            f"(erster Stand {first.isoformat()}) – Berechnung unvollständig."
        )
    if last < bis:
        out.append(
            f"{name}: Zählerstand zum Jahresende ({bis.isoformat()}) fehlt "
            f"(letzter Stand {last.isoformat()}) – Berechnung unvollständig."
        )
    return out


def berechnung(session: Session, property_id: int, von: date, bis: date) -> dict:
    """Berechnet Verbrauch und Kosten für Strom im Zeitraum [von, bis]."""
    if von > bis:
        raise ValueError("Zeitraum ungültig: von darf nicht nach bis liegen")

    prop = session.get(models.Property, property_id)
    unter_aktiv = bool(prop.strom_unterzaehler_aktiv) if prop is not None else True

    # Warnungen, wenn die Zählerstände den Zeitraum nicht abdecken (unvollständige Berechnung)
    warnings: list[str] = []
    haupt_readings = _strom_readings(session, property_id, "HAUPTZAEHLER")
    unter_readings = _strom_readings(session, property_id, "UNTERZAEHLER") if unter_aktiv else []
    prices_exist = (
        session.execute(
            select(models.StromPrice.id).where(models.StromPrice.property_id == property_id).limit(1)
        ).first()
        is not None
    )
    if prices_exist or haupt_readings or unter_readings:
        warnings.extend(_coverage_warnings("Strom Hauptzähler", haupt_readings, von, bis))
        if unter_aktiv:
            warnings.extend(_coverage_warnings("Strom Unterzähler", unter_readings, von, bis))

    haupt = _meter_consumption(session, property_id, "HAUPTZAEHLER", von, bis)
    unter = _meter_consumption(session, property_id, "UNTERZAEHLER", von, bis) if unter_aktiv else None
    haupt_consumption = Decimal(haupt["consumption"]) if haupt else ZERO
    unter_consumption = Decimal(unter["consumption"]) if unter else ZERO
    netto_verbrauch = max(haupt_consumption - unter_consumption, ZERO)

    total_days = (bis - von).days + 1
    positionen: list[dict] = []
    sum_netto = sum_vat = ZERO
    for kind in STROM_KINDS:
        prices = session.execute(
            select(models.StromPrice)
            .where(
                models.StromPrice.property_id == property_id,
                models.StromPrice.kind == kind,
            )
            .order_by(models.StromPrice.valid_from)
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
            else:
                # €/kWh → verbrauchsanteilig
                menge = float(netto_verbrauch * (Decimal(days) / Decimal(total_days)))
                netto = p.amount * (netto_verbrauch * Decimal(days) / Decimal(total_days))
            vat = netto * p.vat_rate / Decimal(100)
            sum_netto += netto
            sum_vat += vat
            positionen.append(
                {
                    "art": kind,
                    "von": seg_start.isoformat(),
                    "bis": seg_end.isoformat(),
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
        "hauptzaehler": haupt,
        "unterzaehler": unter,
        "netto_verbrauch": float(netto_verbrauch),
        "positionen": positionen,
        "warnings": warnings,
        "summen": {
            "netto": float(sum_netto),
            "vat": float(sum_vat),
            "brutto": float(sum_netto + sum_vat),
        },
    }


def unterzaehler_verbrauch(session: Session, property_id: int, von: date, bis: date) -> Decimal:
    """Verbrauch des Unterzählers im Zeitraum (Heizstromanteil für Techem)."""
    try:
        res = berechnung(session, property_id, von, bis)
    except ValueError:
        return ZERO
    unter = res.get("unterzaehler")
    if unter is None:
        return ZERO
    # Heizstrom immer auf ganze kWh gerundet
    return Decimal(str(unter["consumption"])).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def unterzaehler_kosten(session: Session, property_id: int, von: date, bis: date) -> dict:
    """Kosten des Unterzähler-Verbrauchs (Heizstrom) im Zeitraum.

    Arbeitspreis und Stromsteuer werden tageanteilig auf den (auf ganze kWh
    gerundeten) Unterzähler-Verbrauch angewendet; die Grundgebühr bleibt beim
    allgemeinen Strom.
    """
    unter = _meter_consumption(session, property_id, "UNTERZAEHLER", von, bis)
    if unter is None:
        return {"kwh": 0.0, "netto": 0.0, "vat": 0.0, "brutto": 0.0}
    kwh = Decimal(str(unter["consumption"])).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    total_days = (bis - von).days + 1
    netto = vat = ZERO
    for kind in ("ARBEITSPREIS", "STROMSTEUER"):
        prices = (
            session.execute(
                select(models.StromPrice)
                .where(
                    models.StromPrice.property_id == property_id,
                    models.StromPrice.kind == kind,
                )
                .order_by(models.StromPrice.valid_from)
            )
            .scalars()
            .all()
        )
        for p in prices:
            seg_start = max(von, p.valid_from)
            seg_end = min(bis, p.valid_to)
            if seg_start > seg_end:
                continue
            days = (seg_end - seg_start).days + 1
            n = p.amount * (kwh * Decimal(days) / Decimal(total_days))
            v = n * p.vat_rate / Decimal(100)
            netto += n
            vat += v
    return {
        "kwh": float(kwh),
        "netto": float(netto),
        "vat": float(vat),
        "brutto": float(netto + vat),
    }
