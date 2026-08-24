"""Tagesgenaue Pro-rata-Hilfsfunktionen (keine DB-Abhängigkeit)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

ZERO = Decimal("0")


def zaehlerwechsel_series(readings: list) -> list[tuple]:
    """Effektive (monoton steigende) Zählerstandsserie unter Berücksichtigung von Zählerwechseln.

    readings: nach Datum sortierte Liste von Objekten mit `.reading_date`, `.value`,
    `.vor_zaehlerwechsel` (bool) und `.neuer_zaehler_start` (Decimal, Standard 0).
    Ein als `vor_zaehlerwechsel` markierter Stand ist der letzte Stand des ALTEN Zählers;
    der neue Zähler beginnt danach bei `neuer_zaehler_start`. Die Rückgabe enthält
    (Stand-Objekt, effektiver kumulierter Wert) und ist damit streng monoton steigend.
    """
    eff: list[tuple] = []
    prev_value: Decimal | None = None
    prev_eff: Decimal | None = None
    prev_vor = False
    prev_neu_start = ZERO
    for r in readings:
        v = Decimal(r.value)
        if prev_value is None:
            eff_v = v
        elif prev_vor:
            # Zählerwechsel: neuer Zähler beginnt bei prev_neu_start (Standard 0)
            eff_v = prev_eff + (v - prev_neu_start)
        else:
            eff_v = prev_eff + (v - prev_value)
        eff.append((r, eff_v))
        prev_value, prev_eff = v, eff_v
        prev_vor = bool(getattr(r, "vor_zaehlerwechsel", False))
        prev_neu_start = Decimal(getattr(r, "neuer_zaehler_start", 0) or 0)
    return eff


def _eff_interpolate(eff: list[tuple], d: date) -> Decimal | None:
    """Linearer interpolierter Wert der effektiven Serie am Datum d (Clamping an den Rändern)."""
    if not eff:
        return None
    if d <= eff[0][0].reading_date:
        return eff[0][1]
    if d >= eff[-1][0].reading_date:
        return eff[-1][1]
    lo = max((r for r in eff if r[0].reading_date <= d), key=lambda x: x[0].reading_date)
    hi = min((r for r in eff if r[0].reading_date >= d), key=lambda x: x[0].reading_date)
    if lo[0].reading_date == hi[0].reading_date:
        return lo[1]
    frac = Decimal((d - lo[0].reading_date).days) / Decimal(
        (hi[0].reading_date - lo[0].reading_date).days
    )
    return lo[1] + (hi[1] - lo[1]) * frac


def zaehlerwechsel_consumption(
    readings: list, start: date, end: date, clamp: bool = False
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """Verbrauch im Zeitraum [start, end] (Zählerwechsel-sicher).

    Rückgabe: (consumption, start_reading, end_reading) auf Basis der effektiven
    (monotonen) Serie. Ohne `clamp` werden die umgebenden Stände (letzter <= start,
    erster >= end) verwendet und `None` geliefert, wenn diese fehlen; mit `clamp`
    wird an den Rändern interpoliert (Clamping auf den ersten/letzten Stand).
    """
    if not readings:
        return None, None, None
    eff = zaehlerwechsel_series(readings)
    if clamp:
        s = _eff_interpolate(eff, start)
        e = _eff_interpolate(eff, end)
    else:
        before = [r for r in readings if r.reading_date <= start]
        after = [r for r in readings if r.reading_date >= end]
        if not before or not after:
            return None, None, None
        eff_map = {r.id: v for r, v in eff}
        s = eff_map.get(before[-1].id)
        e = eff_map.get(after[0].id)
    if s is None or e is None:
        return None, None, None
    return max(e - s, ZERO), s, e


def days_in_year(year: int) -> int:
    """Anzahl der Tage im Abrechnungsjahr (365 oder 366)."""
    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
        return 366
    return 365


def year_bounds(year: int) -> tuple[date, date]:
    """Start- und Enddatum des Kalenderjahres (inklusiv)."""
    return date(year, 1, 1), date(year, 12, 31)


def overlap_days(start_a: date, end_a: date, start_b: date, end_b: date) -> int:
    """Anzahl überlappender Tage zwischen [start_a, end_a] und [start_b, end_b] (inklusiv)."""
    start = max(start_a, start_b)
    end = min(end_a, end_b)
    if start > end:
        return 0
    return (end - start).days + 1


def interval_days(start: date, end: date) -> int:
    """Anzahl Tage im Intervall [start, end] (inklusiv)."""
    return (end - start).days + 1


def pro_rata_amount(amount: Decimal, item_start: date, item_end: date, year: int) -> Decimal:
    """Anteil eines Betrags, der in das Abrechnungsjahr fällt.

    Beispiel: Rechnung 01.07.2025–30.06.2026, Jahr 2026 → nur 01.01.–30.06. zählt.
    """
    ys, ye = year_bounds(year)
    overlap = overlap_days(item_start, item_end, ys, ye)
    total = interval_days(item_start, item_end)
    if total <= 0 or overlap <= 0:
        return ZERO
    return (amount * Decimal(overlap)) / Decimal(total)
