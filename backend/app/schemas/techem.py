from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TechemSheetRead(BaseModel):
    """Heizkosten-Blatt für einen Zeitraum (strom_kwh automatisch aus Unterzähler)."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    property_id: int
    von: date
    bis: date
    strom_kwh: Decimal = Decimal("0")
    strom_netto: Decimal = Decimal("0")
    strom_vat: Decimal = Decimal("0")
    strom_brutto: Decimal = Decimal("0")
    gas_kwh: Decimal = Decimal("0")
    gas_cost: Decimal = Decimal("0")
    maintenance_cost: Decimal = Decimal("0")
    chimney_cost: Decimal = Decimal("0")
    notes: Optional[str] = None


class TechemSheetWrite(BaseModel):
    property_id: int
    von: date
    bis: date
    gas_kwh: Decimal = Decimal("0")
    gas_cost: Decimal = Decimal("0")
    maintenance_cost: Decimal = Decimal("0")
    chimney_cost: Decimal = Decimal("0")
    notes: Optional[str] = None
