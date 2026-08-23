from __future__ import annotations

from datetime import datetime
from typing import List

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, String, func
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
