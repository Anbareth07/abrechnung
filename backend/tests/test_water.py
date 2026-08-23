from datetime import date
from decimal import Decimal

from app.models.enums import AllocationKey, MeterType
from app.services import engine as engine_mod
from tests import helpers


def _build_objekt1(session):
    prop = helpers.make_property(session, "Objekt 1")

    trink = helpers.make_category(session, prop, "trinkwasser", "Trinkwasser", AllocationKey.CONSUMPTION)
    schmutz = helpers.make_category(session, prop, "schmutzwasser", "Schmutzwasser", AllocationKey.CONSUMPTION)
    grund = helpers.make_category(session, prop, "grundsteuer", "Grundsteuer", AllocationKey.NF)

    helpers.make_config(session, prop, trink, AllocationKey.CONSUMPTION, 1)
    helpers.make_config(session, prop, schmutz, AllocationKey.CONSUMPTION, 2)
    helpers.make_config(session, prop, grund, AllocationKey.NF, 3)

    u1 = helpers.make_unit(session, prop, "Wohnung 1", "76.0", "4.0")
    u2 = helpers.make_unit(session, prop, "Wohnung 2", "65.0", "4.0")
    u3 = helpers.make_unit(session, prop, "Wohnung 3", "65.0", "4.0")

    helpers.make_tenant(session, u1, "Mieter A", date(2020, 1, 1), "150.00")
    helpers.make_tenant(session, u2, "Mieter B", date(2020, 1, 1), "150.00")
    helpers.make_tenant(session, u3, "Mieter C", date(2020, 1, 1), "150.00")

    g_n = helpers.make_meter(session, "Garten Nord", MeterType.GARDEN, prop=prop)
    g_s = helpers.make_meter(session, "Garten Süd", MeterType.GARDEN, prop=prop)
    w1 = helpers.make_meter(session, "Wohnung 1 Wasser", MeterType.APARTMENT_WATER, unit=u1)
    wm1 = helpers.make_meter(session, "Wohnung 1 WM", MeterType.WASHING_MACHINE, unit=u1)
    w2 = helpers.make_meter(session, "Wohnung 2 Wasser", MeterType.APARTMENT_WATER, unit=u2)
    wm2 = helpers.make_meter(session, "Wohnung 2 WM", MeterType.WASHING_MACHINE, unit=u2)
    w3 = helpers.make_meter(session, "Wohnung 3 Wasser", MeterType.APARTMENT_WATER, unit=u3)
    wm3 = helpers.make_meter(session, "Wohnung 3 WM", MeterType.WASHING_MACHINE, unit=u3)

    # Jahresanfangs-/Jahresendstände
    helpers.make_reading(session, g_n, date(2025, 12, 31), "100.0")
    helpers.make_reading(session, g_n, date(2026, 12, 31), "140.0")
    helpers.make_reading(session, g_s, date(2025, 12, 31), "50.0")
    helpers.make_reading(session, g_s, date(2026, 12, 31), "70.0")
    helpers.make_reading(session, w1, date(2025, 12, 31), "10.0")
    helpers.make_reading(session, w1, date(2026, 12, 31), "60.0")
    helpers.make_reading(session, wm1, date(2025, 12, 31), "2.0")
    helpers.make_reading(session, wm1, date(2026, 12, 31), "8.0")
    helpers.make_reading(session, w2, date(2025, 12, 31), "0.0")
    helpers.make_reading(session, w2, date(2026, 12, 31), "45.0")
    helpers.make_reading(session, wm2, date(2025, 12, 31), "0.0")
    helpers.make_reading(session, wm2, date(2026, 12, 31), "10.0")
    helpers.make_reading(session, w3, date(2025, 12, 31), "0.0")
    helpers.make_reading(session, w3, date(2026, 12, 31), "40.0")
    helpers.make_reading(session, wm3, date(2025, 12, 31), "0.0")
    helpers.make_reading(session, wm3, date(2026, 12, 31), "5.0")

    # Rechnungen: Trinkwasser zeitversetzt, Schmutzwasser & Grundsteuer kalenderjährig
    helpers.make_invoice(
        session, prop, trink, date(2025, 7, 1), date(2026, 6, 30),
        [(date(2025, 7, 1), date(2026, 6, 30), "1000.00")],
    )
    helpers.make_invoice(
        session, prop, schmutz, date(2026, 1, 1), date(2026, 12, 31),
        [(date(2026, 1, 1), date(2026, 12, 31), "500.00")],
    )
    helpers.make_invoice(
        session, prop, grund, date(2026, 1, 1), date(2026, 12, 31),
        [(date(2026, 1, 1), date(2026, 12, 31), "2180.00")],
    )

    session.commit()
    return prop


def test_water_calculation(session):
    prop = _build_objekt1(session)
    result = engine_mod.compute_settlement(session, prop.id, 2026)

    assert result.total_wf == Decimal("206.0")
    assert result.total_nf == Decimal("218.0")

    # Gartenverbrauch: Nord 40 + Süd 20 = 60
    assert result.water.garden_consumption == Decimal("60.0")

    # Gesamtverbrauch: (50+6)+(45+10)+(40+5)+60 = 216
    assert result.water.total_consumption == Decimal("216.0")

    # Wasser-Gesamtkosten: Trinkwasser 1000 * 181/365 + Schmutzwasser 500
    trink_pro_rata = Decimal("1000") * Decimal(181) / Decimal(365)
    water_total = trink_pro_rata + Decimal("500")
    expected_price = water_total / Decimal("216")
    assert result.water_price_per_m3 == expected_price

    mieter_a = next(ln for ln in result.tenant_lines if ln.name == "Mieter A")
    mieter_b = next(ln for ln in result.tenant_lines if ln.name == "Mieter B")
    mieter_c = next(ln for ln in result.tenant_lines if ln.name == "Mieter C")

    # Individueller Verbrauch ohne Zeitfaktor
    assert mieter_a.breakdown["WASSER_VERBRAUCH"] == engine_mod.money(Decimal("56") * expected_price)
    assert mieter_b.breakdown["WASSER_VERBRAUCH"] == engine_mod.money(Decimal("55") * expected_price)
    assert mieter_c.breakdown["WASSER_VERBRAUCH"] == engine_mod.money(Decimal("45") * expected_price)

    # Gartenwasser wird nach Wohnfläche umgelegt
    garden_cost = Decimal("60") * expected_price
    assert mieter_a.breakdown["WASSER_GARTEN"] == engine_mod.money(garden_cost * Decimal("76") / Decimal("206"))
    assert mieter_b.breakdown["WASSER_GARTEN"] == engine_mod.money(garden_cost * Decimal("65") / Decimal("206"))

    # Grundsteuer (NF): Mieter A 80/218 von 2180
    assert mieter_a.breakdown["grundsteuer"] == engine_mod.money(Decimal("2180") * Decimal("80") / Decimal("218"))


def test_water_individual_no_time_factor_for_partial_tenant(session):
    prop = _build_objekt1(session)
    # Mieter Mieter B zieht zum 01.07.2026 aus → Zeitfaktor nur für Flächenumlagen
    from app import models

    mieter_b = session.query(models.Tenant).filter_by(name="Mieter B").one()
    mieter_b.move_out = date(2026, 6, 30)
    session.commit()

    result = engine_mod.compute_settlement(session, prop.id, 2026)

    line = next(ln for ln in result.tenant_lines if ln.name == "Mieter B")
    # Miet-Tage: 01.01.–30.06. = 181 Tage
    assert line.tenant_days == 181

    # Individueller Verbrauch wird NICHT zeitanteilig gekürzt (Zähler misst realen Verbrauch).
    # Ohne Zählerstand zum Auszug (30.06.) fällt die Abrechnung auf den Jahresendstand zurück.
    trink_pro_rata = Decimal("1000") * Decimal(181) / Decimal(365)
    water_total = trink_pro_rata + Decimal("500")
    expected_price = water_total / Decimal("216")
    assert line.breakdown["WASSER_VERBRAUCH"] == engine_mod.money(Decimal("55") * expected_price)

    # Hinweis auf fehlenden Zählerstand zu Ein-/Auszug wird ausgegeben.
    assert any("Mieter B" in w for w in result.warnings)
