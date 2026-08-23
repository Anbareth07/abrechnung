from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import MeterType, MeterUnit


class Meter(Base):
    """Zähler – verknüpft mit Property (z. B. Garten) oder LeaseUnit (Wohnung, Waschmaschine)."""

    __tablename__ = "meters"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=True, index=True
    )
    lease_unit_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("lease_units.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    meter_type: Mapped[MeterType] = mapped_column(
        sa.Enum(MeterType, name="meter_type_enum", native_enum=False, length=30),
        nullable=False,
        default=MeterType.OTHER,
    )
    unit: Mapped[MeterUnit] = mapped_column(
        sa.Enum(MeterUnit, name="meter_unit_enum", native_enum=False, length=10),
        nullable=False,
        default=MeterUnit.M3,
    )

    prop: Mapped[Optional["Property"]] = relationship(back_populates="meters")
    lease_unit: Mapped[Optional["LeaseUnit"]] = relationship(back_populates="meters")
    readings: Mapped[List["MeterReading"]] = relationship(
        back_populates="meter",
        cascade="all, delete-orphan",
        order_by="MeterReading.reading_date",
    )


class MeterReading(Base):
    """Zählerstand zu einem Datum."""

    __tablename__ = "meter_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    meter_id: Mapped[int] = mapped_column(
        ForeignKey("meters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reading_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    __table_args__ = (
        sa.UniqueConstraint("meter_id", "reading_date", name="uq_meter_reading"),
    )

    meter: Mapped["Meter"] = relationship(back_populates="readings")
