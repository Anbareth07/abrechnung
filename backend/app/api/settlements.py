"""API für die Abrechnungsberechnung, den Vollständigkeits-Check und das Finalisieren."""

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas.category import NoInvoiceCreate
from ..services.completeness import check_completeness
from ..services.engine import compute_settlement
from ..services.pdf import generate_tenant_pdf

router = APIRouter(prefix="/settlements", tags=["settlements"])


def _safe_filename(name: str) -> str:
    """Wandelt einen Namen in einen dateinamentauglichen String (ASCII, Unterstriche)."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return text or "Export"


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


def _no_invoice_dict(flag: models.CategoryNoInvoice) -> dict:
    return {
        "id": flag.id,
        "property_id": flag.property_id,
        "cost_category_id": flag.cost_category_id,
        "year": flag.year,
        "category_name": flag.cost_category.name,
    }


@router.get("/{property_id}/{year}/no-invoices")
def list_no_invoices(property_id: int, year: int, db: Session = Depends(get_db)):
    """Kostenarten, die für das Jahr als "keine Rechnung" markiert sind."""
    flags = db.scalars(
        select(models.CategoryNoInvoice).where(
            models.CategoryNoInvoice.property_id == property_id,
            models.CategoryNoInvoice.year == year,
        )
    ).all()
    return [_no_invoice_dict(f) for f in flags]


@router.post("/{property_id}/{year}/no-invoices", status_code=201)
def mark_no_invoice(
    property_id: int, year: int, payload: NoInvoiceCreate, db: Session = Depends(get_db)
):
    """Markiert eine Kostenart für das Jahr als "keine Rechnung"."""
    cat = db.get(models.CostCategory, payload.cost_category_id)
    if cat is None or cat.property_id != property_id:
        raise HTTPException(404, "Kostenart nicht gefunden")
    flag = db.scalar(
        select(models.CategoryNoInvoice).where(
            models.CategoryNoInvoice.property_id == property_id,
            models.CategoryNoInvoice.cost_category_id == payload.cost_category_id,
            models.CategoryNoInvoice.year == year,
        )
    )
    if flag is None:
        flag = models.CategoryNoInvoice(
            property_id=property_id,
            cost_category_id=payload.cost_category_id,
            year=year,
        )
        db.add(flag)
        db.commit()
        db.refresh(flag)
    return _no_invoice_dict(flag)


@router.delete("/{property_id}/{year}/no-invoices/{flag_id}", status_code=204)
def unmark_no_invoice(flag_id: int, db: Session = Depends(get_db)):
    """Entfernt die "keine Rechnung"-Markierung."""
    flag = db.get(models.CategoryNoInvoice, flag_id)
    if flag is None:
        raise HTTPException(404, "Markierung nicht gefunden")
    db.delete(flag)
    db.commit()


@router.get("/{property_id}/{year}/tenants/{tenant_id}/pdf")
def get_tenant_pdf(property_id: int, year: int, tenant_id: int, db: Session = Depends(get_db)):
    """Mieter-PDF für die Jahresabrechnung (nur Tabelle, Querformat)."""
    try:
        pdf = generate_tenant_pdf(db, property_id, year, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    prop = db.get(models.Property, property_id)
    tenant = db.get(models.Tenant, tenant_id)
    prop_name = _safe_filename(prop.name) if prop else "Objekt"
    tenant_name = _safe_filename(tenant.name) if tenant else "Mieter"
    filename = f"Nebenkosten_{year}_{tenant_name}_{prop_name}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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


@router.get("/{property_id}/{year}/finalized")
def get_finalized_settlement(property_id: int, year: int, db: Session = Depends(get_db)):
    """Gibt den finalisierten Snapshot einer Abrechnung zurück (falls vorhanden).

    Der Snapshot bleibt nach späteren Datenänderungen unverändert und kann so
    mit der live berechneten Abrechnung verglichen werden.
    """
    prop = db.get(models.Property, property_id)
    if prop is None:
        raise HTTPException(404, "Objekt nicht gefunden")
    settlement = db.scalar(
        select(models.Settlement).where(
            models.Settlement.property_id == property_id,
            models.Settlement.year == year,
        )
    )
    if settlement is None or settlement.status != models.SettlementStatus.FINAL:
        raise HTTPException(404, "Noch nicht finalisiert")

    cats = db.execute(
        select(models.CostCategory).where(models.CostCategory.property_id == property_id)
    ).scalars().all()
    names = {c.code: c.name for c in cats}
    # Vom Engine erzeugte Sondercodes (Wasser) mit sprechenden Namen ergänzen
    names.setdefault("WASSER_GARTEN", "Wasserverbrauch Garten")
    names.setdefault("WASSER_VERBRAUCH", "Wasserkosten (Verbrauch)")
    return {
        "property_id": property_id,
        "property_name": prop.name,
        "year": year,
        "status": settlement.status.value,
        "computed_at": (
            settlement.computed_at.isoformat() if settlement.computed_at is not None else None
        ),
        "meta": settlement.meta,
        "category_names": names,
        "tenant_lines": [
            {
                "tenant_id": line.tenant_id,
                "name": line.detail.get("tenant_name", ""),
                "designation": line.detail.get("designation", ""),
                "living_area": line.detail.get("living_area", 0),
                "utility_area": line.detail.get("utility_area", 0),
                "tenant_days": line.detail.get("tenant_days", 0),
                "time_factor": line.detail.get("time_factor", 0),
                "advance_months": line.detail.get("advance_months", 0),
                "breakdown": line.detail.get("breakdown", {}),
                "total_costs": float(line.total_costs),
                "advance_total": float(line.advance_total),
                "saldo": float(line.saldo),
            }
            for line in settlement.lines
        ],
    }
