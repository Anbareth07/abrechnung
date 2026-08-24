import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import Base, Meter, MeterReading, SettlementLine


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


def _seed_objekt1(client):
    prop = client.post(
        "/properties", json={"name": "Objekt 1", "street": ""}
    ).json()
    pid = prop["id"]

    trink = client.post(
        "/cost-categories",
        json={"property_id": pid, "code": "trinkwasser", "name": "Trinkwasser", "default_allocation_key": "CONSUMPTION"},
    ).json()
    schmutz = client.post(
        "/cost-categories",
        json={"property_id": pid, "code": "schmutzwasser", "name": "Schmutzwasser", "default_allocation_key": "CONSUMPTION"},
    ).json()

    client.post(
        "/allocation-configs",
        json={"property_id": pid, "cost_category_id": trink["id"], "allocation_key": "CONSUMPTION", "sort_order": 1},
    )
    client.post(
        "/allocation-configs",
        json={"property_id": pid, "cost_category_id": schmutz["id"], "allocation_key": "CONSUMPTION", "sort_order": 2},
    )

    unit = client.post(
        "/lease-units",
        json={"property_id": pid, "designation": "Wohnung 1", "living_area": "76.0", "extra_area": "4.0"},
    ).json()
    client.post(
        "/tenants",
        json={"lease_unit_id": unit["id"], "name": "Mieter A", "move_in": "2020-01-01", "monthly_advance": "150.00"},
    )

    garden = client.post(
        "/meters", json={"property_id": pid, "name": "Garten Nord", "meter_type": "GARDEN", "unit": "m3"}
    ).json()
    water = client.post(
        "/meters", json={"lease_unit_id": unit["id"], "name": "Wohnung 1 Wasser", "meter_type": "APARTMENT_WATER", "unit": "m3"}
    ).json()

    client.post("/meter-readings", json={"meter_id": garden["id"], "reading_date": "2025-12-31", "value": "100.0"})
    client.post("/meter-readings", json={"meter_id": garden["id"], "reading_date": "2026-12-31", "value": "130.0"})
    client.post("/meter-readings", json={"meter_id": water["id"], "reading_date": "2025-12-31", "value": "10.0"})
    client.post("/meter-readings", json={"meter_id": water["id"], "reading_date": "2026-12-31", "value": "60.0"})

    client.post(
        "/invoices",
        json={
            "property_id": pid,
            "cost_category_id": trink["id"],
            "period_start": "2025-07-01",
            "period_end": "2026-06-30",
            "items": [{"from_date": "2025-07-01", "to_date": "2026-06-30", "gross_amount": "1000.00"}],
        },
    )
    client.post(
        "/invoices",
        json={
            "property_id": pid,
            "cost_category_id": schmutz["id"],
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
            "items": [{"from_date": "2026-01-01", "to_date": "2026-12-31", "gross_amount": "500.00"}],
        },
    )
    return pid


def test_full_flow(client):
    pid = _seed_objekt1(client)

    # Vollständigkeits-Check: alles vorhanden → leer
    completeness = client.get(f"/settlements/{pid}/2026/completeness").json()
    assert completeness == []

    # Abrechnung berechnen
    result = client.get(f"/settlements/{pid}/2026").json()
    assert result["property_name"] == "Objekt 1"
    assert len(result["tenant_lines"]) == 1
    line = result["tenant_lines"][0]
    assert line["name"] == "Mieter A"
    assert line["tenant_days"] == 365

    # cbm-Preis: (1000*181/365 + 500) / Wohnung 50 (Garten wird ignoriert)
    expected_price = (1000 * 181 / 365 + 500) / 50
    assert abs(float(result["water_price_per_m3"]) - expected_price) < 1e-9
    assert float(result["water"]["garden_consumption"]) == 0.0

    # Finalisieren
    final = client.post(f"/settlements/{pid}/2026/finalize").json()
    assert final["status"] == "FINAL"
    assert final["tenant_count"] == 1


def test_completeness_recurring_grundsteuer(client):
    """Wiederkehrende Grundsteuer (gültig ab + Jahresbetrag, ohne Positionen)
    gilt im Vollständigkeits-Check als vorhandene Rechnung."""
    p = client.post("/properties", json={"name": "Objekt 1", "street": ""}).json()
    cat = client.post(
        "/cost-categories", json={"property_id": p["id"], "name": "Grundsteuer"}
    ).json()
    client.post(
        "/allocation-configs",
        json={
            "property_id": p["id"],
            "cost_category_id": cat["id"],
            "allocation_key": "NF",
            "sort_order": 1,
        },
    ).json()
    u = client.post(
        "/lease-units",
        json={
            "property_id": p["id"],
            "designation": "W1",
            "living_area": "50.0",
            "extra_area": "50.0",
        },
    ).json()
    client.post(
        "/tenants",
        json={
            "lease_unit_id": u["id"],
            "name": "Mieter A",
            "move_in": "2020-01-01",
            "monthly_advance": "100.00",
        },
    ).json()

    # Ohne Rechnung → Grundsteuer fehlt
    missing = client.get(f"/settlements/{p['id']}/2026/completeness").json()
    assert any(m["label"].startswith("Rechnung fehlt: Grundsteuer") for m in missing)

    # Wiederkehrende Grundsteuer anlegen (keine Positionen)
    client.post(
        "/invoices",
        json={
            "property_id": p["id"],
            "cost_category_id": cat["id"],
            "kind": "GRUNDSTEUER",
            "valid_from": "2020-01-01",
            "annual_amount": "1200.00",
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
            "items": [],
        },
    )
    missing2 = client.get(f"/settlements/{p['id']}/2026/completeness").json()
    assert not any(m["label"].startswith("Rechnung fehlt: Grundsteuer") for m in missing2)


def test_finalized_snapshot(client):
    """Snapshot-Endpunkt: 404 vor Finalisierung, danach gespeicherte Werte zurückgeben."""
    pid = _seed_objekt1(client)

    # Vor der Finalisierung → 404
    missing = client.get(f"/settlements/{pid}/2026/finalized")
    assert missing.status_code == 404

    live = client.get(f"/settlements/{pid}/2026").json()
    client.post(f"/settlements/{pid}/2026/finalize")

    snap = client.get(f"/settlements/{pid}/2026/finalized").json()
    assert snap["status"] == "FINAL"
    assert snap["property_name"] == "Objekt 1"
    assert len(snap["tenant_lines"]) == 1

    line = snap["tenant_lines"][0]
    live_line = live["tenant_lines"][0]
    assert line["name"] == "Mieter A"
    # Snapshot ist auf 2 Nachkommastellen gerundet gespeichert
    assert line["total_costs"] == round(live_line["total_costs"], 2)
    assert line["advance_total"] == round(live_line["advance_total"], 2)
    assert line["saldo"] == round(live_line["saldo"], 2)
    # Kostenarten-Namen sind im Snapshot enthalten
    assert "trinkwasser" in snap["category_names"]

    # Der Snapshot bleibt unverändert, auch wenn live eine Rechnung dazukommt
    client.post(
        "/invoices",
        json={
            "property_id": pid,
            "cost_category_id": 1,
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
            "items": [{"from_date": "2026-01-01", "to_date": "2026-12-31", "gross_amount": "999.00"}],
        },
    )
    snap2 = client.get(f"/settlements/{pid}/2026/finalized").json()
    assert snap2["tenant_lines"][0]["total_costs"] == line["total_costs"]


def test_tenant_contact_and_monthly_costs(client):
    p = client.post("/properties", json={"name": "Objekt 1"}).json()
    u = client.post(
        "/lease-units",
        json={"property_id": p["id"], "designation": "W1", "living_area": "50.0"},
    ).json()

    created = client.post(
        "/tenants",
        json={
            "lease_unit_id": u["id"],
            "name": "Mieter A",
            "move_in": "2020-01-01",
            "monthly_advance": "150.00",
            "phone": "0170 123456",
            "email": "a@example.de",
            "advances": [
                {"valid_from": "2020-01-01", "amount": "150.00"},
                {"valid_from": "2025-07-01", "amount": "180.00"},
            ],
            "monthly_costs": [
                {"name": "Heizkosten", "amount": "90.50"},
                {"name": "Kaltmiete", "amount": "620.00"},
            ],
        },
    ).json()
    assert created["phone"] == "0170 123456"
    assert created["email"] == "a@example.de"
    assert len(created["monthly_costs"]) == 2
    assert {c["name"] for c in created["monthly_costs"]} == {"Kaltmiete", "Heizkosten"}
    # Vorauszahlungs-Zeiträume werden zurückgegeben, aktuelle = letzter Zeitraum
    assert len(created["advances"]) == 2
    assert created["monthly_advance"] == "180.00"

    # GET liefert Kontaktdaten, Zeiträume und Monatskosten zurück
    fetched = client.get(f"/tenants/{created['id']}").json()
    assert fetched["phone"] == "0170 123456"
    assert fetched["email"] == "a@example.de"
    assert len(fetched["monthly_costs"]) == 2
    assert len(fetched["advances"]) == 2
    assert {a["valid_from"] for a in fetched["advances"]} == {"2020-01-01", "2025-07-01"}

    # Update ersetzt Kontaktdaten, Zeiträume und Monatskosten
    patched = client.patch(
        f"/tenants/{created['id']}",
        json={
            "phone": "0170 999999",
            "email": "neu@example.de",
            "advances": [
                {"valid_from": "2020-01-01", "amount": "150.00"},
                {"valid_from": "2025-07-01", "amount": "180.00"},
                {"valid_from": "2026-01-01", "amount": "200.00"},
            ],
            "monthly_costs": [{"name": "Kaltmiete", "amount": "640.00"}],
        },
    ).json()
    assert patched["phone"] == "0170 999999"
    assert patched["email"] == "neu@example.de"
    assert [c["name"] for c in patched["monthly_costs"]] == ["Kaltmiete"]
    assert float(patched["monthly_costs"][0]["amount"]) == 640.0
    assert len(patched["advances"]) == 3
    assert patched["monthly_advance"] == "200.00"

    # Auch nach erneutem GET bleiben die Zeiträume erhalten
    refetched = client.get(f"/tenants/{created['id']}").json()
    assert len(refetched["advances"]) == 3
    assert refetched["monthly_advance"] == "200.00"

    # Monatskosten fließen NICHT in die Abrechnung ein
    result = client.get(f"/settlements/{p['id']}/2026").json()
    line = result["tenant_lines"][0]
    assert line["name"] == "Mieter A"
    assert float(line["total_costs"]) == 0.0  # keine umlagefähigen Kosten vorhanden
    assert "monthly_costs" not in line
    assert float(line["saldo"]) == float(-line["advance_total"])


def test_advance_change_must_be_month_start(client):
    p = client.post("/properties", json={"name": "Objekt 1"}).json()
    u = client.post(
        "/lease-units",
        json={"property_id": p["id"], "designation": "W1", "living_area": "50.0"},
    ).json()

    # Erste Vorauszahlung (Einzug) darf unter dem Monat liegen, Änderung nur zum Monatsanfang
    ok = client.post(
        "/tenants",
        json={
            "lease_unit_id": u["id"],
            "name": "Mieter A",
            "move_in": "2025-07-15",
            "monthly_advance": "150.00",
            "advances": [
                {"valid_from": "2025-07-15", "amount": "150.00"},
                {"valid_from": "2025-10-01", "amount": "180.00"},
            ],
        },
    )
    assert ok.status_code == 201

    # Änderung unter dem Monat → 422
    bad = client.post(
        "/tenants",
        json={
            "lease_unit_id": u["id"],
            "name": "Mieter B",
            "move_in": "2025-07-15",
            "monthly_advance": "150.00",
            "advances": [
                {"valid_from": "2025-07-15", "amount": "150.00"},
                {"valid_from": "2025-10-15", "amount": "180.00"},
            ],
        },
    )
    assert bad.status_code == 422


def test_category_auto_code(client):
    p = client.post("/properties", json={"name": "Objekt 1"}).json()
    pid = p["id"]

    # Ohne Code → Code wird aus dem Namen erzeugt (Slug), objektgebunden
    c1 = client.post(
        "/cost-categories",
        json={"property_id": pid, "name": "Trinkwasser", "default_allocation_key": "CONSUMPTION"},
    ).json()
    assert c1["code"] == "trinkwasser"
    assert c1["name"] == "Trinkwasser"
    assert c1["property_id"] == pid

    # Umlaute/Leerzeichen werden normalisiert
    c2 = client.post(
        "/cost-categories",
        json={"property_id": pid, "name": "Gebäudebrand-/Elementarversicherung"},
    ).json()
    assert c2["code"] == "gebaudebrand_elementarversicherung"

    # Gleicher Name am selben Objekt → find-or-create (keine zweite Kostenart)
    c3 = client.post("/cost-categories", json={"property_id": pid, "name": "Trinkwasser"}).json()
    assert c3["id"] == c1["id"]

    # Expliziter Code wird weiterhin akzeptiert
    c5 = client.post(
        "/cost-categories", json={"property_id": pid, "name": "Heizung", "code": "heizung"}
    ).json()
    assert c5["code"] == "heizung"

    # Gleicher Name an anderem Objekt → eigene Kostenart, Code global erweitert
    p2 = client.post("/properties", json={"name": "Objekt 2"}).json()
    c6 = client.post(
        "/cost-categories", json={"property_id": p2["id"], "name": "Trinkwasser"}
    ).json()
    assert c6["id"] != c1["id"]
    assert c6["property_id"] == p2["id"]
    assert c6["code"] == "trinkwasser_2"

    # Filter nach Objekt
    only_p1 = client.get("/cost-categories", params={"property_id": pid}).json()
    assert all(cat["property_id"] == pid for cat in only_p1)


def test_allocation_config_auto_creates_category(client):
    p = client.post("/properties", json={"name": "Objekt 1"}).json()
    pid = p["id"]

    # Kostenart entsteht automatisch beim Hinzufügen in den Umlageschlüsseln
    cfg = client.post(
        "/allocation-configs",
        json={
            "property_id": pid,
            "cost_category_name": "Gartenpflege",
            "allocation_key": "WF",
            "sort_order": 1,
        },
    ).json()
    assert cfg["category_name"] == "Gartenpflege"
    assert cfg["category_code"]  # Auto-Code vorhanden

    # Erneutes Hinzufügen mit gleichem Namen → Config-Konflikt, aber nur EINE Kostenart
    dup = client.post(
        "/allocation-configs",
        json={
            "property_id": pid,
            "cost_category_name": "Gartenpflege",
            "allocation_key": "WF",
            "sort_order": 2,
        },
    )
    assert dup.status_code == 409
    cats = client.get("/cost-categories", params={"property_id": pid}).json()
    assert len(cats) == 1


def test_crud_and_filters(client):
    # Objekte anlegen
    p1 = client.post("/properties", json={"name": "A"}).json()
    p2 = client.post("/properties", json={"name": "B"}).json()
    assert client.get("/properties").json().__len__() == 2

    # Mieteinheiten & Mieter-Filter
    u = client.post("/lease-units", json={"property_id": p1["id"], "designation": "W1", "living_area": "50.0"}).json()
    client.post("/tenants", json={"lease_unit_id": u["id"], "name": "Mieter A", "move_in": "2020-01-01"})
    assert len(client.get("/tenants", params={"property_id": p1["id"]}).json()) == 1
    assert len(client.get("/tenants", params={"property_id": p2["id"]}).json()) == 0

    # Update & Delete
    patched = client.patch(f"/properties/{p2['id']}", json={"city": "Augsburg"}).json()
    assert patched["city"] == "Augsburg"
    assert client.delete(f"/properties/{p2['id']}").status_code == 204
    assert len(client.get("/properties").json()) == 1
