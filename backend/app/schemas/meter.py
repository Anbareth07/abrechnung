from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from ..models.enums import MeterType, MeterUnit


class MeterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: Optional[int]
    lease_unit_id: Optional[int]
    name: str
    meter_type: MeterType
    unit: MeterUnit


class MeterCreate(BaseModel):
    property_id: Optional[int] = None
    lease_unit_id: Optional[int] = None
    name: str
    meter_type: MeterType = MeterType.OTHER
    unit: MeterUnit = MeterUnit.M3


class MeterUpdate(BaseModel):
    property_id: Optional[int] = None
    lease_unit_id: Optional[int] = None
    name: Optional[str] = None
    meter_type: Optional[MeterType] = None
    unit: Optional[MeterUnit] = None


class MeterReadingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meter_id: int
    reading_date: date
    value: Decimal


class MeterReadingCreate(BaseModel):
    meter_id: int
    reading_date: date
    value: Decimal


class MeterReadingUpdate(BaseModel):
    reading_date: Optional[date] = None
    value: Optional[Decimal] = None
