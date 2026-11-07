"""0005_tiles_geom_3857

* Columna generada ``geom_3857`` (Web Mercator) con índice GiST: las teselas MVT
  ya no transforman cada punto en cada petición ni recalculan la envolvente.
* Elimina ``ix_silver_crashes_crash_record_id``, redundante con la clave primaria.

Revision ID: 0005_tiles_geom_3857
Revises: 0004_severity
Create Date: 2026-11-07
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005_tiles_geom_3857"
down_revision: Union[str, Sequence[str], None] = "0004_severity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE silver_crashes ADD COLUMN IF NOT EXISTS geom_3857 geometry(Point, 3857) "
        "GENERATED ALWAYS AS (ST_Transform(geom, 3857)) STORED"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_crashes_geom_3857 ON silver_crashes USING GIST (geom_3857)")
    op.execute("DROP INDEX IF EXISTS ix_silver_crashes_crash_record_id")
    op.execute("ANALYZE silver_crashes")


def downgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_silver_crashes_crash_record_id ON silver_crashes (crash_record_id)"
    )
    op.execute("DROP INDEX IF EXISTS idx_crashes_geom_3857")
    op.execute("ALTER TABLE silver_crashes DROP COLUMN IF EXISTS geom_3857")
