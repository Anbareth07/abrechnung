"""API für Wasser (Plan B): Tarife, Hauptzählerstände und Berechnung."""

from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas.wasser import (
    WasserPriceCreate,
    WasserPriceRead,
    WasserPriceUpdate,
    WasserReadingCreate,
    WasserReadingRead,
    WasserReadingUpdate,
)
from ..services import wasser as wasser_service

router = APIRouter(prefix="/wasser", tags=["wasser"])

WASSER_KINDS = ("TRINKWASSER", "SCHMUTZWASSER", "NIEDERSCHLAGSWASSER", "GRUNDGEBUEHR")

# Standard-MwSt je Art: Trinkwasser 7 %, Schmutzwasser/Niederschlagswasser 0 %, Grundgebühr 7 %
DEFAULT_VAT = {
    "TRINKWASSER": Decimal("7.00"),
    "SCHMUTZWASSER": Decimal("0.00"),
    "NIEDERSCHLAGSWASSER": Decimal("0.00"),
    "GRUNDGEBUEHR": Decimal("7.00"),
}


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
            select(models.WasserPrice).where(
                models.WasserPrice.property_id == property_id,
                models.WasserPrice.kind == kind,
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


@router.get("/prices", response_model=list[WasserPriceRead])
def list_prices(property_id: int | None = None, db: Session = Depends(get_db)):
    query = select(models.WasserPrice)
    if property_id is not None:
        query = query.where(models.WasserPrice.property_id == property_id)
    return db.scalars(query.order_by(models.WasserPrice.kind, models.WasserPrice.valid_from)).all()


@router.post("/prices", response_model=WasserPriceRead, status_code=201)
def create_price(payload: WasserPriceCreate, db: Session = Depends(get_db)):
    if db.get(models.Property, payload.property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    if payload.kind not in WASSER_KINDS:
        raise HTTPException(422, "Unbekannte Tarifart")
    _check_contiguous(db, payload.property_id, payload.kind, payload.valid_from, payload.valid_to)
    data = payload.model_dump()
    if data.get("vat_rate") is None:
        data["vat_rate"] = DEFAULT_VAT[payload.kind]
    obj = models.WasserPrice(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/prices/{price_id}", response_model=WasserPriceRead)
def update_price(price_id: int, payload: WasserPriceUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.WasserPrice, price_id)
    if obj is None:
        raise HTTPException(404, "Tarifbestandteil nicht gefunden")
    data = payload.model_dump(exclude_unset=True)
    kind = data.get("kind", obj.kind)
    valid_from = data.get("valid_from", obj.valid_from)
    valid_to = data.get("valid_to", obj.valid_to)
    if kind not in WASSER_KINDS:
        raise HTTPException(422, "Unbekannte Tarifart")
    _check_contiguous(db, obj.property_id, kind, valid_from, valid_to, exclude_id=obj.id)
    for key, value in data.items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/prices/{price_id}", status_code=204)
def delete_price(price_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.WasserPrice, price_id)
    if obj is None:
        raise HTTPException(404, "Tarifbestandteil nicht gefunden")
    db.delete(obj)
    db.commit()


# --- Zählerstände ------------------------------------------------------------


@router.get("/readings", response_model=list[WasserReadingRead])
def list_readings(property_id: int | None = None, db: Session = Depends(get_db)):
    query = select(models.WasserReading)
    if property_id is not None:
        query = query.where(models.WasserReading.property_id == property_id)
    return db.scalars(query.order_by(models.WasserReading.reading_date)).all()


@router.post("/readings", response_model=WasserReadingRead, status_code=201)
def create_reading(payload: WasserReadingCreate, db: Session = Depends(get_db)):
    if db.get(models.Property, payload.property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    obj = models.WasserReading(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/readings/{reading_id}", response_model=WasserReadingRead)
def update_reading(reading_id: int, payload: WasserReadingUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.WasserReading, reading_id)
    if obj is None:
        raise HTTPException(404, "Zählerstand nicht gefunden")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/readings/{reading_id}", status_code=204)
def delete_reading(reading_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.WasserReading, reading_id)
    if obj is None:
        raise HTTPException(404, "Zählerstand nicht gefunden")
    db.delete(obj)
    db.commit()


# --- Berechnung --------------------------------------------------------------


@router.get("/{property_id}/plan")
def get_plan(property_id: int, db: Session = Depends(get_db)):
    """Plan A (Verbrauch je Wohnung) oder Plan B (Hauptzähler) für das Wasser-Modul."""
    if db.get(models.Property, property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    return {"plan": "A" if wasser_service.is_plan_a(db, property_id) else "B"}


@router.get("/{property_id}/berechnung")
def get_berechnung(property_id: int, von: str, bis: str, db: Session = Depends(get_db)):
    from datetime import date as _date

    if db.get(models.Property, property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    try:
        v = _date.fromisoformat(von)
        b = _date.fromisoformat(bis)
    except ValueError:
        raise HTTPException(422, "Ungültiges Datum")
    try:
        return wasser_service.berechnung(db, property_id, v, b)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
