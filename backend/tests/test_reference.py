"""Validierung gegen die Referenz-Abrechnung Objekt 1 2013 (Excel).

Prüft die Wasser- und Flächenlogik exakt gegen die echten Alt-Abrechnungszahlen.
"""

from datetime import date
from decimal import Decimal

from app.models.enums import AllocationKey, MeterType
from app.services import engine as engine_mod
from tests import helpers


def _build_objekt1_2013(session):
    prop = helpers.make_property(session, "Objekt 1")

    trink = helpers.make_category(session, prop, "trinkwasser", "Trinkwasser", AllocationKey.CONSUMPTION)
    schmutz = helpers.make_category(session, prop, "schmutzwasser", "Schmutzwasser", AllocationKey.CONSUMPTION)
    grund = helpers.make_category(session, prop, "grundsteuer", "Grundsteuer", AllocationKey.NF)
    gebaeude = helpers.make_category(session, prop, "gebaeudeversicherung", "Gebäudebrand-/Elementarversicherung", AllocationKey.NF)
    haft = helpers.make_category(session, prop, "haftpflicht", "Haftpflichtversicherung", AllocationKey.NF)
    nieder = helpers.make_category(session, prop, "niederschlagswasser", "Niederschlagswassergebühr", AllocationKey.NF)
    gartenpflege = helpers.make_category(session, prop, "gartenpflege", "Gartenpflege", AllocationKey.WF)
    hauslicht = helpers.make_category(session, prop, "hausbeleuchtung", "Hausbeleuchtung", AllocationKey.WF)
    schornstein = helpers.make_category(session, prop, "schornstein", "Schornstein/Wartung", AllocationKey.WF)

    for i, (cat, key) in enumerate(
        [
            (trink, AllocationKey.CONSUMPTION),
            (schmutz, AllocationKey.CONSUMPTION),
            (grund, AllocationKey.NF),
            (gebaeude, AllocationKey.NF),
            (haft, AllocationKey.NF),
            (nieder, AllocationKey.NF),
            (gartenpflege, AllocationKey.WF),
            (hauslicht, AllocationKey.WF),
            (schornstein, AllocationKey.WF),
        ]
    ):
        helpers.make_config(session, prop, cat, key, i + 1)

    # 2013: Mieter A 76, Mieter D 77, Mieter E 53 → WF 206; + 12 m² separates Zimmer → NF 218
    u_mieter_a = helpers.make_unit(session, prop, "Wohnung Mieter A", "76.0", "0.0")
    u_mieter_d = helpers.make_unit(session, prop, "Wohnung Mieter D", "77.0", "0.0")
    u_mieter_e = helpers.make_unit(session, prop, "Wohnung Mieter E", "53.0", "0.0")
    helpers.make_unit(session, prop, "Separates Zimmer", "0.0", "12.0")

    helpers.make_tenant(session, u_mieter_a, "Mieter A", date(2012, 1, 1), "0")
    helpers.make_tenant(session, u_mieter_d, "Mieter D", date(2012, 1, 1), "0")
    helpers.make_tenant(session, u_mieter_e, "Mieter E", date(2012, 1, 1), "0")

    def unit_meter(name, mtype, lease_unit, start, end):
        m = helpers.make_meter(session, name, mtype, unit=lease_unit)
        helpers.make_reading(session, m, date(2012, 12, 31), start)
        helpers.make_reading(session, m, date(2013, 12, 31), end)
        return m

    def prop_meter(name, mtype, start, end):
        m = helpers.make_meter(session, name, mtype, prop=prop)
        helpers.make_reading(session, m, date(2012, 12, 31), start)
        helpers.make_reading(session, m, date(2013, 12, 31), end)
        return m

    prop_meter("Garten Nord", MeterType.GARDEN, "47", "48")
    prop_meter("Garten Süd", MeterType.GARDEN, "88", "89")
    unit_meter("Mieter A Wasser", MeterType.APARTMENT_WATER, u_mieter_a, "1128", "1163")
    unit_meter("Mieter A WM", MeterType.WASHING_MACHINE, u_mieter_a, "167", "169")
    unit_meter("Mieter D Wasser", MeterType.APARTMENT_WATER, u_mieter_d, "1727", "1767")
    unit_meter("Mieter D WM", MeterType.WASHING_MACHINE, u_mieter_d, "584", "604")
    unit_meter("Mieter E Wasser", MeterType.APARTMENT_WATER, u_mieter_e, "715", "746")
    unit_meter("Mieter E WM", MeterType.WASHING_MACHINE, u_mieter_e, "129", "137")

    def invoice(cat, amount):
        helpers.make_invoice(
            session, prop, cat, date(2013, 1, 1), date(2013, 12, 31),
            [(date(2013, 1, 1), date(2013, 12, 31), amount)],
        )

    invoice(trink, "309.93")
    invoice(schmutz, "225.40")
    invoice(grund, "155.45")
    invoice(gebaeude, "272.05")
    invoice(haft, "71.91")
    invoice(nieder, "57.63")
    invoice(gartenpflege, "103.00")
    invoice(hauslicht, "104.35")
    invoice(schornstein, "29.49")

    session.commit()
    return prop


def test_reference_2013_water(session):
    prop = _build_objekt1_2013(session)
    result = engine_mod.compute_settlement(session, prop.id, 2013)

    assert result.total_wf == Decimal("206.0")
    assert result.total_nf == Decimal("218.0")

    # Gesamtverbrauch: 35+2 + 40+20 + 31+8 = 136 (ohne Garten)
    assert result.water.total_consumption == Decimal("136.0")
    assert result.water.garden_consumption == Decimal("0")

    # cbm-Preis = (309,93 + 225,40) / 136
    expected_price = Decimal("535.33") / Decimal("136")
    assert result.water_price_per_m3 == expected_price

    mieter_a = next(ln for ln in result.tenant_lines if ln.name == "Mieter A")
    mieter_d = next(ln for ln in result.tenant_lines if ln.name == "Mieter D")
    mieter_e = next(ln for ln in result.tenant_lines if ln.name == "Mieter E")

    # Individueller Verbrauch ohne Zeitfaktor
    assert mieter_a.breakdown["WASSER_VERBRAUCH"] == Decimal("37") * expected_price
    assert mieter_d.breakdown["WASSER_VERBRAUCH"] == Decimal("60") * expected_price
    assert mieter_e.breakdown["WASSER_VERBRAUCH"] == Decimal("39") * expected_price

    # Keine Gartenwasser-Zeile mehr
    assert "WASSER_GARTEN" not in mieter_a.breakdown

    # Flächenumlagen: Mieter A NF-Anteil = 76/218, WF-Anteil = 76/206
    assert mieter_a.breakdown["grundsteuer"] == Decimal("155.45") * (Decimal("76") / Decimal("218"))
    assert mieter_a.breakdown["gartenpflege"] == Decimal("103.00") * (Decimal("76") / Decimal("206"))
    assert mieter_a.breakdown["gebaeudeversicherung"] == Decimal("272.05") * (Decimal("76") / Decimal("218"))

    # Keine Restsumme, da Verbrauch exakt auf die Mieter + Garten aufgeht
    assert result.unallocated_water == Decimal("0")
