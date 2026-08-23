from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class StromPrice(Base):
    """Tarifbestandteil für Strom (Grundgebühr/Arbeitspreis/Stromsteuer) je Objekt.

    Jeder Bestandteil hat einen Gültigkeitszeitraum (von–bis) und einen MwSt-Satz.
    Die Zeiträume je Objekt+Art müssen lückenlos aneinander anschließen.
    """

    __tablename__ = "strom_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # GRUNDGEBUEHR (€/Jahr) | ARBEITSPREIS (€/kWh) | STROMSTEUER (€/kWh)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 5), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("19.00"))

    prop: Mapped["Property"] = relationship(back_populates="strom_prices")


class StromReading(Base):
    """Zählerstand für Strom (Haupt- oder Unterzähler) je Objekt."""

    __tablename__ = "strom_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # HAUPTZAEHLER | UNTERZAEHLER
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    reading_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)  # kWh

    prop: Mapped["Property"] = relationship(back_populates="strom_readings")
