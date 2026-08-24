"""Tests für den Anrechnungsanteil (Zähler/Nenner) an Rechnungen."""

from datetime import date
from decimal import Decimal

from app.models.enums import InvoiceKind
from app.services.engine import compute_settlement
from tests import helpers


def _objekt_mit_grundsteuer(session):
    prop = helpers.make_property(session, "Objekt")
    cat = helpers.make_category(session, prop, "grundsteuer", "Grundsteuer")
    helpers.make_config(session, prop, cat, helpers.AllocationKey.NF, 1)
    u = helpers.make_unit(session, prop, "Wohnung 1", "100.0", "0.0")
    helpers.make_tenant(session, u, "Mieter A", date(2020, 1, 1), "100.00")
    return prop, cat, u


def test_anteil_factor_normale_rechnung(session):
    """Normale Rechnung mit Anteil: angerechnet wird Betrag × Zähler/Nenner."""
    prop, cat, _ = _objekt_mit_grundsteuer(session)
    inv = helpers.make_invoice(
        session, prop, cat, date(2025, 1, 1), date(2025, 12, 31),
        [(date(2025, 1, 1), date(2025, 12, 31), "1121.48")],
    )
    inv.anteil_zaehler = Decimal("13044")
    inv.anteil_nenner = Decimal("13764")
    session.commit()

    result = compute_settlement(session, prop.id, 2025)
    grund = next(cl for cl in result.category_lines if cl.code == "grundsteuer")
    expected = Decimal("1121.48") * Decimal("13044") / Decimal("13764")
    assert abs(grund.year_cost - expected) < Decimal("0.01")

    share = result.tenant_lines[0].details[0]
    hinweise = [line for line in share.info if line["type"] == "hinweis"]
    assert len(hinweise) == 1
    assert "13044/13764" in hinweise[0]["label"]
    assert "1.121,48 €" in hinweise[0]["label"]


def test_anteil_factor_wiederkehrende_grundsteuer(session):
    """Wiederkehrende Grundsteuer mit Anteil: Jahresbetrag × Faktor."""
    prop, cat, _ = _objekt_mit_grundsteuer(session)
    inv = helpers.make_invoice(
        session, prop, cat, date(2025, 1, 1), date(2025, 12, 31), []
    )
    inv.kind = InvoiceKind.GRUNDSTEUER
    inv.valid_from = date(2025, 1, 1)
    inv.annual_amount = Decimal("1121.48")
    inv.anteil_zaehler = Decimal("13044")
    inv.anteil_nenner = Decimal("13764")
    session.commit()

    result = compute_settlement(session, prop.id, 2025)
    grund = next(cl for cl in result.category_lines if cl.code == "grundsteuer")
    expected = Decimal("1121.48") * Decimal("13044") / Decimal("13764")
    assert abs(grund.year_cost - expected) < Decimal("0.01")

    share = result.tenant_lines[0].details[0]
    hinweise = [line for line in share.info if line["type"] == "hinweis"]
    assert len(hinweise) == 1
    assert "13044/13764" in hinweise[0]["label"]
    assert "1.121,48 €" in hinweise[0]["label"]


def test_ohne_anteil_kein_hinweis(session):
    """Ohne Anteil wird der volle Betrag angerechnet und kein Hinweis erzeugt."""
    prop, cat, _ = _objekt_mit_grundsteuer(session)
    helpers.make_invoice(
        session, prop, cat, date(2025, 1, 1), date(2025, 12, 31),
        [(date(2025, 1, 1), date(2025, 12, 31), "1121.48")],
    )
    session.commit()

    result = compute_settlement(session, prop.id, 2025)
    grund = next(cl for cl in result.category_lines if cl.code == "grundsteuer")
    assert grund.year_cost == Decimal("1121.48")

    share = result.tenant_lines[0].details[0]
    assert all(line["type"] != "hinweis" for line in share.info)
