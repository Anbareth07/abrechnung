from datetime import date

from app.models.enums import AllocationKey, MeterType
from app.services.completeness import check_completeness
from tests import helpers


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
