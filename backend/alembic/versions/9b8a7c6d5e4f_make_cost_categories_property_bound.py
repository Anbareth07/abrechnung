"""make cost categories property-bound

Revision ID: 9b8a7c6d5e4f
Revises: 4f9e8d7c6b5a
Create Date: 2026-08-23 18:30:00

Kostenarten werden objektgebunden: Jede Kostenart gehört künftig zu genau
einem Objekt. Bisher globale Kostenarten werden je Objekt dupliziert (mit
eindeutigem technischem Code) und die Umlage-Konfigurationen sowie Rechnungen
auf die objektgebundene Kopie umgehängt. Die bisherige globale Unique auf
`code` bleibt bestehen (Codes werden bei Kopien erweitert).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9b8a7c6d5e4f"
down_revision: Union[str, None] = "4f9e8d7c6b5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # --- 1) Schema: property_id (nullable) + FK ----------------------------
    with op.batch_alter_table("cost_categories", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("property_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_cost_categories_property_id",
            "properties",
            ["property_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # --- 2) Daten: je (Objekt, Kostenart) objektgebundene Kopie -------------
    meta = sa.MetaData()
    cat_t = sa.Table("cost_categories", meta, autoload_with=bind)
    cfg_t = sa.Table("allocation_configs", meta, autoload_with=bind)
    inv_t = sa.Table("invoices", meta, autoload_with=bind)

    rows = [dict(r) for r in bind.execute(sa.select(cat_t)).mappings()]
    used_codes = {r["code"] for r in rows}
    # Noch nicht zugeordnete (bisher globale) Kategorien
    unclaimed = [r for r in rows if r["property_id"] is None]
    # Je Objekt bereits vorhandene Kategorien (id je Code)
    owned: dict[tuple[int, str], int] = {}
    for r in rows:
        if r["property_id"] is not None:
            owned.setdefault((r["property_id"], r["code"]), r["id"])

    configs = bind.execute(
        sa.select(cfg_t.c.id, cfg_t.c.property_id, cfg_t.c.cost_category_id)
    ).all()
    invoices = bind.execute(
        sa.select(inv_t.c.id, inv_t.c.property_id, inv_t.c.cost_category_id)
    ).all()

    def src_for(cid: int):
        return next((r for r in rows if r["id"] == cid), None)

    def ensure(property_id: int, code: str) -> int:
        """Liefert die objektgebundene Kategorie für (Objekt, Code), legt sie ggf. an."""
        key = (property_id, code)
        if key in owned:
            return owned[key]
        # Eine bisher unzugeordnete Kategorie mit diesem Code übernehmen
        for idx, cand in enumerate(unclaimed):
            if cand["code"] == code:
                unclaimed.pop(idx)
                bind.execute(
                    cat_t.update().where(cat_t.c.id == cand["id"]).values(property_id=property_id)
                )
                owned[key] = cand["id"]
                return cand["id"]
        # Neue Kopie mit eindeutigem Code
        new_code = code
        i = 2
        while new_code in used_codes:
            new_code = f"{code}_{i}"
            i += 1
        used_codes.add(new_code)
        src = next((r for r in rows if r["code"] == code), None)
        ins = cat_t.insert().values(
            property_id=property_id,
            code=new_code,
            name=src["name"] if src else new_code,
            default_allocation_key=src["default_allocation_key"] if src else "NONE",
            is_active=src["is_active"] if src else True,
        )
        new_id = bind.execute(ins).inserted_primary_key[0]
        owned[key] = new_id
        return new_id

    for cfg_id, pid, cid in configs:
        src = src_for(cid)
        if src is None:
            continue
        new_id = ensure(pid, src["code"])
        if new_id != cid:
            bind.execute(
                cfg_t.update().where(cfg_t.c.id == cfg_id).values(cost_category_id=new_id)
            )

    for inv_id, pid, cid in invoices:
        src = src_for(cid)
        if src is None:
            continue
        new_id = ensure(pid, src["code"])
        if new_id != cid:
            bind.execute(
                inv_t.update().where(inv_t.c.id == inv_id).values(cost_category_id=new_id)
            )

    # Nicht zugeordnete (obdachlose) Kategorien löschen
    bind.execute(cat_t.delete().where(cat_t.c.property_id.is_(None)))

    # --- 3) property_id NOT NULL -------------------------------------------
    with op.batch_alter_table("cost_categories", recreate="always") as batch_op:
        batch_op.alter_column("property_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    # Bewusst vereinfacht: Daten-Wiedervereinigung wird nicht unterstützt.
    with op.batch_alter_table("cost_categories", recreate="always") as batch_op:
        batch_op.alter_column("property_id", existing_type=sa.Integer(), nullable=True)
    op.drop_constraint("fk_cost_categories_property_id", "cost_categories", type_="foreignkey")
    op.drop_column("cost_categories", "property_id")
