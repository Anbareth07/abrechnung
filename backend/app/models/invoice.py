from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, MetaJSON


class Invoice(Base):
    """Erfasste Versorger-/Vermieter-Rechnung (Kopf)."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cost_category_id: Mapped[int] = mapped_column(
        ForeignKey("cost_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Rechnungsart (Grundsteuer, Wasser, …) – steuert Eingabelayout & Verteilung
    kind: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    # Grundsteuer (wiederkehrend): gültig ab Bescheid + Jahresbetrag
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    annual_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    # Schornsteinfeger o. ä.: optional auf eine einzelne Wohneinheit bezogen
    lease_unit_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("lease_units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    supplier: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    issue_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    gross_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    # Anrechnungsanteil als Bruch Zähler/Nenner (z. B. Wohnungsanteil laut
    # Feststellbescheid 13044/13764). Angerechnet wird Betrag × Zähler/Nenner.
    anteil_zaehler: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 4), nullable=True)
    anteil_nenner: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 4), nullable=True)
    meta: Mapped[dict] = mapped_column(MetaJSON(), nullable=False, default=dict)

    prop: Mapped["Property"] = relationship(back_populates="invoices")
    cost_category: Mapped["CostCategory"] = relationship(back_populates="invoices")
    lease_unit: Mapped[Optional["LeaseUnit"]] = relationship()
    items: Mapped[List["InvoiceItem"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceItem.from_date",
    )


class InvoiceItem(Base):
    """Position/Segment einer Rechnung.

    Über `from_date`/`to_date` lassen sich Zeitabschnitte abbilden, z. B. wenn
    sich eine Grundgebühr innerhalb des Abrechnungszeitraums ändert. Jedes
    Segment trägt seinen eigenen Betrag und wird pro-rata aufs Abrechnungsjahr
    verteilt.
    """

    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 6), nullable=True)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    meta: Mapped[dict] = mapped_column(MetaJSON(), nullable=False, default=dict)

    invoice: Mapped["Invoice"] = relationship(back_populates="items")
