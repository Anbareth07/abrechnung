"""API für Techem-Heizkostenblätter je Objekt und Heizperiode (von–bis)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas.techem import TechemSheetRead, TechemSheetWrite
from ..services import strom as strom_service

router = APIRouter(prefix="/techem", tags=["techem"])


def _parse_dates(von: str, bis: str) -> tuple[date, date]:
    try:
        v = date.fromisoformat(von)
        b = date.fromisoformat(bis)
    except ValueError:
        raise HTTPException(422, "Ungültiges Datum")
    if v > b:
        raise HTTPException(422, "Zeitraum ungültig: von darf nicht nach bis liegen")
    return v, b


def _sheet_dict(record, db: Session, property_id: int, von: date, bis: date) -> dict:
    """Blatt mit automatisch berechnetem Heizstromanteil aus dem Unterzähler."""
    strom = strom_service.unterzaehler_kosten(db, property_id, von, bis)
    return {
        "id": record.id if record else None,
        "property_id": property_id,
        "von": von.isoformat(),
        "bis": bis.isoformat(),
        "strom_kwh": strom["kwh"],
        "strom_netto": strom["netto"],
        "strom_vat": strom["vat"],
        "strom_brutto": strom["brutto"],
        "gas_kwh": float(record.gas_kwh) if record else 0.0,
        "gas_cost": float(record.gas_cost) if record else 0.0,
        "maintenance_cost": float(record.maintenance_cost) if record else 0.0,
        "chimney_cost": float(record.chimney_cost) if record else 0.0,
        "notes": record.notes if record else None,
    }


@router.get("", response_model=list[TechemSheetRead])
def list_techem_sheets(property_id: int | None = None, db: Session = Depends(get_db)):
    query = select(models.TechemRecord)
    if property_id is not None:
        query = query.where(models.TechemRecord.property_id == property_id)
    records = db.scalars(query.order_by(models.TechemRecord.von.desc())).all()
    return [_sheet_dict(r, db, r.property_id, r.von, r.bis) for r in records]


@router.get("/sheet", response_model=TechemSheetRead)
def get_techem_sheet(property_id: int, von: str, bis: str, db: Session = Depends(get_db)):
    if db.get(models.Property, property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    v, b = _parse_dates(von, bis)
    record = db.scalar(
        select(models.TechemRecord).where(
            models.TechemRecord.property_id == property_id,
            models.TechemRecord.von == v,
            models.TechemRecord.bis == b,
        )
    )
    return _sheet_dict(record, db, property_id, v, b)


@router.put("/sheet", response_model=TechemSheetRead)
def save_techem_sheet(payload: TechemSheetWrite, db: Session = Depends(get_db)):
    if db.get(models.Property, payload.property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    record = db.scalar(
        select(models.TechemRecord).where(
            models.TechemRecord.property_id == payload.property_id,
            models.TechemRecord.von == payload.von,
            models.TechemRecord.bis == payload.bis,
        )
    )
    if record is None:
        record = models.TechemRecord(
            property_id=payload.property_id, von=payload.von, bis=payload.bis
        )
        db.add(record)
    record.gas_kwh = payload.gas_kwh
    record.gas_cost = payload.gas_cost
    record.maintenance_cost = payload.maintenance_cost
    record.chimney_cost = payload.chimney_cost
    record.notes = payload.notes
    db.commit()
    db.refresh(record)
    return _sheet_dict(record, db, payload.property_id, payload.von, payload.bis)


@router.delete("/{record_id}", status_code=204)
def delete_techem_record(record_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.TechemRecord, record_id)
    if obj is None:
        raise HTTPException(404, "Heizkosten-Blatt nicht gefunden")
    db.delete(obj)
    db.commit()
