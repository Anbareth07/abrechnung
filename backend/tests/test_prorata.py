from datetime import date
from decimal import Decimal

from app.services import prorata


def test_days_in_year():
    assert prorata.days_in_year(2024) == 366  # Schaltjahr
    assert prorata.days_in_year(2025) == 365
    assert prorata.days_in_year(2026) == 365
    assert prorata.days_in_year(2000) == 366
    assert prorata.days_in_year(1900) == 365


def test_overlap_days_full_year():
    assert prorata.overlap_days(
        date(2026, 1, 1), date(2026, 12, 31), date(2026, 1, 1), date(2026, 12, 31)
    ) == 365


def test_overlap_days_mid_year_invoice():
    # 01.07.2025–30.06.2026 schneidet 2026: Jan–Jun = 181 Tage
    assert prorata.overlap_days(
        date(2025, 7, 1), date(2026, 6, 30), date(2026, 1, 1), date(2026, 12, 31)
    ) == 181


def test_overlap_days_no_overlap():
    assert prorata.overlap_days(
        date(2025, 1, 1), date(2025, 12, 31), date(2026, 1, 1), date(2026, 12, 31)
    ) == 0


def test_pro_rata_full_year():
    assert prorata.pro_rata_amount(Decimal("500"), date(2026, 1, 1), date(2026, 12, 31), 2026) == Decimal("500")


def test_pro_rata_mid_year_invoice():
    # Rechnung 01.07.2025–30.06.2026 → im Jahr 2026 nur 181/365 des Betrags
    amount = Decimal("1000")
    expected = amount * Decimal(181) / Decimal(365)
    assert prorata.pro_rata_amount(amount, date(2025, 7, 1), date(2026, 6, 30), 2026) == expected


def test_pro_rata_no_overlap_is_zero():
    assert prorata.pro_rata_amount(Decimal("100"), date(2025, 1, 1), date(2025, 12, 31), 2026) == Decimal("0")


def test_pro_rata_leap_year():
    # 2024 ist Schaltjahr: volles Jahr = 366 Tage
    assert prorata.pro_rata_amount(Decimal("366"), date(2024, 1, 1), date(2024, 12, 31), 2024) == Decimal("366")
