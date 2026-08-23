from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas.property import (
    AdvanceCreate,
    MonthlyCostCreate,
    TenantCreate,
    TenantRead,
    TenantUpdate,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _set_advances(db: Session, tenant: models.Tenant, advances: list[AdvanceCreate]) -> None:
    """Ersetzt die Vorauszahlungs-Zeiträume und setzt die aktuelle Vorauszahlung.

    Änderungen der Vorauszahlung sind nur zum Monatsanfang (1. des Monats)
    zulässig – die erste/früheste Vorauszahlung (z. B. beim Einzug) ist davon
    ausgenommen.
    """
    sorted_adv = sorted(advances, key=lambda a: a.valid_from)
    for i, adv in enumerate(sorted_adv):
        if i > 0 and adv.valid_from.day != 1:
            raise HTTPException(
                422,
                "Vorauszahlungsänderungen sind nur zum Monatsanfang (1. des Monats) zulässig",
            )
    tenant.advance_payments.clear()  # cascade delete-orphan
    db.flush()
    for adv in advances:
        tenant.advance_payments.append(
            models.AdvancePayment(valid_from=adv.valid_from, amount=adv.amount)
        )
    if advances:
        tenant.monthly_advance = max(advances, key=lambda a: a.valid_from).amount


def _set_monthly_costs(
    db: Session, tenant: models.Tenant, costs: list[MonthlyCostCreate]
) -> None:
    """Ersetzt die zusätzlichen Monatskosten (nur informativ, nicht umlagefähig)."""
    tenant.monthly_costs.clear()  # cascade delete-orphan
    db.flush()
    for cost in costs:
        tenant.monthly_costs.append(
            models.MonthlyCost(name=cost.name, amount=cost.amount)
        )


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
    obj = models.Tenant(**payload.model_dump(exclude={"advances", "monthly_costs"}))
    db.add(obj)
    db.flush()
    _set_advances(db, obj, payload.advances)
    _set_monthly_costs(db, obj, payload.monthly_costs)
    db.commit()
    db.refresh(obj)
    list(obj.advance_payments)  # Relationship für die Antwort laden
    list(obj.monthly_costs)
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
    for key, value in payload.model_dump(
        exclude_unset=True, exclude={"advances", "monthly_costs"}
    ).items():
        setattr(obj, key, value)
    if payload.advances is not None:
        _set_advances(db, obj, payload.advances)
    if payload.monthly_costs is not None:
        _set_monthly_costs(db, obj, payload.monthly_costs)
    db.commit()
    db.refresh(obj)
    list(obj.advance_payments)
    list(obj.monthly_costs)
    return obj


@router.delete("/{tenant_id}", status_code=204)
def delete_tenant(tenant_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Tenant, tenant_id)
    if obj is None:
        raise HTTPException(404, "Mieter nicht gefunden")
    db.delete(obj)
    db.commit()
