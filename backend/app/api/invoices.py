from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas.invoice import InvoiceCreate, InvoiceRead, InvoiceUpdate

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=list[InvoiceRead])
def list_invoices(property_id: int | None = None, db: Session = Depends(get_db)):
    query = select(models.Invoice)
    if property_id is not None:
        query = query.where(models.Invoice.property_id == property_id)
    return db.scalars(query.order_by(models.Invoice.period_start.desc())).all()


@router.post("", response_model=InvoiceRead, status_code=201)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    if db.get(models.Property, payload.property_id) is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    if db.get(models.CostCategory, payload.cost_category_id) is None:
        raise HTTPException(404, "Kostenart nicht gefunden")

    obj = models.Invoice(**payload.model_dump(exclude={"items"}))
    db.add(obj)
    db.flush()
    for item in payload.items:
        db.add(models.InvoiceItem(invoice_id=obj.id, **item.model_dump()))
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Invoice, invoice_id)
    if obj is None:
        raise HTTPException(404, "Rechnung nicht gefunden")
    return obj


@router.patch("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(invoice_id: int, payload: InvoiceUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.Invoice, invoice_id)
    if obj is None:
        raise HTTPException(404, "Rechnung nicht gefunden")

    for key, value in payload.model_dump(exclude_unset=True, exclude={"items"}).items():
        setattr(obj, key, value)

    if payload.items is not None:
        for item in list(obj.items):
            db.delete(item)
        db.flush()
        for item in payload.items:
            db.add(models.InvoiceItem(invoice_id=obj.id, **item.model_dump()))

    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Invoice, invoice_id)
    if obj is None:
        raise HTTPException(404, "Rechnung nicht gefunden")
    db.delete(obj)
    db.commit()
