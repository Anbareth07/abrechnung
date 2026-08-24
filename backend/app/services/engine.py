"""Orchestrierung der Jahresabrechnung: Flächenumlage + Wasser + Saldo."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..models.enums import AllocationKey, InvoiceKind
from . import prorata
from . import strom as strom_service
from . import wasser as wasser_service
from .prorata import ZERO, days_in_year, pro_rata_amount, year_bounds
from .water import WaterResult, compute_water_consumption, unit_water_consumption

CENTS = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    """Rundet auf 2 Nachkommastellen (kaufmännisch)."""
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


@dataclass
class CategoryLine:
    code: str
    name: str
    allocation_key: str
    year_cost: Decimal
    cost_category_id: Optional[int] = None


@dataclass
class CategoryShare:
    """Eine Kostenzeile in der Mieteransicht (Gesamt/Basis/Ihr Anteil/Betrag)."""

    code: str
    name: str
    allocation_key: str
    year_cost: Decimal  # Gesamtkosten der Kostenart
    basis_label: str  # z. B. "Wohnfläche", "Nutzfläche", "Verbrauch", "Wohnung"
    basis_total: Optional[Decimal]  # Gesamt-Basis (z. B. m² gesamt)
    basis_share: Optional[Decimal]  # Anteil des Mieters an der Basis
    days: int  # bewohnte Tage im Abrechnungsjahr
    amount: Decimal  # Kostenanteil des Mieters
    info: list[dict] = field(default_factory=list)  # strukturierte Hover-Info


@dataclass
class TenantLine:
    tenant_id: int
    name: str
    lease_unit_id: int
    designation: str
    living_area: Decimal
    utility_area: Decimal
    tenant_days: int
    time_factor: Decimal
    advance_months: Decimal
    # Für den Mieter relevanter Zeitraum im Abrechnungsjahr (bei Auszug/Wechsel anteilig)
    period_start: date
    period_end: date
    breakdown: dict[str, Decimal] = field(default_factory=dict)
    details: list[CategoryShare] = field(default_factory=list)
    # Vorauszahlungs-Zeiträume im Jahr (für Tooltip/Hover)
    advance_breakdown: list[dict] = field(default_factory=list)
    total_costs: Decimal = ZERO
    advance_total: Decimal = ZERO
    saldo: Decimal = ZERO


@dataclass
class SettlementResult:
    property_id: int
    property_name: str
    year: int
    days_in_year: int
    total_wf: Decimal
    total_nf: Decimal
    category_lines: list[CategoryLine] = field(default_factory=list)
    tenant_lines: list[TenantLine] = field(default_factory=list)
    water: Optional[WaterResult] = None
    water_total_cost: Decimal = ZERO
    water_price_per_m3: Optional[Decimal] = None
    garden_water_cost: Decimal = ZERO
    unallocated_water: Decimal = ZERO
    warnings: list[str] = field(default_factory=list)


def _months_between(start: date, end: date) -> Decimal:
    """Anzahl Kalendermonate zwischen start und end (inklusive).

    Volle Kalendermonate zählen als 1, Teilmonate anteilig (Tage im Monat).
    Z. B. 01.07.–31.12. = 6 Monate, 15.03.–30.06. = 3 + 17/31 Monate.
    """
    total = ZERO
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        m_start = date(y, m, 1)
        m_end = date(y, m, monthrange(y, m)[1])
        seg_start = max(start, m_start)
        seg_end = min(end, m_end)
        if seg_start <= seg_end:
            days_in_month = monthrange(y, m)[1]
            total += Decimal((seg_end - seg_start).days + 1) / Decimal(days_in_month)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return total


def _advance_total(
    tenant: models.Tenant, year: int, occ_start: date, occ_end: date
) -> Decimal:
    """Monatliche Vorauszahlung für das Abrechnungsjahr.

    Berechnung nach KALENDERMONATEN (nicht nach Tagen): ein voller Monat zählt
    als 1 Monat, Teilmonate anteilig. Ohne Vorauszahlungs-Zeiträume wird die
    Einzel-Vorauszahlung (monthly_advance) über die Mietdauer angesetzt.
    """
    payments = sorted(tenant.advance_payments or [], key=lambda p: p.valid_from)
    if not payments:
        return tenant.monthly_advance * _months_between(occ_start, occ_end)
    total = ZERO
    for i, p in enumerate(payments):
        seg_end = (
            payments[i + 1].valid_from - timedelta(days=1) if i + 1 < len(payments) else None
        )
        start = max(p.valid_from, occ_start)
        end = min(seg_end or occ_end, occ_end)
        if start <= end:
            total += p.amount * _months_between(start, end)
    return total


def _advance_breakdown(
    tenant: models.Tenant, year: int, occ_start: date, occ_end: date
) -> list[dict]:
    """Vorauszahlungs-Zeiträume im Abrechnungsjahr (für die Hover-Anzeige).

    Gleiche Segmentierung wie `_advance_total`: ein Eintrag je Vorauszahlungs-
    Zeitraum (gültig ab) mit Start/Ende, Monatsbetrag und Monatsanteilen.
    """
    payments = sorted(tenant.advance_payments or [], key=lambda p: p.valid_from)
    if not payments:
        return [
            {
                "valid_from": occ_start,
                "valid_to": occ_end,
                "amount": tenant.monthly_advance,
                "days": (occ_end - occ_start).days + 1,
                "months": _months_between(occ_start, occ_end),
            }
        ]
    segs: list[dict] = []
    for i, p in enumerate(payments):
        seg_end = (
            payments[i + 1].valid_from - timedelta(days=1) if i + 1 < len(payments) else None
        )
        start = max(p.valid_from, occ_start)
        end = min(seg_end or occ_end, occ_end)
        if start <= end:
            segs.append(
                {
                    "valid_from": start,
                    "valid_to": end,
                    "amount": p.amount,
                    "days": (end - start).days + 1,
                    "months": _months_between(start, end),
                }
            )
    return segs


def _recurring_year_cost(invoices: list, year: int) -> Decimal:
    """Jahreskosten für wiederkehrende Rechnungen (Grundsteuer).

    Grundsteuer gilt ab dem Bescheidsdatum (valid_from) mit einem Jahresbetrag,
    bis ein neuer Bescheid erfasst wird. Mehrere Bescheide teilen das Jahr an
    ihren Stichtagen; der jeweils jüngste Bescheid ist bis zum nächsten gültig.
    """
    ys, ye = year_bounds(year)
    diy = days_in_year(year)
    recs = sorted(
        (inv for inv in invoices if inv.valid_from is not None),
        key=lambda i: i.valid_from,
    )
    if not recs:
        return ZERO

    bounds = sorted(
        {ys}
        | {inv.valid_from for inv in recs if ys <= inv.valid_from <= ye}
        | {ye + timedelta(days=1)}
    )
    total = ZERO
    for i in range(len(bounds) - 1):
        seg_start = bounds[i]
        seg_end = bounds[i + 1] - timedelta(days=1)
        if seg_start > seg_end:
            continue
        active = None
        for inv in recs:
            if inv.valid_from <= seg_start:
                active = inv
        if active is None or active.annual_amount is None:
            continue
        days = (seg_end - seg_start).days + 1
        total += active.annual_amount * (Decimal(days) / Decimal(diy))
    return total


def _category_year_cost(invoices: list, year: int) -> Decimal:
    """Jahreskosten einer Kostenart aus den (objektweiten) Rechnungen.

    Wiederkehrende Grundsteuer über valid_from/Jahresbetrag; alle übrigen
    Rechnungen anteilig über ihre Positionen.
    """
    total = _recurring_year_cost(invoices, year)
    for inv in invoices:
        if inv.kind == InvoiceKind.GRUNDSTEUER and inv.valid_from is not None:
            continue
        for item in inv.items:
            total += pro_rata_amount(item.gross_amount, item.from_date, item.to_date, year)
    return total


def _append_strom_line(category_lines: list, configs: list, strom_brutto: Decimal) -> None:
    """Eigene 'Strom'-Zeile (Umlageschlüssel einer 'Strom'-Kostenart, sonst Wohnfläche)."""
    strom_cfg = next(
        (c for c in configs if (c.cost_category.name or "").strip().lower() == "strom"), None
    )
    strom_key = strom_cfg.allocation_key.value if strom_cfg else AllocationKey.WF.value
    category_lines.append(CategoryLine("STROM", "Strom", strom_key, strom_brutto))


def _fmt_de(value: Decimal, digits: int = 2) -> str:
    """Dezimalzahl deutsch formatieren (Tausenderpunkt, Dezimalkomma)."""
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _money_de(value: Decimal) -> str:
    return f"{_fmt_de(value, 2)} €"


def compute_settlement(session: Session, property_id: int, year: int) -> SettlementResult:
    """Berechnet die komplette Nebenkostenabrechnung für ein Objekt und Jahr."""
    prop = session.get(models.Property, property_id)
    if prop is None:
        raise ValueError(f"Property {property_id} nicht gefunden")

    ys, ye = year_bounds(year)
    diy = days_in_year(year)
    warnings: list[str] = []

    units = session.execute(
        select(models.LeaseUnit).where(models.LeaseUnit.property_id == property_id)
    ).scalars().all()
    total_wf = sum((u.living_area for u in units), ZERO)
    total_nf = sum((u.utility_area for u in units), ZERO)

    tenants = session.execute(
        select(models.Tenant)
        .join(models.LeaseUnit)
        .where(models.LeaseUnit.property_id == property_id)
    ).scalars().all()

    active: list[tuple[models.Tenant, int]] = []
    for t in tenants:
        start = max(t.move_in, ys)
        end = min(t.move_out, ye) if t.move_out else ye
        if start <= end:
            active.append((t, (end - start).days + 1))

    configs = session.execute(
        select(models.AllocationConfig)
        .where(models.AllocationConfig.property_id == property_id)
        .order_by(models.AllocationConfig.sort_order)
    ).scalars().all()

    invoices = session.execute(
        select(models.Invoice).where(models.Invoice.property_id == property_id)
    ).scalars().all()
    # Objektweite Rechnungen je Kostenart + wohneinheitenbezogene Kosten je Einheit
    invoices_by_cat: dict[int, list[models.Invoice]] = {}
    unit_costs: dict[tuple[int, int], Decimal] = {}  # (lease_unit_id, cost_category_id) -> Betrag
    for inv in invoices:
        if inv.lease_unit_id is not None:
            for item in inv.items:
                val = pro_rata_amount(item.gross_amount, item.from_date, item.to_date, year)
                key = (inv.lease_unit_id, inv.cost_category_id)
                unit_costs[key] = unit_costs.get(key, ZERO) + val
        else:
            invoices_by_cat.setdefault(inv.cost_category_id, []).append(inv)

    category_lines: list[CategoryLine] = []
    # Code-/Namens-Zuordnung über ALLE Kostenarten des Objekts (auch ohne Umlage-Konfig,
    # z. B. automatisch per Rechnungsart angelegt → wohneinheitenbezogene Kosten).
    all_cats = session.execute(
        select(models.CostCategory).where(models.CostCategory.property_id == property_id)
    ).scalars().all()
    category_code_by_id: dict[int, str] = {cat.id: cat.code for cat in all_cats}
    category_name_by_id: dict[int, str] = {cat.id: cat.name for cat in all_cats}
    water_configured = False
    for cfg in configs:
        cat = cfg.cost_category
        invs = invoices_by_cat.get(cat.id, [])
        year_cost = _category_year_cost(invs, year)
        category_lines.append(
            CategoryLine(cat.code, cat.name, cfg.allocation_key.value, year_cost, cat.id)
        )
        if cfg.allocation_key == models.AllocationKey.CONSUMPTION:
            water_configured = True

    # Strom (falls Zählerstände vorhanden) als Kostenstelle in die Abrechnung aufnehmen.
    # Verteilung nach dem Umlageschlüssel einer konfigurierten "Strom"-Kostenart, sonst Wohnfläche.
    try:
        strom_res = strom_service.berechnung(session, property_id, ys, ye)
    except ValueError:
        strom_res = None
    if strom_res is not None and strom_res.get("hauptzaehler") is not None:
        strom_brutto = Decimal(str(strom_res["summen"]["brutto"]))
        # Zuordnung Strom → Abrechnung (je Objekt im Strom-Modul):
        #   0   → eigene Zeile "Strom"
        #   leer→ nicht in der Abrechnung (keine automatische neue Kostenstelle)
        #   >0  → in bestehende Kostenstelle einrechnen (z. B. "Hausbeleuchtung")
        if prop.strom_allocation_category_id == 0:
            _append_strom_line(category_lines, configs, strom_brutto)
        elif prop.strom_allocation_category_id is not None:
            target_code = category_code_by_id.get(prop.strom_allocation_category_id)
            merged = False
            for cl in category_lines:
                if cl.code == target_code:
                    cl.year_cost += strom_brutto
                    merged = True
                    break
            if not merged:
                # Kostenstelle ohne Umlage-Zeile → eigene "Strom"-Zeile als Fallback
                _append_strom_line(category_lines, configs, strom_brutto)

    # Wasser (Plan B): Kosten aus dem Wasser-Modul (Tarife + Hauptzähler) automatisch
    # in die zugeordneten Kostenstellen einrechnen. Die Verteilung folgt dem
    # Umlageschlüssel der Kostenstelle. Gesamtkosten:
    #   Trink-/Schmutzwasser aus Hauptzähler-Verbrauch, Grundgebühr nach Tagen,
    #   Niederschlagswasser €/m²/Jahr (versiegelte Fläche) nach Tagen.
    # Grundgebühr läuft über die Trinkwasser-Kostenstelle mit.
    try:
        wasser_res = wasser_service.berechnung(session, property_id, ys, ye)
    except ValueError:
        wasser_res = None
    if wasser_res is not None:
        wasser_brutto: dict[str, Decimal] = {}
        for pos in wasser_res["positionen"]:
            wasser_brutto[pos["art"]] = wasser_brutto.get(pos["art"], ZERO) + Decimal(
                str(pos["brutto"])
            )

        def _merge_wasser(category_id, amount):
            if not category_id or amount <= 0:
                return
            target_code = category_code_by_id.get(category_id)
            if target_code is None:
                return
            for cl in category_lines:
                if cl.code == target_code:
                    cl.year_cost += amount
                    return
            warnings.append(
                f"Wasserkosten können nicht verteilt werden: Kostenstelle '{target_code}' "
                "hat keinen Umlageschlüssel."
            )

        _merge_wasser(
            prop.wasser_trinkwasser_category_id,
            wasser_brutto.get("TRINKWASSER", ZERO) + wasser_brutto.get("GRUNDGEBUEHR", ZERO),
        )
        _merge_wasser(
            prop.wasser_schmutzwasser_category_id, wasser_brutto.get("SCHMUTZWASSER", ZERO)
        )
        _merge_wasser(
            prop.wasser_niederschlag_category_id,
            wasser_brutto.get("NIEDERSCHLAGSWASSER", ZERO),
        )

    water_total_cost = sum(
        (cl.year_cost for cl in category_lines if cl.allocation_key == "CONSUMPTION"), ZERO
    )

    water = (
        compute_water_consumption(
            session, property_id, year, include_washing_machine=bool(prop.wasser_waschmaschinen_aktiv)
        )
        if water_configured
        else None
    )
    if water is not None:
        warnings.extend(water.warnings)

    cbm_price: Optional[Decimal] = None
    if water is not None:
        if water.total_consumption > 0:
            cbm_price = water_total_cost / water.total_consumption
        else:
            warnings.append("Gesamtwasserverbrauch ist 0 – cbm-Preis kann nicht berechnet werden.")

    # --- Hover-Info je Kostenstelle (für die Abrechnungsansicht) -------------------
    # Strukturierte Zeilen: {"type": "head"|"row"|"total", "label", "menge"?,
    #   "netto"?, "vat"?, "vat_rate"?, "betrag"?}. Alle Beträge sind BRUTTO
    #   (inkl. MwSt); Satz links ist NETTO – wird je Position explizit aufgeschlüsselt.
    def _info_head(text: str) -> dict:
        return {"type": "head", "label": text, "menge": None, "betrag": None}

    def _info_row(
        label: str,
        menge: str | None,
        betrag: str,
        netto: str | None = None,
        vat: str | None = None,
        vat_rate: float | None = None,
    ) -> dict:
        return {
            "type": "row",
            "label": label,
            "menge": menge,
            "netto": netto,
            "vat": vat,
            "vat_rate": vat_rate,
            "betrag": betrag,
        }

    def _info_total(betrag: str) -> dict:
        return {"type": "total", "label": "Gesamt (brutto)", "menge": None, "betrag": betrag}

    def _invoice_info(cat_id: int) -> list[dict]:
        """Auflistung der in die Gesamtkosten eingeflossenen Rechnungen einer Kostenart."""
        invs = invoices_by_cat.get(cat_id, [])
        if not invs:
            return []
        lines: list[dict] = []
        total = ZERO
        for inv in invs:
            amt = _category_year_cost([inv], year)
            total += amt
            if amt <= 0:
                continue  # Rechnung ohne Anteil im Jahr nicht aufführen
            parts = [x for x in (inv.invoice_number, inv.supplier) if x]
            if inv.period_start and inv.period_end:
                parts.append(f"{inv.period_start}–{inv.period_end}")
            label = " · ".join(parts) or f"Rechnung {inv.id}"
            lines.append(_info_row(label, "anteilig", _money_de(amt)))
        if not lines:
            return []
        lines.append(_info_total(_money_de(total)))
        return lines

    invoice_info: dict[str, list[dict]] = {}
    for cfg in configs:
        invs = invoices_by_cat.get(cfg.cost_category.id, [])
        if invs:
            invoice_info[cfg.cost_category.code] = _invoice_info(cfg.cost_category.id)

    def _wasser_info(kinds: tuple[str, ...]) -> list[dict]:
        """Berechnung der Wasser-Kostenstelle (Tarifpositionen der jeweiligen Art)."""
        if wasser_res is None:
            return []
        lines: list[dict] = []
        if wasser_res.get("plan") == "B" and wasser_res.get("hauptzaehler"):
            hz = wasser_res["hauptzaehler"]
            lines.append(
                _info_head(f"Hauptzähler: {_fmt_de(Decimal(str(hz['consumption'])), 0)} m³")
            )
        elif wasser_res.get("plan") == "A":
            lines.append(
                _info_head(
                    f"Wohnungsverbrauch: {_fmt_de(Decimal(str(wasser_res['verbrauch'])), 0)} m³"
                )
            )
        for pos in wasser_res["positionen"]:
            if pos["art"] not in kinds:
                continue
            art = pos["art"]
            menge = Decimal(str(pos["menge"]))
            satz = Decimal(str(pos["satz"]))
            netto = Decimal(str(pos["netto"]))
            vat = Decimal(str(pos["vat"]))
            brutto = Decimal(str(pos["brutto"]))
            vat_rate = float(pos["vat_rate"])
            if art == "NIEDERSCHLAGSWASSER":
                lines.append(
                    _info_row(
                        f"{_fmt_de(satz, 2)} €/m²/Jahr",
                        f"{_fmt_de(menge, 0)} m²",
                        _money_de(brutto),
                        _money_de(netto),
                        _money_de(vat),
                        vat_rate,
                    )
                )
            elif art == "GRUNDGEBUEHR":
                lines.append(
                    _info_row(
                        f"Grundgebühr {_fmt_de(satz, 2)} €/Jahr",
                        None,
                        _money_de(brutto),
                        _money_de(netto),
                        _money_de(vat),
                        vat_rate,
                    )
                )
            else:
                lines.append(
                    _info_row(
                        f"{_fmt_de(satz, 2)} €/m³",
                        f"{_fmt_de(menge, 0)} m³",
                        _money_de(brutto),
                        _money_de(netto),
                        _money_de(vat),
                        vat_rate,
                    )
                )
        gesamt = sum(
            (Decimal(str(p["brutto"])) for p in wasser_res["positionen"] if p["art"] in kinds),
            ZERO,
        )
        if gesamt > 0:
            lines.append(_info_total(_money_de(gesamt)))
        return lines

    wasser_info: dict[str, list[dict]] = {}
    if wasser_res is not None:
        for cat_id, kinds in (
            (prop.wasser_trinkwasser_category_id, ("TRINKWASSER", "GRUNDGEBUEHR")),
            (prop.wasser_schmutzwasser_category_id, ("SCHMUTZWASSER",)),
            (prop.wasser_niederschlag_category_id, ("NIEDERSCHLAGSWASSER",)),
        ):
            if not cat_id:
                continue
            code = category_code_by_id.get(cat_id)
            if code is not None:
                wasser_info[code] = _wasser_info(kinds)

    def _strom_info() -> list[dict]:
        """Berechnung der Strom-Kostenstelle inkl. Unterzähler-Abzug."""
        if strom_res is None or strom_res.get("hauptzaehler") is None:
            return []
        lines: list[dict] = []
        hz = strom_res["hauptzaehler"]
        lines.append(_info_head(f"Hauptzähler: {_fmt_de(Decimal(str(hz['consumption'])), 0)} kWh"))
        unter = strom_res.get("unterzaehler")
        if unter is not None and Decimal(str(unter.get("consumption", 0))) > 0:
            lines.append(
                _info_head(f"− Unterzähler: {_fmt_de(Decimal(str(unter['consumption'])), 0)} kWh")
            )
            lines.append(
                _info_head(
                    f"= Nettoverbrauch: {_fmt_de(Decimal(str(strom_res['netto_verbrauch'])), 0)} kWh"
                )
            )
        for pos in strom_res["positionen"]:
            art = pos["art"]
            menge = Decimal(str(pos["menge"]))
            satz = Decimal(str(pos["satz"]))
            netto = Decimal(str(pos["netto"]))
            vat = Decimal(str(pos["vat"]))
            brutto = Decimal(str(pos["brutto"]))
            vat_rate = float(pos["vat_rate"])
            if art == "GRUNDGEBUEHR":
                lines.append(
                    _info_row(
                        f"Grundgebühr {_fmt_de(satz, 2)} €/Jahr",
                        None,
                        _money_de(brutto),
                        _money_de(netto),
                        _money_de(vat),
                        vat_rate,
                    )
                )
            else:
                lines.append(
                    _info_row(
                        f"{_fmt_de(satz, 3)} €/kWh",
                        f"{_fmt_de(menge, 0)} kWh",
                        _money_de(brutto),
                        _money_de(netto),
                        _money_de(vat),
                        vat_rate,
                    )
                )
        gesamt = sum(
            (Decimal(str(p["brutto"])) for p in strom_res["positionen"]), ZERO
        )
        if gesamt > 0:
            lines.append(_info_total(_money_de(gesamt)))
        return lines

    strom_info_code: Optional[str] = None
    strom_info_lines: list[dict] = []
    if prop.strom_allocation_category_id == 0:
        strom_info_code = "STROM"
    elif prop.strom_allocation_category_id is not None:
        strom_info_code = category_code_by_id.get(prop.strom_allocation_category_id)
    if strom_info_code:
        strom_info_lines = _strom_info()

    def _category_info(cl: CategoryLine) -> list[dict]:
        if cl.code in wasser_info:
            return wasser_info[cl.code]
        if strom_info_code and cl.code == strom_info_code:
            return strom_info_lines
        return invoice_info.get(cl.code, [])

    tenant_lines: list[TenantLine] = []
    for t, tenant_days in active:
        unit = t.lease_unit
        occ_start = max(t.move_in, ys)
        occ_end = min(t.move_out, ye) if t.move_out else ye
        time_factor = Decimal(tenant_days) / Decimal(diy)
        advance_months = time_factor * Decimal(12)
        breakdown: dict[str, Decimal] = {}
        details: list[CategoryShare] = []

        # Individueller Wasserverbrauch des Mieters (Basis für die CONSUMPTION-Zeilen
        # und die Hinweise zu fehlenden Zählerständen zu Ein-/Auszug).
        unit_consumption: Optional[Decimal] = None
        if water is not None and cbm_price is not None:
            unit_consumption, missing_meters = unit_water_consumption(
                session,
                unit.id,
                occ_start,
                occ_end,
                include_washing_machine=bool(prop.wasser_waschmaschinen_aktiv),
            )
            if missing_meters:
                warnings.append(
                    f"Mieter {t.name}: Zählerstand zu Ein-/Auszug fehlt "
                    f"({', '.join(missing_meters)})."
                )
            elif tenant_days < diy:
                warnings.append(
                    f"Mieter {t.name}: Mietdauer {tenant_days}/{diy} Tage – für exakte "
                    f"Wasserkosten Zählerstände zu Ein-/Auszug erfassen."
                )

        # Je konfigurierter Kostenstelle (Umlageschlüssel) eine Zeile – in der Reihenfolge
        # der Stammdaten (sort_order). CONSUMPTION wird nach Verbrauch, WOHNUNG nach Wohnung
        # verteilt; so erscheinen z. B. Trinkwasser-/Schmutzwassergebühr als eigene
        # Kostenstellen statt als anonyme „Wasserkosten (Verbrauch)“.
        for cl in category_lines:
            if cl.allocation_key == "WF":
                basis_label, basis_total = "Wohnfläche", total_wf
                basis_share = unit.living_area
                if total_wf > 0:
                    amount = cl.year_cost * (unit.living_area / total_wf) * time_factor
                else:
                    amount = ZERO
                    warnings.append(f"Gesamtfläche 0 für {cl.name} – Anteil 0 gesetzt.")
                breakdown[cl.code] = amount
            elif cl.allocation_key == "NF":
                basis_label, basis_total = "Nutzfläche", total_nf
                basis_share = unit.utility_area
                if total_nf > 0:
                    amount = cl.year_cost * (unit.utility_area / total_nf) * time_factor
                else:
                    amount = ZERO
                    warnings.append(f"Gesamtfläche 0 für {cl.name} – Anteil 0 gesetzt.")
                breakdown[cl.code] = amount
            elif cl.allocation_key == "CONSUMPTION":
                basis_label, basis_total = "Verbrauch", (
                    water.total_consumption if water is not None else ZERO
                )
                basis_share = unit_consumption if unit_consumption is not None else ZERO
                if (
                    water is not None
                    and water.total_consumption > 0
                    and unit_consumption is not None
                ):
                    amount = cl.year_cost * (unit_consumption / water.total_consumption)
                else:
                    amount = ZERO
            elif cl.allocation_key == "WOHNUNG":
                # Wohneinheitenbezogene Kosten (z. B. Schornsteinfeger/Wartung je Wohnung).
                # Ohne Rechnung für die Wohnung erscheint die Kostenstelle mit 0 €.
                val = unit_costs.get((unit.id, cl.cost_category_id), ZERO)
                amount = val * time_factor
                basis_label, basis_total, basis_share = "Wohnung", None, None
                breakdown[cl.code] = breakdown.get(cl.code, ZERO) + amount
            else:
                continue  # NONE: keine Verteilung

            details.append(
                CategoryShare(
                    code=cl.code,
                    name=cl.name,
                    allocation_key=cl.allocation_key,
                    year_cost=cl.year_cost,
                    basis_label=basis_label,
                    basis_total=basis_total,
                    basis_share=basis_share,
                    days=tenant_days,
                    amount=amount,
                    info=_category_info(cl),
                )
            )

        if water is not None and cbm_price is not None:
            # Aggregierter Verbrauchsanteil für Saldo/Snapshot – die einzelnen
            # CONSUMPTION-Kostenstellen stehen oben als eigene Zeilen.
            # Gartenwasser wird nicht mehr berücksichtigt.
            breakdown["WASSER_VERBRAUCH"] = (unit_consumption or ZERO) * cbm_price

        # Wohneinheitenbezogene Kosten OHNE Umlage-Konfiguration (automatisch je
        # Rechnungsart angelegte Kostenarten) am Ende ergänzen – konfigurierte
        # WOHNUNG-Zeilen stehen oben an ihrer sort_order-Position.
        config_wohnung_ids = {
            cl.cost_category_id for cl in category_lines if cl.allocation_key == "WOHNUNG"
        }
        for (uid, cat_id), val in unit_costs.items():
            if uid != unit.id or cat_id in config_wohnung_ids:
                continue
            code = category_code_by_id.get(cat_id)
            if code is None:
                continue
            amount = val * time_factor
            breakdown[code] = breakdown.get(code, ZERO) + amount
            details.append(
                CategoryShare(
                    code=code,
                    name=category_name_by_id.get(cat_id, code),
                    allocation_key="WOHNUNG",
                    year_cost=val,
                    basis_label="Wohnung",
                    # Keine Verteil-Basis: eine Rechnung gilt exakt für die Wohnung
                    basis_total=None,
                    basis_share=None,
                    days=tenant_days,
                    amount=amount,
                )
            )

        total_costs = sum(breakdown.values(), ZERO)
        advance_total = money(_advance_total(t, year, occ_start, occ_end))
        saldo = total_costs - advance_total
        tenant_lines.append(
            TenantLine(
                tenant_id=t.id,
                name=t.name,
                lease_unit_id=unit.id,
                designation=unit.designation,
                living_area=unit.living_area,
                utility_area=unit.utility_area,
                tenant_days=tenant_days,
                time_factor=time_factor,
                advance_months=advance_months,
                period_start=occ_start,
                period_end=occ_end,
                breakdown=breakdown,
                details=details,
                advance_breakdown=_advance_breakdown(t, year, occ_start, occ_end),
                total_costs=total_costs,
                advance_total=advance_total,
                saldo=saldo,
            )
        )

    unallocated_water = ZERO
    if water is not None and cbm_price is not None:
        individual_total = sum(
            (ln.breakdown.get("WASSER_VERBRAUCH", ZERO) for ln in tenant_lines), ZERO
        )
        unallocated_water = money(water_total_cost - individual_total)
        if abs(unallocated_water) > CENTS:
            warnings.append(
                f"Restwasser (Leerstand/Abweichung) nicht umgelegt: {unallocated_water} EUR."
            )

    return SettlementResult(
        property_id=property_id,
        property_name=prop.name,
        year=year,
        days_in_year=diy,
        total_wf=total_wf,
        total_nf=total_nf,
        category_lines=category_lines,
        tenant_lines=tenant_lines,
        water=water,
        water_total_cost=water_total_cost,
        water_price_per_m3=cbm_price,
        garden_water_cost=ZERO,
        unallocated_water=unallocated_water,
        warnings=warnings,
    )
