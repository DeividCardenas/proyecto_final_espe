"""0003_enrichment_and_quality

Columnas de enriquecimiento topológico (obras CDOT / AADT), anonimización PII de
silver_people, tabla de cuarentena de calidad e índices GiST explícitos.

Revision ID: 0003_enrichment
Revises: 50201a69b9b1
Create Date: 2026-10-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_enrichment"
down_revision: Union[str, Sequence[str], None] = "50201a69b9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GIST_INDEXES = [
    ("idx_crashes_geom", "silver_crashes", "geom"),
    ("idx_crashes_geom_3435", "silver_crashes", "geom_3435"),
    ("idx_permits_geom", "silver_road_permits", "geom"),
    ("idx_permits_geom_3435", "silver_road_permits", "geom_3435"),
    ("idx_traffic_geom", "silver_traffic_counts", "geom"),
    ("idx_traffic_geom_3435", "silver_traffic_counts", "geom_3435"),
]

CRASH_COLUMNS = [
    sa.Column("lane_cnt", sa.Integer()),
    sa.Column("intersection_related_i", sa.Boolean()),
    sa.Column("hit_and_run_i", sa.Boolean()),
    sa.Column("work_zone_i", sa.Boolean()),
    sa.Column("active_workzone", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("workzone_permit_id", sa.String()),
    sa.Column("aadt_volume", sa.Integer()),
    sa.Column("aadt_distance_m", sa.Float()),
    sa.Column("aadt_imputed", sa.Boolean()),
]


def upgrade() -> None:
    # --- silver_crashes: atributos adicionales + enriquecimiento ---
    for col in CRASH_COLUMNS:
        op.add_column("silver_crashes", col)

    # --- silver_people: anonimización (cuasi-identificadores) ---
    op.drop_column("silver_people", "city")
    op.drop_column("silver_people", "zipcode")

    # --- silver_road_permits: atributos de obra ---
    op.add_column("silver_road_permits", sa.Column("work_type_description", sa.String()))
    op.add_column("silver_road_permits", sa.Column("application_type", sa.String()))
    op.add_column("silver_road_permits", sa.Column("street_closure", sa.String()))
    op.create_unique_constraint("uq_permits_permit_number", "silver_road_permits", ["permit_number"])

    # --- Tabla de cuarentena ---
    op.create_table(
        "crashes_quarantine",
        sa.Column("crash_record_id", sa.String(), primary_key=True),
        sa.Column("crash_date", sa.DateTime()),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("quarantined_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- Índices GiST (idempotentes) y B-Tree auxiliares ---
    # GeoAlchemy2 ya crea idx_<tabla>_<col> en 0002: se renombran a nombres canónicos
    # en lugar de duplicarlos (rúbrica: cero índices GiST duplicados).
    for name, table, col in GIST_INDEXES:
        op.execute(f"ALTER INDEX IF EXISTS idx_{table}_{col} RENAME TO {name}")
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} USING GIST ({col})")
    op.execute("CREATE INDEX IF NOT EXISTS idx_permits_dates ON silver_road_permits (application_start_date, application_end_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_crash ON silver_vehicles (crash_record_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_people_crash ON silver_people (crash_record_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_people_crash")
    op.execute("DROP INDEX IF EXISTS idx_vehicles_crash")
    op.execute("DROP INDEX IF EXISTS idx_permits_dates")
    for name, table, col in GIST_INDEXES:
        op.execute(f"ALTER INDEX IF EXISTS {name} RENAME TO idx_{table}_{col}")
    op.drop_table("crashes_quarantine")
    op.drop_constraint("uq_permits_permit_number", "silver_road_permits", type_="unique")
    for col in ("street_closure", "application_type", "work_type_description"):
        op.drop_column("silver_road_permits", col)
    op.add_column("silver_people", sa.Column("zipcode", sa.String()))
    op.add_column("silver_people", sa.Column("city", sa.String()))
    for col in reversed(CRASH_COLUMNS):
        op.drop_column("silver_crashes", col.name)
