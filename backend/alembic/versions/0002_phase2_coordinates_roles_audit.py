"""Phase 2: coordinates for the live map + roles + audit fields.

Adds (all nullable except admin_users.role, which defaults existing users
to full admin so nobody is locked out after deploying):

- milestones.lat / milestones.lng      — server-geocoded milestone coordinates
- milestones.created_by                — audit: which admin recorded it
- shipments.created_by                 — audit: which admin created it
- shipments.origin_lat / origin_lng / dest_lat / dest_lng — geocoded endpoints
- admin_users.role                     — "admin" or "operator"

Guarded + batch-mode like 0001, so it also adopts databases that were
manually upgraded partway.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

COLUMNS = {
    "milestones": [
        ("lat", sa.Column("lat", sa.Float(), nullable=True)),
        ("lng", sa.Column("lng", sa.Float(), nullable=True)),
        ("created_by", sa.Column("created_by", sa.String(), nullable=True)),
    ],
    "shipments": [
        ("origin_lat", sa.Column("origin_lat", sa.Float(), nullable=True)),
        ("origin_lng", sa.Column("origin_lng", sa.Float(), nullable=True)),
        ("dest_lat", sa.Column("dest_lat", sa.Float(), nullable=True)),
        ("dest_lng", sa.Column("dest_lng", sa.Float(), nullable=True)),
        ("created_by", sa.Column("created_by", sa.String(), nullable=True)),
    ],
    "admin_users": [
        (
            "role",
            sa.Column(
                "role",
                sa.String(),
                nullable=False,
                server_default="admin",
            ),
        ),
    ],
}


def _insp(bind):
    return sa.inspect(bind)


def _has_column(insp, table, name):
    return any(c["name"] == name for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    for table, cols in COLUMNS.items():
        insp = _insp(bind)
        for name, col in cols:
            if not _has_column(insp, table, name):
                # Plain ADD COLUMN works on SQLite and Postgres alike; the
                # role column carries a server_default so existing rows
                # (including your current admin) become "admin".
                op.add_column(table, col)


def downgrade() -> None:
    bind = op.get_bind()
    for table, cols in reversed(list(COLUMNS.items())):
        insp = _insp(bind)
        existing = [name for name, _ in cols if _has_column(insp, table, name)]
        if not existing:
            continue
        # batch_alter_table keeps DROP COLUMN working on SQLite too.
        with op.batch_alter_table(table) as batch:
            for name in existing:
                batch.drop_column(name)
