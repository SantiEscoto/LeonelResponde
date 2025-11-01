#!/usr/bin/env bash
set -euo pipefail

# Script de arranque simple con autodetección
# Uso:
#   scripts/start.sh [--api|--interactive|--voice-ws|--test|--dry-init] [args]
# Por defecto arranca el API.

# Ir al raíz del repo
cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"
ASSISTANT_DIR="$REPO_ROOT/Assistant"

if [[ ! -d "$ASSISTANT_DIR" ]]; then
  echo "[ERROR] No se encontró el directorio Assistant en: $ASSISTANT_DIR" >&2
  exit 1
fi

MODE="--api"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api|--interactive|--voice-ws|--test|--dry-init)
      MODE="$1"
      shift
      ;;
    -h|--help)
      echo "Uso: $0 [--api|--interactive|--voice-ws|--test|--dry-init] [args...]"
      echo "Ejemplos:" 
      echo "  $0                 # Arranca API con autodetección"
      echo "  $0 --interactive   # Modo consola interactivo con autodetección"
      echo "  $0 --voice-ws      # Arranca servidor de voz WS con autodetección"
      echo "  $0 --test          # Ejecuta tests de integración con autodetección"
      exit 0
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

cd "$ASSISTANT_DIR"
PYTHON_BIN=${PYTHON_BIN:-python3}

# Evitar variable de array no inicializada con set -u
if ((${#EXTRA_ARGS[@]:-0})); then
  exec "$PYTHON_BIN" main.py --auto "$MODE" "${EXTRA_ARGS[@]}"
else
  exec "$PYTHON_BIN" main.py --auto "$MODE"
fi