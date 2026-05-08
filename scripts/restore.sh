#!/usr/bin/env bash
# Restaura un backup creado por scripts/backup.sh.
#
# Requiere sudo: maneja archivos con ownership de containers (UID 999 para
# postgres) y restaura permisos correctos.
#
# Asume que los containers están detenidos. Sobrescribe contenido existente
# en volumes/{postgres,qdrant,uploads} — pide confirmación si esos directorios
# ya tienen datos (a menos que pases --yes).
#
# Uso:
#   sudo ./scripts/restore.sh ~/rag-da-backup-20260504-0830.tar.gz
#   sudo ./scripts/restore.sh -y backup.tar.gz       # sin confirmación

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

REAL_USER="${SUDO_USER:-$USER}"

YES=0
ARCHIVE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes|-y) YES=1; shift ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *)
      if [[ -z "$ARCHIVE" ]]; then ARCHIVE="$1"; shift; else
        echo "ERROR: argumento extra: $1" >&2; exit 2
      fi
      ;;
  esac
done

if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: este script requiere sudo." >&2
  echo "Ejecuta:  sudo $0 $*" >&2
  exit 1
fi

if [[ -z "$ARCHIVE" || ! -f "$ARCHIVE" ]]; then
  echo "Uso: sudo $0 [-y] <archivo.tar.gz>" >&2
  exit 2
fi

# No puede haber containers corriendo
RUNNING=$(docker compose ps --services --filter "status=running" 2>/dev/null | grep -c . || true)
if [[ "$RUNNING" -gt 0 ]]; then
  echo "ERROR: hay $RUNNING containers corriendo. Detén primero:" >&2
  echo "  docker compose --profile prod down" >&2
  exit 1
fi

# Confirmar si hay datos existentes
HAS_DATA=0
for d in volumes/postgres volumes/qdrant volumes/uploads; do
  if [[ -d "$d" ]] && find "$d" -mindepth 1 -print -quit 2>/dev/null | grep -q .; then
    HAS_DATA=1; break
  fi
done

if [[ "$HAS_DATA" -eq 1 && "$YES" -eq 0 ]]; then
  echo "AVISO: volumes/{postgres,qdrant,uploads} ya tienen datos."
  read -p "¿Sobrescribir? [y/N] " resp
  if [[ "${resp,,}" != "y" && "${resp,,}" != "yes" && "${resp,,}" != "s" ]]; then
    echo "Cancelado."; exit 0
  fi
fi

echo "Limpiando volúmenes anteriores..."
rm -rf volumes/postgres volumes/qdrant volumes/uploads

echo "Extrayendo $ARCHIVE..."
tar -xzf "$ARCHIVE" -C "$REPO_DIR"

# Restaurar permisos correctos
# - Postgres alpine corre como UID 999
# - Qdrant corre como root dentro del container; los archivos del tar ya
#   vienen con sus owners pero los reseteamos a UID 0 (root) por si acaso
# - Uploads pertenece al usuario host (backend prod los lee montados)
chown -R 999:999 volumes/postgres
chown -R 0:0 volumes/qdrant
chown -R "$REAL_USER:$REAL_USER" volumes/uploads

echo ""
echo "✓ Restore completado."
echo ""
echo "Siguientes pasos:"
echo "  1. cp backend/.env.example backend/.env  (si no existe)"
echo "  2. Verificar que Ollama esté arriba con los modelos descargados:"
echo "       curl -s http://localhost:11434/api/tags | grep -E 'gpt-oss|qwen3-embedding'"
echo "  3. docker compose --profile prod up -d"
echo "  4. curl -s http://localhost:8000/api/health"
