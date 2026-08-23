from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas.meter import (
    MeterCreate,
    MeterRead,
    MeterReadingCreate,
    MeterReadingRead,
    MeterReadingUpdate,
    MeterUpdate,
)

router = APIRouter(prefix="/meters", tags=["meters"])

reading_router = APIRouter(prefix="/meter-readings", tags=["meter-readings"])


@router.get("", response_model=list[MeterRead])
def list_meters(
    property_id: int | None = None,
    lease_unit_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = select(models.Meter)
    if property_id is not None:
        query = query.where(models.Meter.property_id == property_id)
    if lease_unit_id is not None:
        query = query.where(models.Meter.lease_unit_id == lease_unit_id)
    return db.scalars(query.order_by(models.Meter.id)).all()


@router.post("", response_model=MeterRead, status_code=201)
def create_meter(payload: MeterCreate, db: Session = Depends(get_db)):
    obj = models.Meter(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{meter_id}", response_model=MeterRead)
def get_meter(meter_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Meter, meter_id)
    if obj is None:
        raise HTTPException(404, "Zähler nicht gefunden")
    return obj


@router.patch("/{meter_id}", response_model=MeterRead)
def update_meter(meter_id: int, payload: MeterUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.Meter, meter_id)
    if obj is None:
        raise HTTPException(404, "Zähler nicht gefunden")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{meter_id}", status_code=204)
def delete_meter(meter_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Meter, meter_id)
    if obj is None:
        raise HTTPException(404, "Zähler nicht gefunden")
    db.delete(obj)
    db.commit()


@reading_router.get("", response_model=list[MeterReadingRead])
def list_readings(meter_id: int | None = None, db: Session = Depends(get_db)):
    query = select(models.MeterReading)
    if meter_id is not None:
        query = query.where(models.MeterReading.meter_id == meter_id)
    return db.scalars(query.order_by(models.MeterReading.reading_date)).all()


@reading_router.post("", response_model=MeterReadingRead, status_code=201)
def create_reading(payload: MeterReadingCreate, db: Session = Depends(get_db)):
    if db.get(models.Meter, payload.meter_id) is None:
        raise HTTPException(404, "Zähler nicht gefunden")
    obj = models.MeterReading(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@reading_router.patch("/{reading_id}", response_model=MeterReadingRead)
def update_reading(reading_id: int, payload: MeterReadingUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.MeterReading, reading_id)
    if obj is None:
        raise HTTPException(404, "Zählerstand nicht gefunden")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@reading_router.delete("/{reading_id}", status_code=204)
def delete_reading(reading_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.MeterReading, reading_id)
    if obj is None:
        raise HTTPException(404, "Zählerstand nicht gefunden")
    db.delete(obj)
    db.commit()
