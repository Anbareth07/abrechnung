import re
import unicodedata

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


def _slugify(name: str) -> str:
    """Wandelt einen Namen in einen technischen Code um (z. B. 'Trinkwasser' → 'trinkwasser')."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return text or "kategorie"


def _unique_code(db: Session, name: str) -> str:
    """Erzeugt einen eindeutigen Code aus dem Namen (bei Kollision '_2', '_3', …)."""
    base = _slugify(name)
    code, i = base, 2
    while db.scalar(select(models.CostCategory).where(models.CostCategory.code == code)):
        code = f"{base}_{i}"
        i += 1
    return code


def _get_or_create_category(db: Session, property_id: int, name: str) -> models.CostCategory:
    """Find-or-create einer Kostenart für ein Objekt (gleicher Name → wiederverwenden)."""
    existing = db.scalar(
        select(models.CostCategory).where(
            models.CostCategory.property_id == property_id,
            models.CostCategory.name == name,
        )
    )
    if existing is not None:
        return existing
    obj = models.CostCategory(
        property_id=property_id, name=name, code=_unique_code(db, name)
    )
    db.add(obj)
    db.flush()
    return obj


@router.get("", response_model=list[CostCategoryRead])
def list_categories(
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = select(models.CostCategory)
    if property_id is not None:
        query = query.where(models.CostCategory.property_id == property_id)
    return db.scalars(query.order_by(models.CostCategory.name)).all()


@router.post("", response_model=CostCategoryRead, status_code=201)
def create_category(payload: CostCategoryCreate, db: Session = Depends(get_db)):
    if db.get(models.Property, payload.property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    if payload.code is not None and db.scalar(
        select(models.CostCategory).where(models.CostCategory.code == payload.code)
    ):
        raise HTTPException(409, "Kostenart-Code existiert bereits")
    data = payload.model_dump()
    if not data.get("code"):
        data["code"] = _unique_code(db, data["name"])
    # Find-or-create je Objekt (gleicher Name → vorhandene Kostenart zurückgeben)
    existing = db.scalar(
        select(models.CostCategory).where(
            models.CostCategory.property_id == data["property_id"],
            models.CostCategory.name == data["name"],
        )
    )
    if existing is not None:
        return existing
    obj = models.CostCategory(**data)
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
    if payload.cost_category_id is None and not (payload.cost_category_name or "").strip():
        raise HTTPException(422, "Kostenart (ID oder Name) erforderlich")

    if (payload.cost_category_name or "").strip():
        # Kostenart entsteht automatisch (objektgebunden, find-or-create)
        cat = _get_or_create_category(db, payload.property_id, payload.cost_category_name.strip())
        cost_category_id = cat.id
    else:
        cost_category_id = payload.cost_category_id
        cat = db.get(models.CostCategory, cost_category_id)
        if cat is None:
            raise HTTPException(404, "Kostenart nicht gefunden")
        if cat.property_id != payload.property_id:
            raise HTTPException(409, "Kostenart gehört nicht zu diesem Objekt")

    exists = db.scalar(
        select(models.AllocationConfig).where(
            models.AllocationConfig.property_id == payload.property_id,
            models.AllocationConfig.cost_category_id == cost_category_id,
        )
    )
    if exists:
        raise HTTPException(409, "Umlage-Konfiguration existiert bereits")
    obj = models.AllocationConfig(
        property_id=payload.property_id,
        cost_category_id=cost_category_id,
        allocation_key=payload.allocation_key,
        sort_order=payload.sort_order,
    )
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
