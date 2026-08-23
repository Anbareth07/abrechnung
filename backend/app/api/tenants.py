from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas.property import AdvanceCreate, TenantCreate, TenantRead, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _set_advances(db: Session, tenant: models.Tenant, advances: list[AdvanceCreate]) -> None:
    """Ersetzt die Vorauszahlungs-Zeiträume und setzt die aktuelle Vorauszahlung."""
    for adv in list(tenant.advance_payments):
        db.delete(adv)
    db.flush()
    for adv in advances:
        db.add(
            models.AdvancePayment(
                tenant_id=tenant.id, valid_from=adv.valid_from, amount=adv.amount
            )
        )
    if advances:
        tenant.monthly_advance = max(advances, key=lambda a: a.valid_from).amount


@router.get("", response_model=list[TenantRead])
def list_tenants(
    lease_unit_id: int | None = None,
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = select(models.Tenant)
    if lease_unit_id is not None:
        query = query.where(models.Tenant.lease_unit_id == lease_unit_id)
    elif property_id is not None:
        query = query.join(models.LeaseUnit).where(models.LeaseUnit.property_id == property_id)
    return db.scalars(query.order_by(models.Tenant.name)).all()


@router.post("", response_model=TenantRead, status_code=201)
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    if db.get(models.LeaseUnit, payload.lease_unit_id) is None:
        raise HTTPException(404, "Mieteinheit nicht gefunden")
    obj = models.Tenant(**payload.model_dump(exclude={"advances"}))
    db.add(obj)
    db.flush()
    _set_advances(db, obj, payload.advances)
    db.commit()
    db.refresh(obj)
    list(obj.advance_payments)  # Relationship für die Antwort laden
    return obj


@router.get("/{tenant_id}", response_model=TenantRead)
def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Tenant, tenant_id)
    if obj is None:
        raise HTTPException(404, "Mieter nicht gefunden")
    return obj


@router.patch("/{tenant_id}", response_model=TenantRead)
def update_tenant(tenant_id: int, payload: TenantUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.Tenant, tenant_id)
    if obj is None:
        raise HTTPException(404, "Mieter nicht gefunden")
    for key, value in payload.model_dump(exclude_unset=True, exclude={"advances"}).items():
        setattr(obj, key, value)
    if payload.advances is not None:
        _set_advances(db, obj, payload.advances)
    db.commit()
    db.refresh(obj)
    list(obj.advance_payments)
    return obj


@router.delete("/{tenant_id}", status_code=204)
def delete_tenant(tenant_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Tenant, tenant_id)
    if obj is None:
        raise HTTPException(404, "Mieter nicht gefunden")
    db.delete(obj)
    db.commit()
