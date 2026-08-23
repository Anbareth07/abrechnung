from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    street: str
    zip_code: str
    city: str
    created_at: datetime


class PropertyCreate(BaseModel):
    name: str
    street: str = ""
    zip_code: str = ""
    city: str = ""


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    street: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None


class LeaseUnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    designation: str
    living_area: Decimal
    extra_area: Decimal
    utility_area: Decimal  # computed property (WF + Extra)


class LeaseUnitCreate(BaseModel):
    property_id: int
    designation: str
    living_area: Decimal = Decimal("0")
    extra_area: Decimal = Decimal("0")


class LeaseUnitUpdate(BaseModel):
    designation: Optional[str] = None
    living_area: Optional[Decimal] = None
    extra_area: Optional[Decimal] = None


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lease_unit_id: int
    name: str
    move_in: date
    move_out: Optional[date]
    monthly_advance: Decimal


class TenantCreate(BaseModel):
    lease_unit_id: int
    name: str
    move_in: date
    move_out: Optional[date] = None
    monthly_advance: Decimal = Decimal("0")


class TenantUpdate(BaseModel):
    lease_unit_id: Optional[int] = None
    name: Optional[str] = None
    move_in: Optional[date] = None
    move_out: Optional[date] = None
    monthly_advance: Optional[Decimal] = None
