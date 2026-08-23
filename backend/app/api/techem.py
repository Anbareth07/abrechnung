from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas.techem import TechemRecordCreate, TechemRecordRead, TechemRecordUpdate

router = APIRouter(prefix="/techem", tags=["techem"])


@router.get("", response_model=list[TechemRecordRead])
def list_techem_records(property_id: int | None = None, db: Session = Depends(get_db)):
    query = select(models.TechemRecord)
    if property_id is not None:
        query = query.where(models.TechemRecord.property_id == property_id)
    return db.scalars(query.order_by(models.TechemRecord.invoice_date.desc())).all()


@router.post("", response_model=TechemRecordRead, status_code=201)
def create_techem_record(payload: TechemRecordCreate, db: Session = Depends(get_db)):
    if db.get(models.Property, payload.property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    obj = models.TechemRecord(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{record_id}", response_model=TechemRecordRead)
def update_techem_record(record_id: int, payload: TechemRecordUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.TechemRecord, record_id)
    if obj is None:
        raise HTTPException(404, "Techem-Eintrag nicht gefunden")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{record_id}", status_code=204)
def delete_techem_record(record_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.TechemRecord, record_id)
    if obj is None:
        raise HTTPException(404, "Techem-Eintrag nicht gefunden")
    db.delete(obj)
    db.commit()
