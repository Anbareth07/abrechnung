"""Wasser-Modul (Plan B): Tarife (Trinkwasser/Schmutzwasser/Niederschlagswasser/Grundgebühr)
und Hauptzählerstände je Objekt."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class WasserPrice(Base):
    """Tarifbestandteil für Wasser je Objekt.

    TRINKWASSER/SCHMUTZWASSER in €/m³, NIEDERSCHLAGSWASSER in €/m²
    (Grundlage: versiegelte Fläche am Objekt), GRUNDGEBUEHR in €/Jahr.
    Zeiträume je Objekt+Art müssen lückenlos aneinander anschließen.
    """

    __tablename__ = "wasser_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # TRINKWASSER (€/m³) | SCHMUTZWASSER (€/m³) | NIEDERSCHLAGSWASSER (€/m²) | GRUNDGEBUEHR (€/Jahr)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 5), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("19.00"))

    prop: Mapped["Property"] = relationship(back_populates="wasser_prices")


class WasserReading(Base):
    """Hauptzählerstand für Wasser (m³) je Objekt."""

    __tablename__ = "wasser_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reading_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)  # m³
    # Zählerwechsel: dieser Stand ist der letzte des alten Zählers; der neue beginnt bei neuer_zaehler_start
    vor_zaehlerwechsel: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    neuer_zaehler_start: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )

    prop: Mapped["Property"] = relationship(back_populates="wasser_readings")
