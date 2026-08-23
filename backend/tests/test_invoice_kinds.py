"""Tests für Rechnungsarten: wiederkehrende Grundsteuer & Wohneinheiten-Scope."""

from datetime import date
from decimal import Decimal

from app.models.enums import AllocationKey, InvoiceKind
from app.services import engine as engine_mod
from tests import helpers


def _recurring_invoice(session, prop, cat, valid_from: date, annual: str):
    """Grundsteuer-Rechnung (wiederkehrend): gültig ab + Jahresbetrag."""
    inv = helpers.make_invoice(
        session, prop, cat, valid_from, valid_from, items=[]
    )
    inv.kind = InvoiceKind.GRUNDSTEUER.value
    inv.valid_from = valid_from
    inv.annual_amount = Decimal(annual)
    session.commit()
    return inv


def test_grundsteuer_recurring_full_year(session):
    """Grundsteuer mit gültig ab vor dem Jahr → voller Jahresbetrag."""
    prop = helpers.make_property(session, "Testobjekt")
    grund = helpers.make_category(session, prop, "grundsteuer", "Grundsteuer", AllocationKey.WF)
    helpers.make_config(session, prop, grund, AllocationKey.WF, 1)

    u1 = helpers.make_unit(session, prop, "Wohnung 1", "50.0")
    u2 = helpers.make_unit(session, prop, "Wohnung 2", "50.0")
    helpers.make_tenant(session, u1, "Mieter A", date(2020, 1, 1), "100.00")
    helpers.make_tenant(session, u2, "Mieter B", date(2020, 1, 1), "100.00")

    _recurring_invoice(session, prop, grund, date(2020, 1, 1), "1200.00")

    result = engine_mod.compute_settlement(session, prop.id, 2026)
    line = next(cl for cl in result.category_lines if cl.code == "grundsteuer")
    assert line.year_cost == Decimal("1200.00")
    # 2 Einheiten à 50 von 100 → je 600
    assert result.tenant_lines[0].breakdown["grundsteuer"] == Decimal("600.00")
    assert result.tenant_lines[1].breakdown["grundsteuer"] == Decimal("600.00")


def test_grundsteuer_mid_year_start(session):
    """Grundsteuer mit gültig ab unterjährig → anteilig (gültige Tage/Jahr)."""
    prop = helpers.make_property(session, "Testobjekt")
    grund = helpers.make_category(session, prop, "grundsteuer", "Grundsteuer", AllocationKey.WF)
    helpers.make_config(session, prop, grund, AllocationKey.WF, 1)

    u1 = helpers.make_unit(session, prop, "Wohnung 1", "50.0")
    helpers.make_tenant(session, u1, "Mieter A", date(2020, 1, 1), "100.00")

    _recurring_invoice(session, prop, grund, date(2026, 7, 1), "1200.00")

    result = engine_mod.compute_settlement(session, prop.id, 2026)
    line = next(cl for cl in result.category_lines if cl.code == "grundsteuer")
    # 01.07.–31.12. = 184 Tage von 365
    expected = engine_mod.money(Decimal("1200") * Decimal(184) / Decimal(365))
    assert engine_mod.money(line.year_cost) == expected


def test_grundsteuer_bescheid_wechsel(session):
    """Neuer Bescheid mid-year: das Jahr wird an den Stichtagen aufgeteilt."""
    prop = helpers.make_property(session, "Testobjekt")
    grund = helpers.make_category(session, prop, "grundsteuer", "Grundsteuer", AllocationKey.WF)
    helpers.make_config(session, prop, grund, AllocationKey.WF, 1)

    u1 = helpers.make_unit(session, prop, "Wohnung 1", "50.0")
    helpers.make_tenant(session, u1, "Mieter A", date(2020, 1, 1), "100.00")

    _recurring_invoice(session, prop, grund, date(2026, 1, 1), "1200.00")
    _recurring_invoice(session, prop, grund, date(2026, 7, 1), "2400.00")

    result = engine_mod.compute_settlement(session, prop.id, 2026)
    line = next(cl for cl in result.category_lines if cl.code == "grundsteuer")
    # 01.01.–30.06. = 181 Tage mit 1200, 01.07.–31.12. = 184 Tage mit 2400
    expected = engine_mod.money(
        Decimal("1200") * Decimal(181) / Decimal(365)
        + Decimal("2400") * Decimal(184) / Decimal(365)
    )
    assert engine_mod.money(line.year_cost) == expected


def test_wohneinheit_scope_schornsteinfeger(session):
    """Schornsteinfeger auf eine Wohneinheit bezogen → nur diese Einheit zahlt."""
    prop = helpers.make_property(session, "Testobjekt")
    schorn = helpers.make_category(
        session, prop, "schornstein", "Schornsteinfeger", AllocationKey.NONE
    )
    helpers.make_config(session, prop, schorn, AllocationKey.NONE, 1)

    u1 = helpers.make_unit(session, prop, "Wohnung 1", "50.0")
    u2 = helpers.make_unit(session, prop, "Wohnung 2", "50.0")
    helpers.make_tenant(session, u1, "Mieter A", date(2020, 1, 1), "100.00")
    helpers.make_tenant(session, u2, "Mieter B", date(2020, 1, 1), "100.00")

    # Wohneinheitenbezogene Rechnung: nur für u1
    inv = helpers.make_invoice(
        session, prop, schorn, date(2026, 1, 1), date(2026, 12, 31),
        [(date(2026, 1, 1), date(2026, 12, 31), "120.00")],
    )
    inv.lease_unit_id = u1.id
    session.commit()

    result = engine_mod.compute_settlement(session, prop.id, 2026)

    # Kein objektweiter (geteilter) Anteil, da NONE
    line = next(cl for cl in result.category_lines if cl.code == "schornstein")
    assert line.year_cost == Decimal("0.00")

    a = next(ln for ln in result.tenant_lines if ln.name == "Mieter A")
    b = next(ln for ln in result.tenant_lines if ln.name == "Mieter B")
    assert a.breakdown.get("schornstein", Decimal("0")) == Decimal("120.00")
    assert b.breakdown.get("schornstein", Decimal("0")) == Decimal("0.00")
    assert a.total_costs == Decimal("120.00")
    assert b.total_costs == Decimal("0.00")


def test_wohneinheit_scope_without_config(session):
    """Wohneinheitenbezogene Kosten funktionieren auch ohne Umlage-Konfiguration.

    Die Kostenart entsteht bei der Rechnungseingabe automatisch (per Rechnungsart)
    und hat dann noch keine Konfiguration – die Engine muss den Code trotzdem kennen.
    """
    prop = helpers.make_property(session, "Testobjekt")
    # Keine make_config für diese Kostenart!
    schorn = helpers.make_category(
        session, prop, "schornsteinfeger", "Schornsteinfeger", AllocationKey.NONE
    )

    u1 = helpers.make_unit(session, prop, "Wohnung 1", "50.0")
    u2 = helpers.make_unit(session, prop, "Wohnung 2", "50.0")
    helpers.make_tenant(session, u1, "Mieter A", date(2020, 1, 1), "100.00")
    helpers.make_tenant(session, u2, "Mieter B", date(2020, 1, 1), "100.00")

    inv = helpers.make_invoice(
        session, prop, schorn, date(2026, 1, 1), date(2026, 12, 31),
        [(date(2026, 1, 1), date(2026, 12, 31), "120.00")],
    )
    inv.lease_unit_id = u1.id
    session.commit()

    result = engine_mod.compute_settlement(session, prop.id, 2026)

    a = next(ln for ln in result.tenant_lines if ln.name == "Mieter A")
    b = next(ln for ln in result.tenant_lines if ln.name == "Mieter B")
    assert a.breakdown.get("schornsteinfeger", Decimal("0")) == Decimal("120.00")
    assert b.breakdown.get("schornsteinfeger", Decimal("0")) == Decimal("0.00")
    assert a.total_costs == Decimal("120.00")
