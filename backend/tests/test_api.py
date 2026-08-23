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
        json={"code": "trinkwasser", "name": "Trinkwasser", "default_allocation_key": "CONSUMPTION"},
    ).json()
    schmutz = client.post(
        "/cost-categories",
        json={"code": "schmutzwasser", "name": "Schmutzwasser", "default_allocation_key": "CONSUMPTION"},
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

    # cbm-Preis: (1000*181/365 + 500) / (Garten 30 + Wohnung 50) = ... / 80
    expected_price = (1000 * 181 / 365 + 500) / 80
    assert abs(float(result["water_price_per_m3"]) - expected_price) < 1e-9
    assert float(result["water"]["garden_consumption"]) == 30.0

    # Finalisieren
    final = client.post(f"/settlements/{pid}/2026/finalize").json()
    assert final["status"] == "FINAL"
    assert final["tenant_count"] == 1


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
