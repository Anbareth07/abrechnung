from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import InvoiceKind


class InvoiceItemCreate(BaseModel):
    from_date: date
    to_date: date
    description: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    gross_amount: Decimal = Decimal("0")
    meta: dict = Field(default_factory=dict)


class InvoiceItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    from_date: date
    to_date: date
    description: Optional[str]
    quantity: Optional[Decimal]
    unit: Optional[str]
    unit_price: Optional[Decimal]
    gross_amount: Decimal
    meta: dict


class InvoiceCreate(BaseModel):
    property_id: int
    cost_category_id: int
    kind: Optional[InvoiceKind] = None
    valid_from: Optional[date] = None
    annual_amount: Optional[Decimal] = None
    lease_unit_id: Optional[int] = None
    invoice_number: Optional[str] = None
    supplier: Optional[str] = None
    description: Optional[str] = None
    issue_date: Optional[date] = None
    period_start: date
    period_end: date
    gross_amount: Optional[Decimal] = None
    anteil_zaehler: Optional[Decimal] = None
    anteil_nenner: Optional[Decimal] = None
    meta: dict = Field(default_factory=dict)
    items: list[InvoiceItemCreate] = Field(default_factory=list)


class InvoiceUpdate(BaseModel):
    cost_category_id: Optional[int] = None
    kind: Optional[InvoiceKind] = None
    valid_from: Optional[date] = None
    annual_amount: Optional[Decimal] = None
    lease_unit_id: Optional[int] = None
    invoice_number: Optional[str] = None
    supplier: Optional[str] = None
    description: Optional[str] = None
    issue_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    gross_amount: Optional[Decimal] = None
    anteil_zaehler: Optional[Decimal] = None
    anteil_nenner: Optional[Decimal] = None
    meta: Optional[dict] = None
    items: Optional[list[InvoiceItemCreate]] = None


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    cost_category_id: int
    kind: Optional[str]
    valid_from: Optional[date]
    annual_amount: Optional[Decimal]
    lease_unit_id: Optional[int]
    invoice_number: Optional[str]
    supplier: Optional[str]
    description: Optional[str]
    issue_date: Optional[date]
    period_start: date
    period_end: date
    gross_amount: Optional[Decimal]
    anteil_zaehler: Optional[Decimal]
    anteil_nenner: Optional[Decimal]
    meta: dict
    items: list[InvoiceItemRead]
