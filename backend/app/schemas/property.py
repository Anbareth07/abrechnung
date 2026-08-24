from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    street: str
    zip_code: str
    city: str
    is_test: bool = False
    strom_allocation_category_id: Optional[int] = None
    wasser_trinkwasser_category_id: Optional[int] = None
    wasser_schmutzwasser_category_id: Optional[int] = None
    wasser_niederschlag_category_id: Optional[int] = None
    wasser_versiegelte_flaeche: Optional[Decimal] = None
    strom_unterzaehler_aktiv: bool = True
    wasser_waschmaschinen_aktiv: bool = True
    created_at: datetime


class PropertyCreate(BaseModel):
    name: str
    street: str = ""
    zip_code: str = ""
    city: str = ""
    is_test: bool = False
    wasser_versiegelte_flaeche: Optional[Decimal] = None
    strom_unterzaehler_aktiv: bool = True
    wasser_waschmaschinen_aktiv: bool = True


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    street: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    is_test: Optional[bool] = None
    strom_allocation_category_id: Optional[int] = None
    wasser_trinkwasser_category_id: Optional[int] = None
    wasser_schmutzwasser_category_id: Optional[int] = None
    wasser_niederschlag_category_id: Optional[int] = None
    wasser_versiegelte_flaeche: Optional[Decimal] = None
    strom_unterzaehler_aktiv: Optional[bool] = None
    wasser_waschmaschinen_aktiv: Optional[bool] = None


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


class AdvanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    valid_from: date
    amount: Decimal


class AdvanceCreate(BaseModel):
    valid_from: date
    amount: Decimal


class MonthlyCostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    amount: Decimal


class MonthlyCostCreate(BaseModel):
    name: str
    amount: Decimal


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lease_unit_id: int
    name: str
    move_in: date
    move_out: Optional[date]
    monthly_advance: Decimal
    phone: Optional[str] = None
    email: Optional[str] = None
    # ORM-Relationship heißt "advance_payments" → Alias für from_attributes
    advances: list[AdvanceRead] = Field(default=[], validation_alias="advance_payments")
    monthly_costs: list[MonthlyCostRead] = []


class TenantCreate(BaseModel):
    lease_unit_id: int
    name: str
    move_in: date
    move_out: Optional[date] = None
    monthly_advance: Decimal = Decimal("0")
    phone: Optional[str] = None
    email: Optional[str] = None
    advances: list[AdvanceCreate] = []
    monthly_costs: list[MonthlyCostCreate] = []


class TenantUpdate(BaseModel):
    lease_unit_id: Optional[int] = None
    name: Optional[str] = None
    move_in: Optional[date] = None
    move_out: Optional[date] = None
    monthly_advance: Optional[Decimal] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    advances: Optional[list[AdvanceCreate]] = None
    monthly_costs: Optional[list[MonthlyCostCreate]] = None
