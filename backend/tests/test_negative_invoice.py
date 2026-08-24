"""Tests für Gutschriften/negative Rechnungsbeträge (z. B. Strompreisbremse-Erstattung)."""

from datetime import date
from decimal import Decimal

from app.services.engine import compute_settlement
from tests import helpers


def _objekt_mit_kostenart(session):
    prop = helpers.make_property(session, "Objekt")
    cat = helpers.make_category(session, prop, "strom", "Strom")
    helpers.make_config(session, prop, cat, helpers.AllocationKey.NF, 1)
    u = helpers.make_unit(session, prop, "Wohnung 1", "100.0", "0.0")
    helpers.make_tenant(session, u, "Mieter A", date(2020, 1, 1), "100.00")
    return prop, cat


def test_gutschrift_reduziert_kosten(session):
    """Negative Rechnung (Gutschrift) verringert die Jahreskosten der Kostenart."""
    prop, cat = _objekt_mit_kostenart(session)
    helpers.make_invoice(
        session, prop, cat, date(2025, 1, 1), date(2025, 12, 31),
        [(date(2025, 1, 1), date(2025, 12, 31), "1000.00")],
    )
    helpers.make_invoice(
        session, prop, cat, date(2025, 1, 1), date(2025, 12, 31),
        [(date(2025, 1, 1), date(2025, 12, 31), "-200.00")],
    )
    session.commit()

    result = compute_settlement(session, prop.id, 2025)
    line = next(cl for cl in result.category_lines if cl.code == "strom")
    assert line.year_cost == Decimal("800.00")

    share = result.tenant_lines[0].details[0]
    assert share.amount == Decimal("800.00")


def test_nur_gutschrift_ergibt_erstattung(session):
    """Nur eine Gutschrift (keine Kosten) ergibt einen negativen Mieter-Anteil (Erstattung)."""
    prop, cat = _objekt_mit_kostenart(session)
    helpers.make_invoice(
        session, prop, cat, date(2025, 1, 1), date(2025, 12, 31),
        [(date(2025, 1, 1), date(2025, 12, 31), "-200.00")],
    )
    session.commit()

    result = compute_settlement(session, prop.id, 2025)
    line = next(cl for cl in result.category_lines if cl.code == "strom")
    assert line.year_cost == Decimal("-200.00")

    share = result.tenant_lines[0].details[0]
    assert share.amount == Decimal("-200.00")
