"""Tests für das Wasser-Modul (Plan B): Tarife, Zählerstände, Berechnung."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.db import get_db
from app.main import app
from app.models import Base
from app.models.enums import AllocationKey, MeterType
from app.services import engine as engine_mod
from app.services import wasser as wasser_service
from tests import helpers


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _objekt(client):
    return client.post("/properties", json={"name": "Testobjekt", "street": ""}).json()


def test_wasser_preis_luecken_verboten(client):
    p = _objekt(client)
    r = client.post(
        "/wasser/prices",
        json={"property_id": p["id"], "kind": "TRINKWASSER", "valid_from": "2025-01-01", "valid_to": "2025-06-30", "amount": "2.00"},
    )
    assert r.status_code == 201

    # Lücke → 422
    r = client.post(
        "/wasser/prices",
        json={"property_id": p["id"], "kind": "TRINKWASSER", "valid_from": "2025-10-01", "valid_to": "2025-12-31", "amount": "2.10"},
    )
    assert r.status_code == 422

    # lückenlos → 201
    r = client.post(
        "/wasser/prices",
        json={"property_id": p["id"], "kind": "TRINKWASSER", "valid_from": "2025-07-01", "valid_to": "2025-12-31", "amount": "2.10"},
    )
    assert r.status_code == 201

    # Überlappung → 422
    r = client.post(
        "/wasser/prices",
        json={"property_id": p["id"], "kind": "TRINKWASSER", "valid_from": "2025-01-01", "valid_to": "2025-03-31", "amount": "1.90"},
    )
    assert r.status_code == 422


def test_wasser_berechnung_verbrauch_und_kosten(client):
    p = _objekt(client)
    # Versiegelte Fläche (m²) für Niederschlagswasser (€/m²)
    client.patch(f"/properties/{p['id']}", json={"wasser_versiegelte_flaeche": "100"})

    client.post("/wasser/readings", json={"property_id": p["id"], "reading_date": "2025-01-01", "value": "1000"})
    client.post("/wasser/readings", json={"property_id": p["id"], "reading_date": "2025-12-31", "value": "2000"})

    client.post("/wasser/prices", json={"property_id": p["id"], "kind": "TRINKWASSER", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "2.00", "vat_rate": "19"})
    client.post("/wasser/prices", json={"property_id": p["id"], "kind": "SCHMUTZWASSER", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "1.50", "vat_rate": "19"})
    client.post("/wasser/prices", json={"property_id": p["id"], "kind": "NIEDERSCHLAGSWASSER", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "0.50", "vat_rate": "19"})
    client.post("/wasser/prices", json={"property_id": p["id"], "kind": "GRUNDGEBUEHR", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "120.00", "vat_rate": "19"})

    r = client.get(f"/wasser/{p['id']}/berechnung", params={"von": "2025-01-01", "bis": "2025-12-31"})
    assert r.status_code == 200
    data = r.json()
    assert data["verbrauch"] == pytest.approx(1000.0)
    assert data["hauptzaehler"]["consumption"] == pytest.approx(1000.0)
    assert data["versiegelte_flaeche"] == pytest.approx(100.0)

    by_art = {x["art"]: x for x in data["positionen"]}
    assert by_art["TRINKWASSER"]["netto"] == pytest.approx(2000.0)
    assert by_art["TRINKWASSER"]["einheit"] == "m³"
    assert by_art["SCHMUTZWASSER"]["netto"] == pytest.approx(1500.0)
    # Niederschlagswasser: 100 m² × 0,50 €/m² (versiegelte Fläche, NICHT Verbrauch)
    assert by_art["NIEDERSCHLAGSWASSER"]["netto"] == pytest.approx(50.0)
    assert by_art["NIEDERSCHLAGSWASSER"]["menge"] == pytest.approx(100.0)
    assert by_art["NIEDERSCHLAGSWASSER"]["einheit"] == "m²"
    assert by_art["GRUNDGEBUEHR"]["netto"] == pytest.approx(120.0)

    # Summe brutto: (2000+1500+50+120) × 1,19
    assert data["summen"]["netto"] == pytest.approx(3670.0)
    assert data["summen"]["brutto"] == pytest.approx(3670.0 * 1.19)


def test_wasser_mwst_standard_je_art(client):
    p = _objekt(client)
    # Ohne explizite MwSt → artabhängiger Standard
    r = client.post("/wasser/prices", json={"property_id": p["id"], "kind": "TRINKWASSER", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "2.00"})
    assert r.status_code == 201
    assert float(r.json()["vat_rate"]) == pytest.approx(7.0)

    r = client.post("/wasser/prices", json={"property_id": p["id"], "kind": "SCHMUTZWASSER", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "1.50"})
    assert float(r.json()["vat_rate"]) == pytest.approx(0.0)

    r = client.post("/wasser/prices", json={"property_id": p["id"], "kind": "NIEDERSCHLAGSWASSER", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "0.50"})
    assert float(r.json()["vat_rate"]) == pytest.approx(0.0)

    r = client.post("/wasser/prices", json={"property_id": p["id"], "kind": "GRUNDGEBUEHR", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "120.00"})
    assert float(r.json()["vat_rate"]) == pytest.approx(7.0)


def test_wasser_ohne_zaehler_verbrauch_null(client):
    p = _objekt(client)
    client.post("/wasser/prices", json={"property_id": p["id"], "kind": "TRINKWASSER", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "2.00", "vat_rate": "19"})
    r = client.get(f"/wasser/{p['id']}/berechnung", params={"von": "2025-01-01", "bis": "2025-12-31"})
    assert r.status_code == 200
    data = r.json()
    assert data["verbrauch"] == pytest.approx(0.0)
    assert data["hauptzaehler"] is None
    assert data["summen"]["netto"] == pytest.approx(0.0)
    assert data["summen"]["brutto"] == pytest.approx(0.0)


def test_wasser_niederschlag_und_grundgebuehr_nach_tagen(client):
    """Niederschlagswasser (€/m²/Jahr) und Grundgebühr (€/Jahr) laufen nach Tagen."""
    p = _objekt(client)
    client.patch(f"/properties/{p['id']}", json={"wasser_versiegelte_flaeche": "100"})
    client.post("/wasser/prices", json={"property_id": p["id"], "kind": "NIEDERSCHLAGSWASSER", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "0.50", "vat_rate": "0"})
    client.post("/wasser/prices", json={"property_id": p["id"], "kind": "GRUNDGEBUEHR", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "120.00", "vat_rate": "7"})

    # Halbes Jahr: 01.07.–31.12.2025 = 184 von 365 Tagen
    r = client.get(f"/wasser/{p['id']}/berechnung", params={"von": "2025-07-01", "bis": "2025-12-31"})
    assert r.status_code == 200
    data = r.json()
    by_art = {x["art"]: x for x in data["positionen"]}
    factor = Decimal(184) / Decimal(365)

    assert by_art["NIEDERSCHLAGSWASSER"]["menge"] == pytest.approx(100.0)
    assert by_art["NIEDERSCHLAGSWASSER"]["netto"] == pytest.approx(
        float(Decimal("0.50") * Decimal(100) * factor)
    )
    assert by_art["NIEDERSCHLAGSWASSER"]["satz_einheit"] == "€/m²/Jahr"
    assert by_art["GRUNDGEBUEHR"]["netto"] == pytest.approx(float(Decimal("120") * factor))
    assert by_art["GRUNDGEBUEHR"]["satz_einheit"] == "€/Jahr"


def test_wasser_in_abrechnung_plan_b(session):
    """Wasser-Kosten (Plan B) fließen in die Abrechnung: Trink/Schmutz nach
    Hauptzähler-Verbrauch, Grundgebühr nach Tagen, Niederschlagswasser €/m²/Jahr
    nach Tagen; Verteilung über den Umlageschlüssel der Kostenstelle."""
    prop = helpers.make_property(session, "Testobjekt")
    trink = helpers.make_category(session, prop, "trink", "Trinkwassergebühr", AllocationKey.WF)
    schmutz = helpers.make_category(session, prop, "schmutz", "Schmutzwassergebühr", AllocationKey.WF)
    niederschlag = helpers.make_category(session, prop, "niederschlag", "Niederschlagswassergebühr", AllocationKey.NF)
    helpers.make_config(session, prop, trink, AllocationKey.WF, 1)
    helpers.make_config(session, prop, schmutz, AllocationKey.WF, 2)
    helpers.make_config(session, prop, niederschlag, AllocationKey.NF, 3)

    prop.wasser_trinkwasser_category_id = trink.id
    prop.wasser_schmutzwasser_category_id = schmutz.id
    prop.wasser_niederschlag_category_id = niederschlag.id
    prop.wasser_versiegelte_flaeche = Decimal("100")
    session.add(prop)
    session.commit()

    u1 = helpers.make_unit(session, prop, "Wohnung 1", "50.0", "10.0")
    u2 = helpers.make_unit(session, prop, "Wohnung 2", "50.0", "10.0")
    helpers.make_tenant(session, u1, "Mieter A", date(2020, 1, 1), "100.00")
    helpers.make_tenant(session, u2, "Mieter B", date(2020, 1, 1), "100.00")

    session.add(models.WasserPrice(property_id=prop.id, kind="TRINKWASSER", valid_from=date(2025, 1, 1), valid_to=date(2025, 12, 31), amount=Decimal("2.00"), vat_rate=Decimal("7.00")))
    session.add(models.WasserPrice(property_id=prop.id, kind="SCHMUTZWASSER", valid_from=date(2025, 1, 1), valid_to=date(2025, 12, 31), amount=Decimal("1.50"), vat_rate=Decimal("0.00")))
    session.add(models.WasserPrice(property_id=prop.id, kind="NIEDERSCHLAGSWASSER", valid_from=date(2025, 1, 1), valid_to=date(2025, 12, 31), amount=Decimal("0.50"), vat_rate=Decimal("0.00")))
    session.add(models.WasserPrice(property_id=prop.id, kind="GRUNDGEBUEHR", valid_from=date(2025, 1, 1), valid_to=date(2025, 12, 31), amount=Decimal("120.00"), vat_rate=Decimal("7.00")))
    session.add(models.WasserReading(property_id=prop.id, reading_date=date(2025, 1, 1), value=Decimal("1000")))
    session.add(models.WasserReading(property_id=prop.id, reading_date=date(2025, 12, 31), value=Decimal("2000")))
    session.commit()

    result = engine_mod.compute_settlement(session, prop.id, 2025)

    by_code = {cl.code: cl for cl in result.category_lines}
    # Trinkwasser: 2000 € (7 % MwSt → 2140) + Grundgebühr 120 € (7 % → 128,40) = 2268,40
    assert by_code["trink"].year_cost == Decimal("2268.40")
    assert by_code["schmutz"].year_cost == Decimal("1500.00")
    # Niederschlagswasser: 100 m² × 0,50 €/m²/Jahr (Volljahr) = 50,00
    assert by_code["niederschlag"].year_cost == Decimal("50.00")

    mieter_a = next(ln for ln in result.tenant_lines if ln.name == "Mieter A")
    # Verteilung über Umlageschlüssel: WF 50/100, NF 10/20
    assert mieter_a.breakdown["trink"] == Decimal("2268.40") / Decimal(2)
    assert mieter_a.breakdown["schmutz"] == Decimal("1500.00") / Decimal(2)
    assert mieter_a.breakdown["niederschlag"] == Decimal("50.00") / Decimal(2)


def _plan_a_setup(session, with_grundgebuehr=True):
    """Objekt mit zwei Wohnungen + je 2 Zähler (Wohnung + Waschmaschine).
    Wohnung 1: 56 m³ (50+6), Wohnung 2: 55 m³ (45+10) → Summe 111 m³."""
    prop = helpers.make_property(session, "Testobjekt")
    trink = helpers.make_category(session, prop, "trink", "Trinkwassergebühr", AllocationKey.CONSUMPTION)
    schmutz = helpers.make_category(session, prop, "schmutz", "Schmutzwassergebühr", AllocationKey.CONSUMPTION)
    helpers.make_config(session, prop, trink, AllocationKey.CONSUMPTION, 1)
    helpers.make_config(session, prop, schmutz, AllocationKey.CONSUMPTION, 2)
    prop.wasser_trinkwasser_category_id = trink.id
    prop.wasser_schmutzwasser_category_id = schmutz.id
    session.add(prop)
    session.commit()

    u1 = helpers.make_unit(session, prop, "Wohnung 1", "50.0", "0.0")
    u2 = helpers.make_unit(session, prop, "Wohnung 2", "50.0", "0.0")

    w1 = helpers.make_meter(session, "Wohnung 1 Wasser", MeterType.APARTMENT_WATER, unit=u1)
    wm1 = helpers.make_meter(session, "Wohnung 1 WM", MeterType.WASHING_MACHINE, unit=u1)
    w2 = helpers.make_meter(session, "Wohnung 2 Wasser", MeterType.APARTMENT_WATER, unit=u2)
    wm2 = helpers.make_meter(session, "Wohnung 2 WM", MeterType.WASHING_MACHINE, unit=u2)
    helpers.make_reading(session, w1, date(2025, 1, 1), "100.0")
    helpers.make_reading(session, w1, date(2025, 12, 31), "150.0")
    helpers.make_reading(session, wm1, date(2025, 1, 1), "10.0")
    helpers.make_reading(session, wm1, date(2025, 12, 31), "16.0")
    helpers.make_reading(session, w2, date(2025, 1, 1), "0.0")
    helpers.make_reading(session, w2, date(2025, 12, 31), "45.0")
    helpers.make_reading(session, wm2, date(2025, 1, 1), "0.0")
    helpers.make_reading(session, wm2, date(2025, 12, 31), "10.0")

    session.add(models.WasserPrice(property_id=prop.id, kind="TRINKWASSER", valid_from=date(2025, 1, 1), valid_to=date(2025, 12, 31), amount=Decimal("2.00"), vat_rate=Decimal("7.00")))
    session.add(models.WasserPrice(property_id=prop.id, kind="SCHMUTZWASSER", valid_from=date(2025, 1, 1), valid_to=date(2025, 12, 31), amount=Decimal("1.50"), vat_rate=Decimal("0.00")))
    if with_grundgebuehr:
        session.add(models.WasserPrice(property_id=prop.id, kind="GRUNDGEBUEHR", valid_from=date(2025, 1, 1), valid_to=date(2025, 12, 31), amount=Decimal("120.00"), vat_rate=Decimal("7.00")))
    session.commit()
    return prop, u1, u2


def test_wasser_plan_a_berechnung_wohnungsverbrauch(session):
    """Plan A: Berechnung nutzt die Summe der Wohnungszähler statt Hauptzähler."""
    prop, _u1, _u2 = _plan_a_setup(session)
    res = wasser_service.berechnung(session, prop.id, date(2025, 1, 1), date(2025, 12, 31))
    assert res["plan"] == "A"
    assert res["hauptzaehler"] is None
    assert res["verbrauch"] == pytest.approx(111.0)
    trink = next(x for x in res["positionen"] if x["art"] == "TRINKWASSER")
    assert trink["netto"] == pytest.approx(222.0)


def test_waschmaschinen_abschaltbar_plan_a(session):
    """Waschmaschinen-Zähler abschaltbar → nur Wohnungs-Wasserzähler zählen (Plan A)."""
    prop, _u1, _u2 = _plan_a_setup(session)

    res = wasser_service.berechnung(session, prop.id, date(2025, 1, 1), date(2025, 12, 31))
    assert res["plan"] == "A"
    # aktiv: Wohnung 1 = 56 (50+6), Wohnung 2 = 55 (45+10) → 111
    assert res["verbrauch"] == pytest.approx(111.0)

    prop.wasser_waschmaschinen_aktiv = False
    session.add(prop)
    session.commit()
    res = wasser_service.berechnung(session, prop.id, date(2025, 1, 1), date(2025, 12, 31))
    # deaktiviert: nur Wohnungs-Wasserzähler → 50 + 45 = 95
    assert res["verbrauch"] == pytest.approx(95.0)


def test_wasser_plan_a_in_abrechnung(session):
    """Plan A: Trink-/Schmutzwasser werden nach Verbrauchsanteil je Wohnung verteilt."""
    prop, u1, u2 = _plan_a_setup(session)
    helpers.make_tenant(session, u1, "Mieter A", date(2020, 1, 1), "100.00")
    helpers.make_tenant(session, u2, "Mieter B", date(2020, 1, 1), "100.00")
    session.commit()

    result = engine_mod.compute_settlement(session, prop.id, 2025)

    by_code = {cl.code: cl for cl in result.category_lines}
    # Trink: 111×2=222 netto +7 % → 237,54; Grundgebühr 120+7 % → 128,40; zusammen 365,94
    assert by_code["trink"].year_cost == Decimal("365.94")
    # Schmutz: 111×1,50 = 166,50 (0 %)
    assert by_code["schmutz"].year_cost == Decimal("166.50")

    # Verteilung über Wohnungsverbrauch (Wohnung 1 = 56/111, Wohnung 2 = 55/111)
    total = Decimal("365.94") + Decimal("166.50")
    mieter_a = next(ln for ln in result.tenant_lines if ln.name == "Mieter A")
    mieter_b = next(ln for ln in result.tenant_lines if ln.name == "Mieter B")
    assert float(mieter_a.breakdown["WASSER_VERBRAUCH"]) == pytest.approx(
        float(total * Decimal(56) / Decimal(111))
    )
    assert float(mieter_b.breakdown["WASSER_VERBRAUCH"]) == pytest.approx(
        float(total * Decimal(55) / Decimal(111))
    )
