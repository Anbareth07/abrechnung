"""Tests für das Strom-Modul (Tarife, Zählerstände, Berechnung, Techem)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import Base


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


def test_preis_luecken_und_ueberlappungen_verboten(client):
    p = _objekt(client)
    # erster Zeitraum
    r = client.post(
        "/strom/prices",
        json={"property_id": p["id"], "kind": "ARBEITSPREIS", "valid_from": "2025-01-01", "valid_to": "2025-06-30", "amount": "0.30"},
    )
    assert r.status_code == 201

    # Lücke (Juli–September fehlt) → 422
    r = client.post(
        "/strom/prices",
        json={"property_id": p["id"], "kind": "ARBEITSPREIS", "valid_from": "2025-10-01", "valid_to": "2025-12-31", "amount": "0.35"},
    )
    assert r.status_code == 422

    # lückenlos anschließend → 201
    r = client.post(
        "/strom/prices",
        json={"property_id": p["id"], "kind": "ARBEITSPREIS", "valid_from": "2025-07-01", "valid_to": "2025-12-31", "amount": "0.35"},
    )
    assert r.status_code == 201

    # Überlappung → 422
    r = client.post(
        "/strom/prices",
        json={"property_id": p["id"], "kind": "ARBEITSPREIS", "valid_from": "2025-01-01", "valid_to": "2025-03-31", "amount": "0.28"},
    )
    assert r.status_code == 422


def test_berechnung_interpolation_unterzaehler_und_kosten(client):
    p = _objekt(client)
    client.post("/strom/readings", json={"property_id": p["id"], "role": "HAUPTZAEHLER", "reading_date": "2025-01-01", "value": "1000"})
    client.post("/strom/readings", json={"property_id": p["id"], "role": "HAUPTZAEHLER", "reading_date": "2025-12-31", "value": "2000"})
    client.post("/strom/readings", json={"property_id": p["id"], "role": "UNTERZAEHLER", "reading_date": "2025-01-01", "value": "100"})
    client.post("/strom/readings", json={"property_id": p["id"], "role": "UNTERZAEHLER", "reading_date": "2025-12-31", "value": "300"})

    client.post("/strom/prices", json={"property_id": p["id"], "kind": "ARBEITSPREIS", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "0.30", "vat_rate": "19"})
    client.post("/strom/prices", json={"property_id": p["id"], "kind": "STROMSTEUER", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "0.02", "vat_rate": "19"})
    client.post("/strom/prices", json={"property_id": p["id"], "kind": "GRUNDGEBUEHR", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "10.00", "vat_rate": "19"})

    r = client.get(f"/strom/{p['id']}/berechnung", params={"von": "2025-01-01", "bis": "2025-12-31"})
    assert r.status_code == 200
    data = r.json()
    assert data["hauptzaehler"]["consumption"] == pytest.approx(1000.0)
    assert data["unterzaehler"]["consumption"] == pytest.approx(200.0)
    assert data["netto_verbrauch"] == pytest.approx(800.0)

    by_art = {x["art"]: x for x in data["positionen"]}
    assert by_art["ARBEITSPREIS"]["netto"] == pytest.approx(240.0, abs=1e-6)
    assert by_art["STROMSTEUER"]["netto"] == pytest.approx(16.0, abs=1e-6)
    # Grundgebühr €/Jahr: 2025 (365 Tage, kein Schaltjahr) → voller Jahresbetrag
    expected_gg = 10.0
    assert by_art["GRUNDGEBUEHR"]["netto"] == pytest.approx(expected_gg, abs=1e-6)
    assert by_art["ARBEITSPREIS"]["vat"] == pytest.approx(240 * 0.19, abs=1e-6)
    assert data["summen"]["brutto"] == pytest.approx((240 + 16 + expected_gg) * 1.19, abs=1e-6)


def test_berechnung_preisaenderung_im_zeitraum(client):
    p = _objekt(client)
    client.post("/strom/readings", json={"property_id": p["id"], "role": "HAUPTZAEHLER", "reading_date": "2025-01-01", "value": "1000"})
    client.post("/strom/readings", json={"property_id": p["id"], "role": "HAUPTZAEHLER", "reading_date": "2025-12-31", "value": "1600"})
    client.post("/strom/prices", json={"property_id": p["id"], "kind": "ARBEITSPREIS", "valid_from": "2025-01-01", "valid_to": "2025-06-30", "amount": "0.30"})
    client.post("/strom/prices", json={"property_id": p["id"], "kind": "ARBEITSPREIS", "valid_from": "2025-07-01", "valid_to": "2025-12-31", "amount": "0.36"})

    r = client.get(f"/strom/{p['id']}/berechnung", params={"von": "2025-01-01", "bis": "2025-12-31"})
    assert r.status_code == 200
    data = r.json()
    assert data["netto_verbrauch"] == pytest.approx(600.0)
    ap = [x for x in data["positionen"] if x["art"] == "ARBEITSPREIS"]
    assert len(ap) == 2
    ap1 = 600 * (181 / 365) * 0.30
    ap2 = 600 * (184 / 365) * 0.36
    assert sum(x["netto"] for x in ap) == pytest.approx(ap1 + ap2, abs=1e-6)


def test_techem_sheet_rundet_heizstrom(client):
    """Heizstrom wird auf ganze kWh gerundet (100,55 → 101)."""
    p = _objekt(client)
    client.post("/strom/readings", json={"property_id": p["id"], "role": "UNTERZAEHLER", "reading_date": "2025-01-01", "value": "100"})
    client.post("/strom/readings", json={"property_id": p["id"], "role": "UNTERZAEHLER", "reading_date": "2025-12-31", "value": "300"})

    # Heizperiode 01.07.2025–30.06.2026 → interpoliert 100,55 kWh → 101
    s = client.get("/techem/sheet", params={"property_id": p["id"], "von": "2025-07-01", "bis": "2026-06-30"})
    assert s.status_code == 200
    assert float(s.json()["strom_kwh"]) == pytest.approx(101.0)


def test_techem_sheet(client):
    """Heizkosten-Blatt: Stromanteil + -kosten automatisch, Werte speicherbar."""
    p = _objekt(client)
    client.post("/strom/readings", json={"property_id": p["id"], "role": "UNTERZAEHLER", "reading_date": "2025-01-01", "value": "100"})
    client.post("/strom/readings", json={"property_id": p["id"], "role": "UNTERZAEHLER", "reading_date": "2025-12-31", "value": "300"})
    client.post("/strom/prices", json={"property_id": p["id"], "kind": "ARBEITSPREIS", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "0.30", "vat_rate": "19"})
    client.post("/strom/prices", json={"property_id": p["id"], "kind": "STROMSTEUER", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "0.02", "vat_rate": "19"})

    # Vor dem Speichern: Stromanteil 200 kWh, Kosten (0,30+0,02)×200×1,19 = 76,16
    s = client.get("/techem/sheet", params={"property_id": p["id"], "von": "2025-01-01", "bis": "2025-12-31"})
    assert s.status_code == 200
    assert float(s.json()["strom_kwh"]) == pytest.approx(200.0)
    assert float(s.json()["strom_brutto"]) == pytest.approx(76.16)
    assert float(s.json()["gas_kwh"]) == pytest.approx(0.0)

    # Speichern von Gas, Wartung Heizung und Kaminfeger
    put = client.put("/techem/sheet", json={
        "property_id": p["id"], "von": "2025-01-01", "bis": "2025-12-31",
        "gas_kwh": "12000", "gas_cost": "900.00",
        "maintenance_cost": "150.00", "chimney_cost": "80.00",
        "notes": "Heizperiode 2025",
    })
    assert put.status_code == 200
    data = put.json()
    assert float(data["gas_kwh"]) == pytest.approx(12000.0)
    assert float(data["gas_cost"]) == pytest.approx(900.0)
    assert float(data["maintenance_cost"]) == pytest.approx(150.0)
    assert float(data["chimney_cost"]) == pytest.approx(80.0)
    assert float(data["strom_kwh"]) == pytest.approx(200.0)
    assert float(data["strom_brutto"]) == pytest.approx(76.16)

    # Liste enthält das Blatt
    lst = client.get("/techem", params={"property_id": p["id"]}).json()
    assert len(lst) == 1
    assert float(lst[0]["gas_cost"]) == pytest.approx(900.0)
    assert float(lst[0]["strom_kwh"]) == pytest.approx(200.0)
    assert float(lst[0]["strom_brutto"]) == pytest.approx(76.16)


def test_strom_in_abrechnung(client):
    """Strom fließt (falls Zählerstände vorhanden) als Kostenstelle in die Abrechnung ein."""
    p = _objekt(client)
    u = client.post("/lease-units", json={"property_id": p["id"], "designation": "W1", "living_area": "50.0"}).json()
    client.post("/tenants", json={"lease_unit_id": u["id"], "name": "Mieter A", "move_in": "2020-01-01", "monthly_advance": "100.00"}).json()

    client.post("/strom/readings", json={"property_id": p["id"], "role": "HAUPTZAEHLER", "reading_date": "2025-01-01", "value": "1000"})
    client.post("/strom/readings", json={"property_id": p["id"], "role": "HAUPTZAEHLER", "reading_date": "2025-12-31", "value": "2000"})
    client.post("/strom/prices", json={"property_id": p["id"], "kind": "ARBEITSPREIS", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "0.30", "vat_rate": "19"})

    # Explizit eigene "Strom"-Zeile (0), da leer = nicht in der Abrechnung
    client.patch(f"/properties/{p['id']}", json={"strom_allocation_category_id": 0})

    s = client.get(f"/settlements/{p['id']}/2025").json()
    strom_line = next((c for c in s["category_lines"] if c["code"] == "STROM"), None)
    assert strom_line is not None
    # Brutto: 1000 kWh × 0.30 × 1.19 = 357
    assert strom_line["year_cost"] == pytest.approx(357.0, abs=1e-6)
    # WF-Verteilung (50 von 50 m²) → voller Anteil beim einzigen Mieter
    assert s["tenant_lines"][0]["breakdown"]["STROM"] == pytest.approx(357.0, abs=1e-6)


def test_strom_in_bestehender_kostenstelle(client):
    """Stromkosten fließen in eine bestehende Kostenstelle ein – keine neue 'Strom'-Zeile."""
    p = _objekt(client)
    u = client.post("/lease-units", json={"property_id": p["id"], "designation": "W1", "living_area": "50.0"}).json()
    client.post("/tenants", json={"lease_unit_id": u["id"], "name": "Mieter A", "move_in": "2020-01-01", "monthly_advance": "100.00"}).json()

    client.post("/strom/readings", json={"property_id": p["id"], "role": "HAUPTZAEHLER", "reading_date": "2025-01-01", "value": "1000"})
    client.post("/strom/readings", json={"property_id": p["id"], "role": "HAUPTZAEHLER", "reading_date": "2025-12-31", "value": "2000"})
    client.post("/strom/prices", json={"property_id": p["id"], "kind": "ARBEITSPREIS", "valid_from": "2025-01-01", "valid_to": "2025-12-31", "amount": "0.30", "vat_rate": "19"})

    # bestehende Kostenstelle "Hausbeleuchtung" mit Umlageschlüssel WF
    cfg = client.post(
        "/allocation-configs",
        json={"property_id": p["id"], "cost_category_name": "Hausbeleuchtung", "allocation_key": "WF", "sort_order": 1},
    ).json()
    client.patch(f"/properties/{p['id']}", json={"strom_allocation_category_id": cfg["cost_category_id"]})

    s = client.get(f"/settlements/{p['id']}/2025").json()
    # keine eigene "Strom"-Zeile mehr
    assert not any(c["code"] == "STROM" for c in s["category_lines"])
    haus = next((c for c in s["category_lines"] if c["code"] == cfg["category_code"]), None)
    assert haus is not None
    # Strom-Brutto (357) fließt in die Kostenstelle ein
    assert haus["year_cost"] == pytest.approx(357.0, abs=1e-6)
    assert s["tenant_lines"][0]["breakdown"].get(haus["code"], 0) == pytest.approx(357.0, abs=1e-6)
