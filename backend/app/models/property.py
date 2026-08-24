from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Property(Base):
    """Immobilie (z. B. Objekt 1, Objekt 2)."""

    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    street: Mapped[str] = mapped_column(String(200), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Strom → Abrechnung (im Strom-Modul je Objekt eingestellt):
    #   0    → eigene Zeile "Strom"
    #   leer → nicht in der Abrechnung (keine automatische neue Kostenstelle)
    #   >0   → in bestehende Kostenstelle einrechnen (z. B. "Hausbeleuchtung")
    strom_allocation_category_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Wasser → Abrechnung: Zuordnung zu bestehenden Kostenstellen
    # (Trinkwasser/Schmutzwasser/Niederschlagswasser) – für Plan A/B
    wasser_trinkwasser_category_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    wasser_schmutzwasser_category_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    wasser_niederschlag_category_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Versiegelte Fläche (m²) für Niederschlagswasser (€/m²) – Stammdaten am Objekt
    wasser_versiegelte_flaeche: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    # Strom: Unterzähler optional – wenn deaktiviert, fließen dessen Werte NICHT ein (kein Abzug, kein Heizstrom)
    strom_unterzaehler_aktiv: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Wasser (Plan A): Waschmaschinen-Zähler optional – wenn deaktiviert, zählen nur die Wohnungs-Zähler
    wasser_waschmaschinen_aktiv: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lease_units: Mapped[List["LeaseUnit"]] = relationship(
        back_populates="prop", cascade="all, delete-orphan"
    )
    meters: Mapped[List["Meter"]] = relationship(
        back_populates="prop", cascade="all, delete-orphan"
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        back_populates="prop", cascade="all, delete-orphan"
    )
    allocation_configs: Mapped[List["AllocationConfig"]] = relationship(
        back_populates="prop", cascade="all, delete-orphan"
    )
    cost_categories: Mapped[List["CostCategory"]] = relationship(
        back_populates="prop", cascade="all, delete-orphan"
    )
    settlements: Mapped[List["Settlement"]] = relationship(
        back_populates="prop", cascade="all, delete-orphan"
    )
    techem_records: Mapped[List["TechemRecord"]] = relationship(
        back_populates="prop", cascade="all, delete-orphan"
    )
    strom_prices: Mapped[List["StromPrice"]] = relationship(
        back_populates="prop", cascade="all, delete-orphan"
    )
    strom_readings: Mapped[List["StromReading"]] = relationship(
        back_populates="prop", cascade="all, delete-orphan"
    )
    wasser_prices: Mapped[List["WasserPrice"]] = relationship(
        back_populates="prop", cascade="all, delete-orphan"
    )
    wasser_readings: Mapped[List["WasserReading"]] = relationship(
        back_populates="prop", cascade="all, delete-orphan"
    )
