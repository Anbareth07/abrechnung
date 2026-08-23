"""Techem-Heizkostenblatt je Objekt und Heizperiode (von-bis).

Gasverbrauch/-kosten, Wartung Heizung und Kaminfeger werden manuell erfasst;
der Heizstromanteil (strom_kwh) wird automatisch aus dem Unterzaehler berechnet.
Fliesst NICHT in die Mieter-Abrechnung ein.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Date, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, MetaJSON


class TechemRecord(Base):
    """Heizkosten-Blatt fuer einen Zeitraum (normalerweise 01.07.-30.06. Folgejahr)."""

    __tablename__ = "techem_records"
    __table_args__ = (
        sa.UniqueConstraint("property_id", "von", "bis", name="uq_techem_property_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Heizperiode: von (z. B. 01.07.) bis (z. B. 30.06. des Folgejahres)
    von: Mapped[date] = mapped_column(Date, nullable=False)
    bis: Mapped[date] = mapped_column(Date, nullable=False)
    gas_kwh: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=0)
    gas_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    maintenance_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    chimney_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(MetaJSON(), nullable=False, default=dict)

    prop: Mapped["Property"] = relationship(back_populates="techem_records")
