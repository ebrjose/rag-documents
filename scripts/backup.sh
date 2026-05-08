#!/usr/bin/env bash
# Empaqueta los volúmenes con estado (postgres + qdrant + uploads) en un .tar.gz.
#
# Requiere sudo: los archivos de Postgres son UID 999 (alpine container user)
# y no son legibles por el usuario host. Ejecuta el script con sudo.
#
# Asume que los containers están detenidos para un snapshot consistente.
#
# Uso:
#   sudo ./scripts/backup.sh
#   sudo ./scripts/backup.sh --output /ruta/file.tar.gz
#   sudo ./scripts/backup.sh --force          # ignora si hay containers corriendo
#
# Tras el backup, el archivo queda con ownership del usuario que invocó sudo
# (no de root), gracias a SUDO_USER.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

# Si se ejecutó con sudo, recuperamos el usuario original
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"

OUTPUT="$REAL_HOME/rag-da-backup-$(date +%Y%m%d-%H%M).tar.gz"
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output|-o) OUTPUT="$2"; shift 2 ;;
    --force|-f)  FORCE=1; shift ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *) echo "ERROR: opción desconocida: $1" >&2; exit 2 ;;
  esac
done

# Verificar permisos
if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: este script requiere sudo (postgres data es UID 999)." >&2
  echo "Ejecuta:  sudo $0 $*" >&2
  exit 1
fi

# Verificar que no haya containers corriendo
RUNNING=$(docker compose ps --services --filter "status=running" 2>/dev/null | grep -c . || true)
if [[ "$RUNNING" -gt 0 && "$FORCE" -eq 0 ]]; then
  echo "ERROR: hay $RUNNING containers corriendo. Detén el stack primero:" >&2
  echo "  docker compose --profile prod down" >&2
  echo "  (o usa --force para backup en caliente, no recomendado)" >&2
  exit 1
fi

# Verificar volúmenes
for d in volumes/postgres volumes/qdrant volumes/uploads; do
  if [[ ! -d "$d" ]]; then
    echo "ERROR: no existe $d" >&2
    exit 1
  fi
done

echo "Tamaño de los volúmenes a respaldar:"
du -sh volumes/postgres volumes/qdrant volumes/uploads
echo ""
echo "Empaquetando a: $OUTPUT"
echo ""

tar -czf "$OUTPUT" \
  volumes/postgres \
  volumes/qdrant \
  volumes/uploads

# Devolver ownership al usuario original
chown "$REAL_USER:$REAL_USER" "$OUTPUT"

SIZE=$(du -h "$OUTPUT" | cut -f1)
echo ""
echo "✓ Backup creado: $OUTPUT ($SIZE)"
echo ""
echo "Para restaurar en otro PC:"
echo "  sudo ./scripts/restore.sh $OUTPUT"
