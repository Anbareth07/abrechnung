"""Factory-Funktionen zum Aufbau von Testdaten."""

from datetime import date
from decimal import Decimal
from typing import Optional

from app import models
from app.models.enums import AllocationKey, MeterType, MeterUnit


def make_property(session, name: str, street: str = ""):
    prop = models.Property(name=name, street=street or name, zip_code="", city="")
    session.add(prop)
    session.flush()
    return prop


def make_category(session, code: str, name: str, default_key: AllocationKey = AllocationKey.NONE):
    cat = models.CostCategory(code=code, name=name, default_allocation_key=default_key)
    session.add(cat)
    session.flush()
    return cat


def make_config(session, prop, cat, key: AllocationKey, order: int = 0):
    cfg = models.AllocationConfig(
        property_id=prop.id, cost_category_id=cat.id, allocation_key=key, sort_order=order
    )
    session.add(cfg)
    session.flush()
    return cfg


def make_unit(session, prop, designation: str, wf: str, extra: str = "0"):
    unit = models.LeaseUnit(
        property_id=prop.id,
        designation=designation,
        living_area=Decimal(wf),
        extra_area=Decimal(extra),
    )
    session.add(unit)
    session.flush()
    return unit


def make_tenant(
    session,
    unit,
    name: str,
    move_in: date,
    monthly: str,
    move_out: Optional[date] = None,
):
    tenant = models.Tenant(
        lease_unit_id=unit.id,
        name=name,
        move_in=move_in,
        move_out=move_out,
        monthly_advance=Decimal(monthly),
    )
    session.add(tenant)
    session.flush()
    return tenant


def make_meter(
    session,
    name: str,
    mtype: MeterType,
    prop=None,
    unit=None,
    munit: MeterUnit = MeterUnit.M3,
):
    meter = models.Meter(
        name=name,
        meter_type=mtype,
        unit=munit,
        property_id=prop.id if prop else None,
        lease_unit_id=unit.id if unit else None,
    )
    session.add(meter)
    session.flush()
    return meter


def make_reading(session, meter, reading_date: date, value: str):
    reading = models.MeterReading(
        meter_id=meter.id, reading_date=reading_date, value=Decimal(value)
    )
    session.add(reading)
    session.flush()
    return reading


def make_invoice(session, prop, cat, period_start: date, period_end: date, items=None):
    """items: Liste von (from_date, to_date, gross_amount_str)."""
    invoice = models.Invoice(
        property_id=prop.id,
        cost_category_id=cat.id,
        period_start=period_start,
        period_end=period_end,
    )
    session.add(invoice)
    session.flush()
    for from_date, to_date, amount in items or []:
        session.add(
            models.InvoiceItem(
                invoice_id=invoice.id,
                from_date=from_date,
                to_date=to_date,
                gross_amount=Decimal(amount),
            )
        )
    session.flush()
    return invoice
