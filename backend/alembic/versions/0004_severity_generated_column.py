"""0004_severity_generated_column

Columna generada ``severity`` (0 Bajo / 1 Moderado / 2 Crítico) materializada en
disco a partir de las lesiones y daños, con índice B-Tree para filtros de la API.

Revision ID: 0004_severity
Revises: 0003_enrichment
Create Date: 2026-10-23
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004_severity"
down_revision: Union[str, Sequence[str], None] = "0003_enrichment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Copia congelada de app.core.severity.SEVERITY_SQL (las migraciones no deben
# depender de código de la aplicación que puede cambiar).
SEVERITY_SQL = """
CASE
    WHEN coalesce(injuries_fatal, 0) > 0 OR coalesce(injuries_incapacitating, 0) > 0 THEN 2
    WHEN coalesce(injuries_non_incapacitating, 0) > 0
      OR coalesce(injuries_reported_not_evident, 0) > 0
      OR damage = 'OVER $1,500' THEN 1
    ELSE 0
END
"""


def upgrade() -> None:
    op.execute(f"ALTER TABLE silver_crashes ADD COLUMN severity smallint GENERATED ALWAYS AS ({SEVERITY_SQL}) STORED")
    op.execute("CREATE INDEX IF NOT EXISTS idx_crashes_severity ON silver_crashes (severity)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_crashes_hour ON silver_crashes (crash_hour)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_crashes_hour")
    op.execute("DROP INDEX IF EXISTS idx_crashes_severity")
    op.execute("ALTER TABLE silver_crashes DROP COLUMN severity")
