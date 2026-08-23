from typing import Optional

from pydantic import BaseModel, ConfigDict

from ..models.enums import AllocationKey


class CostCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    code: str
    name: str
    default_allocation_key: AllocationKey
    is_active: bool


class CostCategoryCreate(BaseModel):
    name: str
    property_id: int
    # Code wird bei Nichtangabe automatisch aus dem Namen erzeugt.
    code: Optional[str] = None
    default_allocation_key: AllocationKey = AllocationKey.NONE
    is_active: bool = True


class CostCategoryUpdate(BaseModel):
    name: Optional[str] = None
    default_allocation_key: Optional[AllocationKey] = None
    is_active: Optional[bool] = None


class AllocationConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    cost_category_id: int
    allocation_key: AllocationKey
    sort_order: int


class AllocationConfigCreate(BaseModel):
    property_id: int
    cost_category_id: Optional[int] = None
    # Statt einer ID kann direkt ein Name angegeben werden → Kostenart wird
    # objektgebunden automatisch angelegt (find-or-create).
    cost_category_name: Optional[str] = None
    allocation_key: AllocationKey = AllocationKey.WF
    sort_order: int = 0


class AllocationConfigUpdate(BaseModel):
    allocation_key: Optional[AllocationKey] = None
    sort_order: Optional[int] = None


class NoInvoiceCreate(BaseModel):
    cost_category_id: int
