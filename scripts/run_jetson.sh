#!/usr/bin/env bash
set -euo pipefail

# Lanzador de servicios para Jetson Orin Nano
# - Arranca assistant-dev con GPU y API
# - Observabilidad opcional (desactivada por defecto)

COMPOSE_BASE="docker-compose.yml"
COMPOSE_JETSON="docker-compose.jetson.yml"
COMPOSE_OBS="docker-compose.observability.yml"

function usage() {
  echo "Uso: $0 [--observability] [--rebuild]"
  echo "  --observability       Arranca Prometheus (Alertmanager no se inicia por defecto)"
  echo "  --rebuild            Fuerza rebuild de la imagen"
}

NO_OBS=1
REBUILD=0
for arg in "$@"; do
  case "$arg" in
    --observability) NO_OBS=0 ; shift ;;
    --rebuild) REBUILD=1 ; shift ;;
    -h|--help) usage ; exit 0 ;;
    *) ;;
  esac
done

# Verificar NVIDIA Container Toolkit
if ! command -v nvidia-ctk >/dev/null 2>&1; then
  echo "[WARN] NVIDIA Container Toolkit no detectado. Instala con:"
  echo "  sudo apt-get install -y nvidia-container-toolkit && sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker"
fi

# Arrancar assistant-dev con override Jetson
if [[ $REBUILD -eq 1 ]]; then
  docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_JETSON" build --no-cache assistant-dev
fi

docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_JETSON" up -d assistant-dev

echo "[INFO] Assistant API arrancando. Verifica salud y métricas:"
echo "  curl -s -D - 'http://127.0.0.1:8000/metrics?format=prometheus' -o /dev/null"
echo "  curl 'http://127.0.0.1:8000/health'"

# Arrancar observabilidad solo si se solicita
if [[ $NO_OBS -eq 0 ]]; then
  docker compose -f "$COMPOSE_OBS" up -d prometheus
  echo "[INFO] Prometheus listo: http://127.0.0.1:9090"
  echo "[INFO] Alertmanager NO se inicia por defecto. Si quieres notificaciones:"
  echo "  docker compose -f $COMPOSE_OBS up -d alertmanager"
fi

echo "[DONE] Jetson services en marcha."