"""Demo-Daten: Leerstand mit Wasserzähler -> "Restwasser (Leerstand)" in der Abrechnung.

Fügt dem Objekt „Ulrichstraße 8“ (dev.db) eine leerstehende Wohnung mit
Wasserzähler und Zählerständen für 2025 hinzu. Deren Verbrauch fließt in den
Gesamtverbrauch (und damit die Wasserkosten) ein, wird aber keinem Mieter
zugeordnet -> die Abrechnung weist „Nicht umgelegtes Restwasser (Leerstand)“ aus.

Idempotent: erneutes Ausführen legt nichts doppelt an.
"""

import os
from datetime import date
from decimal import Decimal

os.environ.setdefault(
    "DATABASE_URL", "sqlite:///c:/Users/tfran/Projects/Abrechnung/backend/dev.db"
)

from sqlalchemy import select

from app import models
from app.db import SessionLocal
from app.models.enums import MeterType, MeterUnit

UNIT_NAME = "Wohnung 4 (Leerstand)"


def add_restwasser_demo() -> None:
    with SessionLocal() as s:
        prop = s.execute(
            select(models.Property).where(models.Property.name.contains("Ulrichstraße"))
        ).scalars().first()
        if prop is None:
            raise SystemExit(
                "Objekt „Ulrichstraße 8“ nicht gefunden – bitte das Objekt in "
                "add_restwasser_demo.py anpassen."
            )

        existing = s.execute(
            select(models.LeaseUnit).where(
                models.LeaseUnit.property_id == prop.id,
                models.LeaseUnit.designation == UNIT_NAME,
            )
        ).scalars().first()
        if existing is not None:
            print(f"{UNIT_NAME} existiert bereits – nichts zu tun.")
            return

        unit = models.LeaseUnit(
            property_id=prop.id,
            designation=UNIT_NAME,
            living_area=Decimal("55.0"),
            extra_area=Decimal("0.0"),
        )
        s.add(unit)
        s.flush()

        meter = models.Meter(
            name=f"{UNIT_NAME} Wasser",
            meter_type=MeterType.APARTMENT_WATER,
            unit=MeterUnit.M3,
            lease_unit_id=unit.id,
        )
        s.add(meter)
        s.flush()

        s.add(
            models.MeterReading(
                meter_id=meter.id, reading_date=date(2024, 12, 31), value=Decimal("100")
            )
        )
        s.add(
            models.MeterReading(
                meter_id=meter.id, reading_date=date(2025, 12, 31), value=Decimal("128")
            )
        )

        s.commit()
        print(
            f"{UNIT_NAME} + Wasserzähler + Zählerstände 2025 (28 m³) angelegt."
        )


if __name__ == "__main__":
    add_restwasser_demo()
