from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StromPriceCreate(BaseModel):
    property_id: int
    kind: str  # GRUNDGEBUEHR | ARBEITSPREIS | STROMSTEUER
    valid_from: date
    valid_to: date
    amount: Decimal
    vat_rate: Decimal = Decimal("19.00")


class StromPriceUpdate(BaseModel):
    kind: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    amount: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None


class StromPriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    kind: str
    valid_from: date
    valid_to: date
    amount: Decimal
    vat_rate: Decimal


class StromReadingCreate(BaseModel):
    property_id: int
    role: str  # HAUPTZAEHLER | UNTERZAEHLER
    reading_date: date
    value: Decimal
    vor_zaehlerwechsel: bool = False
    neuer_zaehler_start: Decimal = Decimal("0")
    # RECHNUNG (vom Versorger übermittelt) | ABLESUNG (selbst abgelesen)
    source: str = "RECHNUNG"


class StromReadingUpdate(BaseModel):
    role: Optional[str] = None
    reading_date: Optional[date] = None
    value: Optional[Decimal] = None
    vor_zaehlerwechsel: Optional[bool] = None
    neuer_zaehler_start: Optional[Decimal] = None
    source: Optional[str] = None


class StromReadingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    role: str
    reading_date: date
    value: Decimal
    vor_zaehlerwechsel: bool = False
    neuer_zaehler_start: Decimal = Decimal("0")
    source: str = "RECHNUNG"
