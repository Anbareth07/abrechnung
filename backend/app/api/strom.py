"""API für Strom: Tarifbestandteile, Zählerstände und Berechnung."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas.strom import (
    StromPriceCreate,
    StromPriceRead,
    StromPriceUpdate,
    StromReadingCreate,
    StromReadingRead,
    StromReadingUpdate,
)
from ..services import strom as strom_service

router = APIRouter(prefix="/strom", tags=["strom"])

STROM_KINDS = ("GRUNDGEBUEHR", "ARBEITSPREIS", "STROMSTEUER")
ROLES = ("HAUPTZAEHLER", "UNTERZAEHLER")


def _check_contiguous(
    db: Session,
    property_id: int,
    kind: str,
    new_from,
    new_to,
    exclude_id: int | None = None,
) -> None:
    """Stellt sicher, dass die Gültigkeitszeiträume einer Art lückenlos sind."""
    if new_from > new_to:
        raise HTTPException(422, "Gültig-bis muss nach Gültig-von liegen")
    periods = [
        (o.valid_from, o.valid_to)
        for o in db.scalars(
            select(models.StromPrice).where(
                models.StromPrice.property_id == property_id,
                models.StromPrice.kind == kind,
            )
        ).all()
        if o.id != exclude_id
    ]
    periods.append((new_from, new_to))
    periods.sort()
    for i in range(len(periods) - 1):
        f, t = periods[i]
        nf, nt = periods[i + 1]
        if nt <= t:
            raise HTTPException(422, "Zeiträume dürfen sich nicht überlappen")
        if nf != t + timedelta(days=1):
            raise HTTPException(422, "Zeiträume müssen lückenlos aneinander anschließen (keine Lücken)")


# --- Tarifbestandteile -------------------------------------------------------


@router.get("/prices", response_model=list[StromPriceRead])
def list_prices(property_id: int | None = None, db: Session = Depends(get_db)):
    query = select(models.StromPrice)
    if property_id is not None:
        query = query.where(models.StromPrice.property_id == property_id)
    return db.scalars(query.order_by(models.StromPrice.kind, models.StromPrice.valid_from)).all()


@router.post("/prices", response_model=StromPriceRead, status_code=201)
def create_price(payload: StromPriceCreate, db: Session = Depends(get_db)):
    if db.get(models.Property, payload.property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    if payload.kind not in STROM_KINDS:
        raise HTTPException(422, "Unbekannte Tarifart")
    _check_contiguous(db, payload.property_id, payload.kind, payload.valid_from, payload.valid_to)
    obj = models.StromPrice(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/prices/{price_id}", response_model=StromPriceRead)
def update_price(price_id: int, payload: StromPriceUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.StromPrice, price_id)
    if obj is None:
        raise HTTPException(404, "Tarifbestandteil nicht gefunden")
    data = payload.model_dump(exclude_unset=True)
    kind = data.get("kind", obj.kind)
    valid_from = data.get("valid_from", obj.valid_from)
    valid_to = data.get("valid_to", obj.valid_to)
    if kind not in STROM_KINDS:
        raise HTTPException(422, "Unbekannte Tarifart")
    _check_contiguous(db, obj.property_id, kind, valid_from, valid_to, exclude_id=obj.id)
    for key, value in data.items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/prices/{price_id}", status_code=204)
def delete_price(price_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.StromPrice, price_id)
    if obj is None:
        raise HTTPException(404, "Tarifbestandteil nicht gefunden")
    db.delete(obj)
    db.commit()


# --- Zählerstände ------------------------------------------------------------


@router.get("/readings", response_model=list[StromReadingRead])
def list_readings(
    property_id: int | None = None,
    role: str | None = None,
    db: Session = Depends(get_db),
):
    query = select(models.StromReading)
    if property_id is not None:
        query = query.where(models.StromReading.property_id == property_id)
    if role is not None:
        query = query.where(models.StromReading.role == role)
    return db.scalars(query.order_by(models.StromReading.reading_date)).all()


@router.post("/readings", response_model=StromReadingRead, status_code=201)
def create_reading(payload: StromReadingCreate, db: Session = Depends(get_db)):
    if db.get(models.Property, payload.property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    if payload.role not in ROLES:
        raise HTTPException(422, "Unbekannte Zählerrolle")
    obj = models.StromReading(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/readings/{reading_id}", response_model=StromReadingRead)
def update_reading(reading_id: int, payload: StromReadingUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.StromReading, reading_id)
    if obj is None:
        raise HTTPException(404, "Zählerstand nicht gefunden")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/readings/{reading_id}", status_code=204)
def delete_reading(reading_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.StromReading, reading_id)
    if obj is None:
        raise HTTPException(404, "Zählerstand nicht gefunden")
    db.delete(obj)
    db.commit()


# --- Berechnung & Techem -----------------------------------------------------


@router.get("/{property_id}/berechnung")
def get_berechnung(
    property_id: int,
    von: str,
    bis: str,
    db: Session = Depends(get_db),
):
    from datetime import date as _date

    if db.get(models.Property, property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    try:
        v = _date.fromisoformat(von)
        b = _date.fromisoformat(bis)
    except ValueError:
        raise HTTPException(422, "Ungültiges Datum")
    try:
        return strom_service.berechnung(db, property_id, v, b)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
