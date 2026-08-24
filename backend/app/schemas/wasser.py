from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class WasserPriceCreate(BaseModel):
    property_id: int
    kind: str  # TRINKWASSER | SCHMUTZWASSER | NIEDERSCHLAGSWASSER | GRUNDGEBUEHR
    valid_from: date
    valid_to: date
    amount: Decimal
    # None → artabhängiger Standard (Trinkwasser/Grundgebühr 7 %, Schmutz/Niederschlag 0 %)
    vat_rate: Optional[Decimal] = None


class WasserPriceUpdate(BaseModel):
    kind: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    amount: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None


class WasserPriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    kind: str
    valid_from: date
    valid_to: date
    amount: Decimal
    vat_rate: Decimal


class WasserReadingCreate(BaseModel):
    property_id: int
    reading_date: date
    value: Decimal
    vor_zaehlerwechsel: bool = False
    neuer_zaehler_start: Decimal = Decimal("0")


class WasserReadingUpdate(BaseModel):
    reading_date: Optional[date] = None
    value: Optional[Decimal] = None
    vor_zaehlerwechsel: Optional[bool] = None
    neuer_zaehler_start: Optional[Decimal] = None


class WasserReadingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    reading_date: date
    value: Decimal
    vor_zaehlerwechsel: bool = False
    neuer_zaehler_start: Decimal = Decimal("0")
