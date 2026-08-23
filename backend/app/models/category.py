from __future__ import annotations

from typing import List

import sqlalchemy as sa
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import AllocationKey


class CostCategory(Base):
    """Kostenart (z. B. Grundsteuer), gebunden an ein Objekt.

    Kostenarten werden nicht separat verwaltet, sondern entstehen automatisch,
    wenn im Umlageschlüssel eine Kostenart hinzugefügt wird – sie gelten dann
    für genau dieses eine Objekt.
    """

    __tablename__ = "cost_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Technischer Schlüssel: bleibt global eindeutig; je Objekt gibt es eigene
    # Kategorien, deren Code bei Bedarf automatisch erweitert wird.
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    default_allocation_key: Mapped[AllocationKey] = mapped_column(
        sa.Enum(AllocationKey, name="allocation_key_enum", native_enum=False, length=20),
        nullable=False,
        default=AllocationKey.NONE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    prop: Mapped["Property"] = relationship(back_populates="cost_categories")
    allocation_configs: Mapped[List["AllocationConfig"]] = relationship(
        back_populates="cost_category", cascade="all, delete-orphan"
    )
    invoices: Mapped[List["Invoice"]] = relationship(back_populates="cost_category")


class AllocationConfig(Base):
    """Umlageschlüssel einer Kostenart für ein bestimmtes Objekt.

    Löst das Problem, dass dieselbe Kostenart je Objekt unterschiedlich
    umgelegt wird (z. B. Grundsteuer: NF in Objekt 1, WF in Objekt 2).
    """

    __tablename__ = "allocation_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cost_category_id: Mapped[int] = mapped_column(
        ForeignKey("cost_categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    allocation_key: Mapped[AllocationKey] = mapped_column(
        sa.Enum(AllocationKey, name="allocation_key_enum", native_enum=False, length=20),
        nullable=False,
        default=AllocationKey.WF,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        sa.UniqueConstraint("property_id", "cost_category_id", name="uq_allocation_property_category"),
    )

    prop: Mapped["Property"] = relationship(back_populates="allocation_configs")
    cost_category: Mapped["CostCategory"] = relationship(back_populates="allocation_configs")


class CategoryNoInvoice(Base):
    """Kennzeichnung: für eine Kostenart liegt in einem Jahr bewusst keine Rechnung vor.

    Wird im Vollständigkeits-Check als "keine Rechnung in diesem Jahr" berücksichtigt.
    """

    __tablename__ = "category_no_invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cost_category_id: Mapped[int] = mapped_column(
        ForeignKey("cost_categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        sa.UniqueConstraint(
            "property_id", "cost_category_id", "year", name="uq_no_invoice_property_cat_year"
        ),
    )

    prop: Mapped["Property"] = relationship()
    cost_category: Mapped["CostCategory"] = relationship()
