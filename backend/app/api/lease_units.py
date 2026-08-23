from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas.property import LeaseUnitCreate, LeaseUnitRead, LeaseUnitUpdate

router = APIRouter(prefix="/lease-units", tags=["lease-units"])


@router.get("", response_model=list[LeaseUnitRead])
def list_lease_units(property_id: int | None = None, db: Session = Depends(get_db)):
    query = select(models.LeaseUnit)
    if property_id is not None:
        query = query.where(models.LeaseUnit.property_id == property_id)
    return db.scalars(query.order_by(models.LeaseUnit.id)).all()


@router.post("", response_model=LeaseUnitRead, status_code=201)
def create_lease_unit(payload: LeaseUnitCreate, db: Session = Depends(get_db)):
    if db.get(models.Property, payload.property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    obj = models.LeaseUnit(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{lease_unit_id}", response_model=LeaseUnitRead)
def get_lease_unit(lease_unit_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.LeaseUnit, lease_unit_id)
    if obj is None:
        raise HTTPException(404, "Mieteinheit nicht gefunden")
    return obj


@router.patch("/{lease_unit_id}", response_model=LeaseUnitRead)
def update_lease_unit(lease_unit_id: int, payload: LeaseUnitUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.LeaseUnit, lease_unit_id)
    if obj is None:
        raise HTTPException(404, "Mieteinheit nicht gefunden")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{lease_unit_id}", status_code=204)
def delete_lease_unit(lease_unit_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.LeaseUnit, lease_unit_id)
    if obj is None:
        raise HTTPException(404, "Mieteinheit nicht gefunden")
    db.delete(obj)
    db.commit()
