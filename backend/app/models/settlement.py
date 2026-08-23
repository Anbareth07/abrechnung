from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, MetaJSON
from .enums import SettlementStatus


class Settlement(Base):
    """Snapshot einer finalisierten Jahresabrechnung für ein Objekt."""

    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SettlementStatus] = mapped_column(
        sa.Enum(SettlementStatus, name="settlement_status_enum", native_enum=False, length=20),
        nullable=False,
        default=SettlementStatus.DRAFT,
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    meta: Mapped[dict] = mapped_column(MetaJSON(), nullable=False, default=dict)

    __table_args__ = (
        sa.UniqueConstraint("property_id", "year", name="uq_settlement_property_year"),
    )

    prop: Mapped["Property"] = relationship(back_populates="settlements")
    lines: Mapped[List["SettlementLine"]] = relationship(
        back_populates="settlement", cascade="all, delete-orphan"
    )


class SettlementLine(Base):
    """Abrechnungszeile eines Mieters (Snapshot der Ergebnisse)."""

    __tablename__ = "settlement_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_id: Mapped[int] = mapped_column(
        ForeignKey("settlements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    detail: Mapped[dict] = mapped_column(MetaJSON(), nullable=False, default=dict)
    total_costs: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    advance_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    saldo: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    settlement: Mapped["Settlement"] = relationship(back_populates="lines")
    tenant: Mapped["Tenant"] = relationship(back_populates="settlement_lines")
