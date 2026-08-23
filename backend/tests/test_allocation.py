from datetime import date
from decimal import Decimal

from app.models.enums import AllocationKey
from app.services import engine as engine_mod
from tests import helpers


def _build_two_units(session):
    prop = helpers.make_property(session, "Testobjekt")

    grund = helpers.make_category(session, prop, "grundsteuer", "Grundsteuer", AllocationKey.NF)
    pflege = helpers.make_category(session, prop, "gartenpflege", "Gartenpflege", AllocationKey.WF)
    helpers.make_config(session, prop, grund, AllocationKey.NF, 1)
    helpers.make_config(session, prop, pflege, AllocationKey.WF, 2)

    u1 = helpers.make_unit(session, prop, "Wohnung 1", "50.0", "10.0")
    u2 = helpers.make_unit(session, prop, "Wohnung 2", "50.0", "10.0")

    helpers.make_tenant(session, u1, "Volljahr", date(2020, 1, 1), "100.00")
    # Halbes Jahr: Einzug 01.07.2026
    helpers.make_tenant(session, u2, "Halbjahr", date(2026, 7, 1), "100.00")

    helpers.make_invoice(
        session, prop, grund, date(2026, 1, 1), date(2026, 12, 31),
        [(date(2026, 1, 1), date(2026, 12, 31), "1200.00")],
    )
    helpers.make_invoice(
        session, prop, pflege, date(2026, 1, 1), date(2026, 12, 31),
        [(date(2026, 1, 1), date(2026, 12, 31), "600.00")],
    )

    session.commit()
    return prop


def test_area_allocation_and_time_factor(session):
    prop = _build_two_units(session)
    result = engine_mod.compute_settlement(session, prop.id, 2026)

    assert result.total_wf == Decimal("100.0")
    assert result.total_nf == Decimal("120.0")

    volljahr = next(ln for ln in result.tenant_lines if ln.name == "Volljahr")
    halbjahr = next(ln for ln in result.tenant_lines if ln.name == "Halbjahr")

    # Volljahr: 365 Tage, Faktor 1
    assert volljahr.tenant_days == 365
    assert volljahr.time_factor == Decimal(1)

    # Halbjahr: 01.07.–31.12. = 184 Tage
    assert halbjahr.tenant_days == 184
    factor = Decimal(184) / Decimal(365)
    assert halbjahr.time_factor == factor

    # Grundsteuer (NF 60 je Einheit von 120): Volljahr 600, Halbjahr 600*factor
    assert volljahr.breakdown["grundsteuer"] == Decimal("600.00")
    assert halbjahr.breakdown["grundsteuer"] == Decimal("600") * factor

    # Gartenpflege (WF 50 je Einheit von 100): Volljahr 300, Halbjahr 300*factor
    assert volljahr.breakdown["gartenpflege"] == Decimal("300.00")
    assert halbjahr.breakdown["gartenpflege"] == Decimal("300") * factor

    # Saldo: Kosten − Vorauszahlung × (Tage/365 × 12)
    expected_total = Decimal("600") + Decimal("300")
    assert volljahr.total_costs == expected_total
    assert volljahr.advance_total == Decimal("1200.00")
    assert volljahr.saldo == expected_total - Decimal("1200")

    halb_total = Decimal("600") * factor + Decimal("300") * factor
    halb_advance = Decimal("600")  # 01.07.–31.12. = 6 Monate × 100
    assert halbjahr.advance_total == halb_advance
    assert halbjahr.saldo == halb_total - halb_advance


def test_wohnung_allocation_unit_scoped(session):
    """Umlageschlüssel 'Wohnung': eine Rechnung gilt exakt für eine Wohnung.

    Objektweite Rechnungen werden NICHT auf alle Wohnungen aufgeteilt; nur
    wohnungbezogene Rechnungen (lease_unit_id) zählen – exakt für diese Wohnung.
    """
    prop = helpers.make_property(session, "Testobjekt")
    wohn = helpers.make_category(session, prop, "wohnungskosten", "Wohnungskosten", AllocationKey.WOHNUNG)
    helpers.make_config(session, prop, wohn, AllocationKey.WOHNUNG, 1)

    u1 = helpers.make_unit(session, prop, "Wohnung 1", "80.0", "0.0")
    u2 = helpers.make_unit(session, prop, "Wohnung 2", "40.0", "0.0")
    helpers.make_tenant(session, u1, "Volljahr", date(2020, 1, 1), "100.00")
    helpers.make_tenant(session, u2, "Halbjahr", date(2026, 7, 1), "100.00")

    # Objektweite Rechnung (ohne Wohnung) → wird NICHT aufgeteilt (Anteil 0)
    helpers.make_invoice(
        session, prop, wohn, date(2026, 1, 1), date(2026, 12, 31),
        [(date(2026, 1, 1), date(2026, 12, 31), "1200.00")],
    )
    session.commit()
    result = engine_mod.compute_settlement(session, prop.id, 2026)
    volljahr = next(ln for ln in result.tenant_lines if ln.name == "Volljahr")
    assert volljahr.breakdown.get("wohnungskosten", Decimal("0")) == Decimal("0")

    # Wohnungbezogene Rechnung auf u1 → gilt exakt für Wohnung 1 (Volljahr)
    inv = helpers.make_invoice(
        session, prop, wohn, date(2026, 1, 1), date(2026, 12, 31),
        [(date(2026, 1, 1), date(2026, 12, 31), "1200.00")],
    )
    inv.lease_unit_id = u1.id
    session.commit()
    result = engine_mod.compute_settlement(session, prop.id, 2026)
    volljahr = next(ln for ln in result.tenant_lines if ln.name == "Volljahr")
    halbjahr = next(ln for ln in result.tenant_lines if ln.name == "Halbjahr")
    assert volljahr.breakdown["wohnungskosten"] == Decimal("1200.00")
    assert halbjahr.breakdown.get("wohnungskosten", Decimal("0")) == Decimal("0")


def test_move_out_handling(session):
    prop = _build_two_units(session)
    from app import models

    halbjahr = session.query(models.Tenant).filter_by(name="Halbjahr").one()
    halbjahr.move_out = date(2026, 6, 30)  # ausgezogen vor Einzug? → kein aktiver Mieter
    session.commit()

    result = engine_mod.compute_settlement(session, prop.id, 2026)
    names = [ln.name for ln in result.tenant_lines]
    assert "Halbjahr" not in names
    assert "Volljahr" in names


def test_advance_periods_pro_rata(session):
    """Vorauszahlung mit Zeiträumen: ab 01.07.2026 gelten 180 € statt 100 €."""
    from app import models

    prop = _build_two_units(session)
    voll = session.query(models.Tenant).filter_by(name="Volljahr").one()
    session.add(models.AdvancePayment(tenant_id=voll.id, valid_from=date(2020, 1, 1), amount=Decimal("100")))
    session.add(models.AdvancePayment(tenant_id=voll.id, valid_from=date(2026, 7, 1), amount=Decimal("180")))
    session.commit()

    result = engine_mod.compute_settlement(session, prop.id, 2026)
    line = next(ln for ln in result.tenant_lines if ln.name == "Volljahr")

    # 2026: 01.01–30.06 = 6 Monate à 100 €, 01.07–31.12 = 6 Monate à 180 €
    expected = Decimal("100") * 6 + Decimal("180") * 6
    assert line.advance_total == engine_mod.money(expected)

    # Saldo berücksichtigt die neue Vorauszahlung
    assert line.saldo == engine_mod.money(line.total_costs - line.advance_total)
