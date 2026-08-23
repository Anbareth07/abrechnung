from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import TechemKind


class TechemRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    kind: TechemKind
    invoice_date: date
    quantity_kwh: Optional[Decimal]
    gross_amount: Decimal
    notes: Optional[str]
    meta: dict


class TechemRecordCreate(BaseModel):
    property_id: int
    kind: TechemKind = TechemKind.GAS
    invoice_date: date
    quantity_kwh: Optional[Decimal] = None
    gross_amount: Decimal = Decimal("0")
    notes: Optional[str] = None
    meta: dict = Field(default_factory=dict)


class TechemRecordUpdate(BaseModel):
    kind: Optional[TechemKind] = None
    invoice_date: Optional[date] = None
    quantity_kwh: Optional[Decimal] = None
    gross_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    meta: Optional[dict] = None
