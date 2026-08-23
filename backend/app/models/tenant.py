from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class LeaseUnit(Base):
    """Mieteinheit mit Wohnfläche und Anteil an Extraflächen."""

    __tablename__ = "lease_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    designation: Mapped[str] = mapped_column(String(200), nullable=False)
    living_area: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    extra_area: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)

    prop: Mapped["Property"] = relationship(back_populates="lease_units")
    tenants: Mapped[List["Tenant"]] = relationship(
        back_populates="lease_unit", cascade="all, delete-orphan"
    )
    meters: Mapped[List["Meter"]] = relationship(
        back_populates="lease_unit", cascade="all, delete-orphan"
    )

    @property
    def utility_area(self) -> Decimal:
        """Nutzfläche der Einheit = Wohnfläche + Extrafläche."""
        return self.living_area + self.extra_area


class Tenant(Base):
    """Mieter mit Ein-/Auszugsdatum und monatlicher Vorauszahlung."""

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    lease_unit_id: Mapped[int] = mapped_column(
        ForeignKey("lease_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    move_in: Mapped[date] = mapped_column(Date, nullable=False)
    move_out: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    monthly_advance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    lease_unit: Mapped["LeaseUnit"] = relationship(back_populates="tenants")
    settlement_lines: Mapped[List["SettlementLine"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
