from datetime import date

from app import models
from app.models.enums import AllocationKey, MeterType
from app.services.completeness import check_completeness
from tests import helpers


def test_completeness_no_invoice_flag_and_strom_target(session):
    """'Keine Rechnung'-Markierung und Strom-Ziel-Kostenart werden nicht als fehlend gemeldet."""
    prop = helpers.make_property(session, "Objekt 3")

    legion = helpers.make_category(session, prop, "legionellen", "Legionellen", AllocationKey.WF)
    haus = helpers.make_category(session, prop, "hausbeleuchtung", "Hausbeleuchtung", AllocationKey.WF)
    helpers.make_config(session, prop, legion, AllocationKey.WF, 1)
    helpers.make_config(session, prop, haus, AllocationKey.WF, 2)

    # Hausbeleuchtung ist als Strom-Ziel verknüpft → wird über das Strom-Modul abgedeckt
    prop.strom_allocation_category_id = haus.id
    # Legionellen: bewusst keine Rechnung in 2026
    session.add(
        models.CategoryNoInvoice(
            property_id=prop.id, cost_category_id=legion.id, year=2026
        )
    )

    session.commit()

    missing = check_completeness(session, prop.id, 2026)
    labels = {m.label for m in missing}
    assert not any("Hausbeleuchtung" in l for l in labels)
    assert not any("Legionellen" in l for l in labels)


def test_completeness_reports_missing_everything(session):
    prop = helpers.make_property(session, "Objekt 1")

    trink = helpers.make_category(session, prop, "trinkwasser", "Trinkwasser", AllocationKey.CONSUMPTION)
    grund = helpers.make_category(session, prop, "grundsteuer", "Grundsteuer", AllocationKey.NF)
    abfall = helpers.make_category(session, prop, "abfall", "Abfall", AllocationKey.NONE)

    helpers.make_config(session, prop, trink, AllocationKey.CONSUMPTION, 1)
    helpers.make_config(session, prop, grund, AllocationKey.NF, 2)
    helpers.make_config(session, prop, abfall, AllocationKey.NONE, 3)

    u1 = helpers.make_unit(session, prop, "Wohnung 1", "50.0", "0.0")
    helpers.make_meter(session, "Garten Nord", MeterType.GARDEN, prop=prop)
    helpers.make_meter(session, "Wohnung 1 Wasser", MeterType.APARTMENT_WATER, unit=u1)

    session.commit()

    missing = check_completeness(session, prop.id, 2026)

    labels = {m.label for m in missing}
    # Rechnungen fehlen für trinkwasser & grundsteuer, nicht für abfall (NONE)
    assert "Rechnung fehlt: Trinkwasser" in labels
    assert "Rechnung fehlt: Grundsteuer" in labels
    assert not any("Abfall" in l for l in labels)

    # Zählerstände fehlen an beiden Jahresgrenzen für beide Zähler
    assert "Zählerstand Jahresanfang fehlt: Garten Nord" in labels
    assert "Zählerstand Jahresende fehlt: Garten Nord" in labels
    assert "Zählerstand Jahresanfang fehlt: Wohnung 1 Wasser" in labels


def test_completeness_ok_when_data_present(session):
    prop = helpers.make_property(session, "Objekt 2")

    grund = helpers.make_category(session, prop, "grundsteuer", "Grundsteuer", AllocationKey.WF)
    helpers.make_config(session, prop, grund, AllocationKey.WF, 1)

    helpers.make_invoice(
        session, prop, grund, date(2026, 1, 1), date(2026, 12, 31),
        [(date(2026, 1, 1), date(2026, 12, 31), "1000.00")],
    )

    session.commit()

    missing = check_completeness(session, prop.id, 2026)
    assert missing == []
