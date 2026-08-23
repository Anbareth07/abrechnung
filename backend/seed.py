"""Seed-Daten: Objekte, Kostenarten, Umlageschlüssel, Mieteinheiten, Mieter, Zähler.

Hinweis: Flächen je Mieteinheit sind Beispielwerte, die Gesamtflächen entsprechen
den Vorgaben (Objekt 1 WF 206 / NF 218, Objekt 2 WF 287,7 / NF 330).
Adressen (PLZ/Ort) und Vorauszahlungen bitte anpassen.
Rechnungen und Zählerstände werden bewusst NICHT geseedet – der
Vollständigkeits-Check zeigt dann genau, welche Daten noch fehlen.
"""

from datetime import date
from decimal import Decimal

from app import models
from app.db import SessionLocal
from app.models.enums import AllocationKey, MeterType, MeterUnit


def _category(session, code, name, default_key=AllocationKey.NONE):
    cat = session.query(models.CostCategory).filter_by(code=code).first()
    if cat is None:
        cat = models.CostCategory(code=code, name=name, default_allocation_key=default_key)
        session.add(cat)
        session.flush()
    return cat


def _config(session, prop, cat, key, order):
    session.add(
        models.AllocationConfig(
            property_id=prop.id, cost_category_id=cat.id, allocation_key=key, sort_order=order
        )
    )


def _unit(session, prop, designation, wf, extra):
    unit = models.LeaseUnit(
        property_id=prop.id, designation=designation, living_area=Decimal(wf), extra_area=Decimal(extra)
    )
    session.add(unit)
    session.flush()
    return unit


def _tenant(session, unit, name, move_in, monthly):
    tenant = models.Tenant(
        lease_unit_id=unit.id, name=name, move_in=move_in, move_out=None, monthly_advance=Decimal(monthly)
    )
    session.add(tenant)
    session.flush()
    session.add(
        models.AdvancePayment(tenant_id=tenant.id, valid_from=move_in, amount=Decimal(monthly))
    )
    return tenant


def _meter(session, name, mtype, prop=None, unit=None):
    session.add(
        models.Meter(
            name=name,
            meter_type=mtype,
            unit=MeterUnit.M3 if mtype != MeterType.HEATING_ELECTRICITY else MeterUnit.KWH,
            property_id=prop.id if prop else None,
            lease_unit_id=unit.id if unit else None,
        )
    )


def seed() -> None:
    session = SessionLocal()
    try:
        # --- Kostenarten -------------------------------------------------
        cats = {
            "grundsteuer": _category(session, "grundsteuer", "Grundsteuer", AllocationKey.NF),
            "gebaeudeversicherung": _category(session, "gebaeudeversicherung", "Gebäudebrand-/Elementarversicherung", AllocationKey.NF),
            "haftpflicht": _category(session, "haftpflicht", "Haftpflichtversicherung", AllocationKey.NF),
            "niederschlagswasser": _category(session, "niederschlagswasser", "Niederschlagswassergebühr", AllocationKey.NF),
            "gartenpflege": _category(session, "gartenpflege", "Gartenpflege", AllocationKey.WF),
            "hausbeleuchtung": _category(session, "hausbeleuchtung", "Hausbeleuchtung", AllocationKey.WF),
            "schornstein": _category(session, "schornstein", "Schornstein/Wartung", AllocationKey.WF),
            "trinkwasser": _category(session, "trinkwasser", "Trinkwasser", AllocationKey.CONSUMPTION),
            "schmutzwasser": _category(session, "schmutzwasser", "Schmutzwasser", AllocationKey.CONSUMPTION),
            "legionellen": _category(session, "legionellen", "Legionellenmessung", AllocationKey.WF),
            "abfall": _category(session, "abfall", "Abfall", AllocationKey.NONE),
            "heizung": _category(session, "heizung", "Heizung/Gas (Techem)", AllocationKey.NONE),
        }

        # --- Objekt 1 -----------------------------------------------------
        p1 = models.Property(name="Objekt 1", street="", zip_code="", city="")
        session.add(p1)
        session.flush()

        _config(session, p1, cats["grundsteuer"], AllocationKey.NF, 1)
        _config(session, p1, cats["gebaeudeversicherung"], AllocationKey.NF, 2)
        _config(session, p1, cats["haftpflicht"], AllocationKey.NF, 3)
        _config(session, p1, cats["niederschlagswasser"], AllocationKey.NF, 4)
        _config(session, p1, cats["gartenpflege"], AllocationKey.WF, 5)
        _config(session, p1, cats["hausbeleuchtung"], AllocationKey.WF, 6)
        _config(session, p1, cats["schornstein"], AllocationKey.WF, 7)
        _config(session, p1, cats["trinkwasser"], AllocationKey.CONSUMPTION, 8)
        _config(session, p1, cats["schmutzwasser"], AllocationKey.CONSUMPTION, 9)

        u1 = _unit(session, p1, "Wohnung 1 (Mieter A)", "76.0", "0.0")
        u2 = _unit(session, p1, "Wohnung 2 (Mieter B)", "65.0", "0.0")
        u3 = _unit(session, p1, "Wohnung 3 (Mieter C)", "65.0", "0.0")
        # Extrafläche (12 m² separates Zimmer) ist Gemeinschaftsfläche und wird laut
        # Referenz-Abrechnung NICHT auf Mieter umgelegt (nur im NF-Nenner enthalten).
        _unit(session, p1, "Gemeinschaftsfläche (separates Zimmer)", "0.0", "12.0")

        _tenant(session, u1, "Mieter A", date(2020, 1, 1), "150.00")
        _tenant(session, u2, "Mieter B", date(2020, 1, 1), "150.00")
        _tenant(session, u3, "Mieter C", date(2020, 1, 1), "150.00")

        _meter(session, "Garten Nord", MeterType.GARDEN, prop=p1)
        _meter(session, "Garten Süd", MeterType.GARDEN, prop=p1)
        _meter(session, "Wohnung 1 Wasser", MeterType.APARTMENT_WATER, unit=u1)
        _meter(session, "Wohnung 1 Waschmaschine", MeterType.WASHING_MACHINE, unit=u1)
        _meter(session, "Wohnung 2 Wasser", MeterType.APARTMENT_WATER, unit=u2)
        _meter(session, "Wohnung 2 Waschmaschine", MeterType.WASHING_MACHINE, unit=u2)
        _meter(session, "Wohnung 3 Wasser", MeterType.APARTMENT_WATER, unit=u3)
        _meter(session, "Wohnung 3 Waschmaschine", MeterType.WASHING_MACHINE, unit=u3)

        # --- Objekt 2 -----------------------------------------------------
        p2 = models.Property(name="Objekt 2", street="", zip_code="", city="")
        session.add(p2)
        session.flush()

        _config(session, p2, cats["grundsteuer"], AllocationKey.WF, 1)
        _config(session, p2, cats["trinkwasser"], AllocationKey.WF, 2)
        _config(session, p2, cats["schmutzwasser"], AllocationKey.WF, 3)
        _config(session, p2, cats["gartenpflege"], AllocationKey.WF, 4)
        _config(session, p2, cats["legionellen"], AllocationKey.WF, 5)
        _config(session, p2, cats["gebaeudeversicherung"], AllocationKey.NF, 6)
        _config(session, p2, cats["haftpflicht"], AllocationKey.NF, 7)
        _config(session, p2, cats["niederschlagswasser"], AllocationKey.NF, 8)
        _config(session, p2, cats["hausbeleuchtung"], AllocationKey.NF, 9)
        # Abfall & Heizung/Gas fließen nicht in die Umlage ein.
        _config(session, p2, cats["abfall"], AllocationKey.NONE, 10)
        _config(session, p2, cats["heizung"], AllocationKey.NONE, 11)

        s1 = _unit(session, p2, "Wohnung 1", "143.85", "0.0")
        s2 = _unit(session, p2, "Wohnung 2", "143.85", "0.0")
        # Garage ist Gemeinschaftsfläche (nur im NF-Nenner, wird nicht umgelegt).
        _unit(session, p2, "Garage", "0.0", "42.3")

        _tenant(session, s1, "Mieter F", date(2020, 1, 1), "200.00")
        _tenant(session, s2, "Mieter G", date(2020, 1, 1), "200.00")

        _meter(session, "Heizstrom (Heizung)", MeterType.HEATING_ELECTRICITY, prop=p2)

        session.commit()
        print("Seed-Daten geladen: 2 Objekte, 12 Kostenarten, 5 Mieteinheiten, 5 Mieter, 9 Zähler.")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
