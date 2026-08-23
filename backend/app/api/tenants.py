from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas.property import TenantCreate, TenantRead, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])


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
    obj = models.Tenant(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
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
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{tenant_id}", status_code=204)
def delete_tenant(tenant_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Tenant, tenant_id)
    if obj is None:
        raise HTTPException(404, "Mieter nicht gefunden")
    db.delete(obj)
    db.commit()
