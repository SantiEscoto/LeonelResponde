#!/usr/bin/env bash
set -euo pipefail

# Automate assistant-dev startup via Docker Compose
# - Frees port 8000 if occupied
# - Starts service with docker compose
# - Waits for /health to be ready
# - Prints /health and /status responses

PROJECT_ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
cd "$PROJECT_ROOT_DIR"

SERVICE_NAME="assistant-dev"
HEALTH_URL="http://localhost:8000/health"
STATUS_URL="http://localhost:8000/status"
HEALTH_TIMEOUT_SEC=90
SLEEP_INTERVAL_SEC=3

log() { echo "[assistant-dev:auto] $*"; }

require_cli() {
  if ! command -v docker >/dev/null 2>&1; then
    log "ERROR: docker CLI no disponible. Instala Docker Desktop y asegúrate que esté corriendo."
    log "Descarga: https://www.docker.com/products/docker-desktop/"
    exit 1
  fi
}

wait_for_docker() {
  local tries=0
  local max_tries=40
  while ! docker info >/dev/null 2>&1; do
    tries=$((tries+1))
    if [ "$tries" -ge "$max_tries" ]; then
      log "ERROR: Docker no está listo. Abre Docker Desktop y espera a 'Docker Desktop is running'."
      exit 1
    fi
    log "Esperando Docker Desktop... (intento $tries/$max_tries)"
    sleep 2
  done
  log "Docker listo."
}

free_port_8000() {
  local pid
  pid=$(lsof -ti tcp:8000 || true)
  if [ -n "$pid" ]; then
    log "Puerto 8000 ocupado por PID $pid. Intentando detener proceso..."
    kill -TERM "$pid" || true
    sleep 1
    if lsof -ti tcp:8000 >/dev/null 2>&1; then
      log "Proceso aún activo; enviando SIGKILL..."
      kill -KILL "$pid" || true
      sleep 1
    fi
    if lsof -ti tcp:8000 >/dev/null 2>&1; then
      log "ERROR: No se pudo liberar el puerto 8000."
      exit 1
    fi
    log "Puerto 8000 liberado."
  else
    log "Puerto 8000 libre."
  fi
}

compose_up() {
  log "Levantando $SERVICE_NAME con Docker Compose..."
  docker compose up -d --build "$SERVICE_NAME"
  log "Servicio $SERVICE_NAME levantado."
}

wait_for_health() {
  log "Esperando a que $HEALTH_URL responda 200..."
  local start_ts=$(date +%s)
  while true; do
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo "000")
    if [ "$code" = "200" ]; then
      log "Health OK (200)."
      break
    fi
    local now_ts=$(date +%s)
    local elapsed=$((now_ts - start_ts))
    if [ "$elapsed" -ge "$HEALTH_TIMEOUT_SEC" ]; then
      log "ERROR: Timeout esperando /health." 
      log "Tail de logs del servicio:" 
      docker compose logs --tail=200 "$SERVICE_NAME" || true
      exit 1
    fi
    sleep "$SLEEP_INTERVAL_SEC"
  done
}

print_json_or_raw() {
  local url="$1"
  if command -v jq >/dev/null 2>&1; then
    curl -s "$url" | jq .
  else
    curl -s "$url"
  fi
}

show_status() {
  log "Respuesta /health:" 
  print_json_or_raw "$HEALTH_URL"
  log "Respuesta /status:" 
  print_json_or_raw "$STATUS_URL"
}

compose_ps() {
  log "Estado de contenedores relevantes:" 
  docker compose ps "$SERVICE_NAME" || true
}

main() {
  log "Inicio de arranque automático de $SERVICE_NAME"
  require_cli
  wait_for_docker
  free_port_8000
  compose_up
  compose_ps
  wait_for_health
  show_status
  log "Listo: backend operativo en http://localhost:8000/"
  log "Si el frontend está en desarrollo (Vite), recarga http://localhost:3000/"
}

main "$@"