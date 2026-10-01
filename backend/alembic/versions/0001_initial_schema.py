"""Initial schema: shipments, milestones, admin_users + hot-path indexes.

This migration is deliberately *idempotent* (guarded with inspector checks)
so it can adopt databases created the old way, before Alembic existed:

- Brand-new database      -> creates all three tables with the full current
                             schema, then the indexes.
- Existing create_all-era -> tables already exist, so it only adds what's
                             new: the `shipments.deleted_at` soft-delete
                             column and the performance indexes. No data is
                             touched.

Either way the database ends up stamped at this revision.

Revision ID: 0001
Revises:
Create Date: 2026-09-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

NEW_INDEXES = [
    ("ix_shipments_status", "shipments", ["status"]),
    ("ix_shipments_created_at", "shipments", ["created_at"]),
    ("ix_milestones_timestamp", "milestones", ["timestamp"]),
    # Composite: serves "timeline for one shipment, ordered by time" —
    # the query every public tracking lookup performs.
    ("ix_milestones_shipment_timestamp", "milestones", ["shipment_id", "timestamp"]),
]


def _has_table(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _has_column(insp, table: str, name: str) -> bool:
    return any(c["name"] == name for c in insp.get_columns(table))


def _has_index(insp, table: str, name: str) -> bool:
    return any(i["name"] == name for i in insp.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()

    # ---- tables -----------------------------------------------------------
    if not _has_table(sa.inspect(bind), "admin_users"):
        op.create_table(
            "admin_users",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("username", sa.String(), nullable=False),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_admin_users_username", "admin_users", ["username"], unique=True)

    if not _has_table(sa.inspect(bind), "shipments"):
        op.create_table(
            "shipments",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("tracking_number", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("origin", sa.String(), nullable=False),
            sa.Column("destination", sa.String(), nullable=False),
            sa.Column("sender_name", sa.String(), nullable=False),
            sa.Column("recipient_name", sa.String(), nullable=False),
            sa.Column("carrier", sa.String(), nullable=True),
            sa.Column("shipping_mode", sa.String(), nullable=True),
            sa.Column("weight_kg", sa.Float(), nullable=True),
            sa.Column("length_cm", sa.Float(), nullable=True),
            sa.Column("width_cm", sa.Float(), nullable=True),
            sa.Column("height_cm", sa.Float(), nullable=True),
            sa.Column("estimated_delivery", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_shipments_tracking_number", "shipments", ["tracking_number"], unique=True
        )
    elif not _has_column(sa.inspect(bind), "shipments", "deleted_at"):
        # Adopting a pre-Alembic database: add the soft-delete column.
        op.add_column("shipments", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    if not _has_table(sa.inspect(bind), "milestones"):
        op.create_table(
            "milestones",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("shipment_id", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("location", sa.String(), nullable=False),
            sa.Column("note", sa.String(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    # ---- performance indexes ---------------------------------------------
    # IMPORTANT: (re)inspect AFTER table creation — an Inspector reflects and
    # caches once, so reusing the pre-create snapshot would skip this loop on
    # fresh databases.
    insp = sa.inspect(bind)
    for name, table, columns in NEW_INDEXES:
        if _has_table(insp, table) and not _has_index(insp, table, name):
            op.create_index(name, table, columns)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    for name, table, _ in NEW_INDEXES:
        if _has_table(insp, table) and _has_index(insp, table, name):
            op.drop_index(name, table_name=table)
    if _has_table(insp, "shipments") and _has_column(insp, "shipments", "deleted_at"):
        op.drop_column("shipments", "deleted_at")
    for table in ("milestones", "shipments"):
        if _has_table(insp, table):
            op.drop_table(table)
    if _has_table(insp, "admin_users"):
        if _has_index(insp, "admin_users", "ix_admin_users_username"):
            op.drop_index("ix_admin_users_username", table_name="admin_users")
        op.drop_table("admin_users")
