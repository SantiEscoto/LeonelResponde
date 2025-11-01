#!/usr/bin/env bash
set -euo pipefail

# Levanta API, Prometheus, Alertmanager y Grafana en la misma red de Compose
# Uso:
#   scripts/observability_up.sh

PROJECT_ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
cd "$PROJECT_ROOT_DIR"

log() { echo "[observability] $*"; }

require_cli() {
  if ! command -v docker >/dev/null 2>&1; then
    log "ERROR: docker CLI no disponible. Instala Docker Desktop."
    exit 1
  fi
}

compose_up() {
  log "Levantando stack: assistant-dev + prometheus + alertmanager + grafana..."
  docker compose \
    -f docker-compose.yml \
    -f docker-compose.observability.yml \
    -f docker-compose.observabilidad.grafana.yml \
    up -d --build assistant-dev prometheus alertmanager grafana
  log "Servicios levantados."
}

show_urls() {
  log "Prometheus: http://localhost:9090/"
  log "Grafana:    http://localhost:3000/ (admin/admin)"
  log "Backend:    http://localhost:8000/metrics?format=prometheus"
}

main() {
  require_cli
  compose_up
  show_urls
}

main "$@"