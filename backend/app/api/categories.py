from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas.category import (
    AllocationConfigCreate,
    AllocationConfigRead,
    AllocationConfigUpdate,
    CostCategoryCreate,
    CostCategoryRead,
    CostCategoryUpdate,
)

router = APIRouter(prefix="/cost-categories", tags=["cost-categories"])

config_router = APIRouter(prefix="/allocation-configs", tags=["allocation-configs"])


@router.get("", response_model=list[CostCategoryRead])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(models.CostCategory).order_by(models.CostCategory.name)).all()


@router.post("", response_model=CostCategoryRead, status_code=201)
def create_category(payload: CostCategoryCreate, db: Session = Depends(get_db)):
    if db.scalar(select(models.CostCategory).where(models.CostCategory.code == payload.code)):
        raise HTTPException(409, "Kostenart-Code existiert bereits")
    obj = models.CostCategory(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{category_id}", response_model=CostCategoryRead)
def get_category(category_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.CostCategory, category_id)
    if obj is None:
        raise HTTPException(404, "Kostenart nicht gefunden")
    return obj


@router.patch("/{category_id}", response_model=CostCategoryRead)
def update_category(category_id: int, payload: CostCategoryUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.CostCategory, category_id)
    if obj is None:
        raise HTTPException(404, "Kostenart nicht gefunden")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.CostCategory, category_id)
    if obj is None:
        raise HTTPException(404, "Kostenart nicht gefunden")
    db.delete(obj)
    db.commit()


def _config_dict(config: models.AllocationConfig) -> dict:
    return {
        "id": config.id,
        "property_id": config.property_id,
        "cost_category_id": config.cost_category_id,
        "allocation_key": config.allocation_key.value,
        "sort_order": config.sort_order,
        "category_code": config.cost_category.code,
        "category_name": config.cost_category.name,
    }


@config_router.get("")
def list_allocation_configs(property_id: int | None = None, db: Session = Depends(get_db)):
    query = select(models.AllocationConfig)
    if property_id is not None:
        query = query.where(models.AllocationConfig.property_id == property_id)
    configs = db.scalars(query.order_by(models.AllocationConfig.sort_order)).all()
    return [_config_dict(c) for c in configs]


@config_router.post("", status_code=201)
def create_allocation_config(payload: AllocationConfigCreate, db: Session = Depends(get_db)):
    if db.get(models.Property, payload.property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    if db.get(models.CostCategory, payload.cost_category_id) is None:
        raise HTTPException(404, "Kostenart nicht gefunden")
    exists = db.scalar(
        select(models.AllocationConfig).where(
            models.AllocationConfig.property_id == payload.property_id,
            models.AllocationConfig.cost_category_id == payload.cost_category_id,
        )
    )
    if exists:
        raise HTTPException(409, "Umlage-Konfiguration existiert bereits")
    obj = models.AllocationConfig(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _config_dict(obj)


@config_router.patch("/{config_id}")
def update_allocation_config(config_id: int, payload: AllocationConfigUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.AllocationConfig, config_id)
    if obj is None:
        raise HTTPException(404, "Umlage-Konfiguration nicht gefunden")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return _config_dict(obj)


@config_router.delete("/{config_id}", status_code=204)
def delete_allocation_config(config_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.AllocationConfig, config_id)
    if obj is None:
        raise HTTPException(404, "Umlage-Konfiguration nicht gefunden")
    db.delete(obj)
    db.commit()
