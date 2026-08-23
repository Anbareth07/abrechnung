from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Date, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, MetaJSON
from .enums import TechemKind


class TechemRecord(Base):
    """Techem-Datenaufbereitung (nur Objekt 2).

    Erfasst Gas-/Heizstrom-Daten gebündelt, damit der Vermieter die externen
    „Techem Bögen" ausfüllen kann. Fließt NICHT in die Mieter-Abrechnung ein.
    """

    __tablename__ = "techem_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[TechemKind] = mapped_column(
        sa.Enum(TechemKind, name="techem_kind_enum", native_enum=False, length=30),
        nullable=False,
        default=TechemKind.GAS,
    )
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_kwh: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(MetaJSON(), nullable=False, default=dict)

    prop: Mapped["Property"] = relationship(back_populates="techem_records")
