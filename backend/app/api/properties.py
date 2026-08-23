from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas.property import PropertyCreate, PropertyRead, PropertyUpdate

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=list[PropertyRead])
def list_properties(db: Session = Depends(get_db)):
    return db.scalars(select(models.Property).order_by(models.Property.name)).all()


@router.post("", response_model=PropertyRead, status_code=201)
def create_property(payload: PropertyCreate, db: Session = Depends(get_db)):
    obj = models.Property(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{property_id}", response_model=PropertyRead)
def get_property(property_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Property, property_id)
    if obj is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    return obj


@router.patch("/{property_id}", response_model=PropertyRead)
def update_property(property_id: int, payload: PropertyUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.Property, property_id)
    if obj is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{property_id}", status_code=204)
def delete_property(property_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Property, property_id)
    if obj is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    db.delete(obj)
    db.commit()
