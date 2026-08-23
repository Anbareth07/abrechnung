from datetime import date
from decimal import Decimal

from app import models


def test_all_tables_create_and_snapshot_works(session):
    """Smoke-Test: Settlement- und Techem-Tabellen lassen sich anlegen und befüllen."""
    prop = models.Property(name="Test", street="Teststraße 1", zip_code="", city="")
    session.add(prop)
    session.flush()

    unit = models.LeaseUnit(
        property_id=prop.id, designation="Wohnung 1", living_area=Decimal("50"), extra_area=Decimal("0")
    )
    session.add(unit)
    session.flush()

    tenant = models.Tenant(
        lease_unit_id=unit.id, name="Mieter A", move_in=date(2020, 1, 1), monthly_advance=Decimal("150")
    )
    session.add(tenant)
    session.flush()

    session.add(
        models.AdvancePayment(tenant_id=tenant.id, valid_from=date(2020, 1, 1), amount=Decimal("150"))
    )

    settlement = models.Settlement(property_id=prop.id, year=2026)
    session.add(settlement)
    session.flush()

    line = models.SettlementLine(
        settlement_id=settlement.id,
        tenant_id=tenant.id,
        detail={"grundsteuer": "800.00"},
        total_costs=Decimal("800.00"),
        advance_total=Decimal("1800.00"),
        saldo=Decimal("-1000.00"),
    )
    session.add(line)

    techem = models.TechemRecord(
        property_id=prop.id,
        von=date(2025, 7, 1),
        bis=date(2026, 6, 30),
        gas_kwh=Decimal("12000"),
        gas_cost=Decimal("950.00"),
    )
    session.add(techem)

    session.commit()

    assert session.get(models.Settlement, settlement.id).year == 2026
    assert session.get(models.SettlementLine, line.id).saldo == Decimal("-1000.00")
    assert session.get(models.TechemRecord, techem.id).gas_kwh == Decimal("12000")
    tenant_advances = session.get(models.Tenant, tenant.id).advance_payments
    assert len(tenant_advances) == 1
    assert tenant_advances[0].amount == Decimal("150")
