"""Tagesgenaue Pro-rata-Hilfsfunktionen (keine DB-Abhängigkeit)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

ZERO = Decimal("0")


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
