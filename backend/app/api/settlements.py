"""API für die Abrechnungsberechnung, den Vollständigkeits-Check und das Finalisieren."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..services.completeness import check_completeness
from ..services.engine import compute_settlement
from ..services.pdf import generate_tenant_pdf

router = APIRouter(prefix="/settlements", tags=["settlements"])


@router.get("/{property_id}/{year}")
def get_settlement(property_id: int, year: int, db: Session = Depends(get_db)):
    """Berechnete Nebenkostenabrechnung für ein Objekt und Jahr."""
    try:
        return compute_settlement(db, property_id, year)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{property_id}/{year}/completeness")
def get_completeness(property_id: int, year: int, db: Session = Depends(get_db)):
    """Liste fehlender Daten (Rechnungen, Zählerstände) für das Abrechnungsjahr."""
    return check_completeness(db, property_id, year)


@router.get("/{property_id}/{year}/tenants/{tenant_id}/pdf")
def get_tenant_pdf(property_id: int, year: int, tenant_id: int, db: Session = Depends(get_db)):
    """Mieter-PDF für die Jahresabrechnung."""
    try:
        pdf = generate_tenant_pdf(db, property_id, year, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Nebenkosten_{year}_{tenant_id}.pdf"'},
    )


@router.post("/{property_id}/{year}/finalize")
def finalize_settlement(property_id: int, year: int, db: Session = Depends(get_db)):
    """Speichert die berechnete Abrechnung als Snapshot (Status FINAL)."""
    try:
        result = compute_settlement(db, property_id, year)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    settlement = db.scalar(
        select(models.Settlement).where(
            models.Settlement.property_id == property_id,
            models.Settlement.year == year,
        )
    )
    if settlement is None:
        settlement = models.Settlement(property_id=property_id, year=year)
        db.add(settlement)
        db.flush()

    settlement.status = models.SettlementStatus.FINAL
    settlement.meta = {
        "total_wf": float(result.total_wf),
        "total_nf": float(result.total_nf),
        "water_price_per_m3": (
            float(result.water_price_per_m3) if result.water_price_per_m3 is not None else None
        ),
        "warnings": result.warnings,
    }

    for line in list(settlement.lines):
        db.delete(line)
    db.flush()

    for ln in result.tenant_lines:
        db.add(
            models.SettlementLine(
                settlement_id=settlement.id,
                tenant_id=ln.tenant_id,
                detail={
                    "tenant_name": ln.name,
                    "designation": ln.designation,
                    "living_area": float(ln.living_area),
                    "utility_area": float(ln.utility_area),
                    "tenant_days": ln.tenant_days,
                    "time_factor": float(ln.time_factor),
                    "advance_months": float(ln.advance_months),
                    "breakdown": {k: float(v) for k, v in ln.breakdown.items()},
                },
                total_costs=ln.total_costs,
                advance_total=ln.advance_total,
                saldo=ln.saldo,
            )
        )

    db.commit()
    return {
        "settlement_id": settlement.id,
        "property_id": property_id,
        "year": year,
        "status": settlement.status.value,
        "tenant_count": len(result.tenant_lines),
        "warnings": result.warnings,
    }
