#!/bin/sh
set -e

echo "[Chicago Backend] Verificando conexión a PostgreSQL y ejecutando migraciones..."
alembic upgrade head

echo "[Chicago Backend] Migraciones aplicadas con éxito. Iniciando proceso: $*"
exec "$@"
