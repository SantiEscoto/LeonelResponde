# 📈 Observabilidad con Prometheus y Grafana

## Objetivo
Establecer una observabilidad confiable para el backend (`/metrics` y `/health`), validando el scrape desde Prometheus y visualizando en Grafana, con troubleshooting claro para macOS/Linux.

## Prerrequisitos
- Docker Desktop actualizado (Compose v2).
- Puertos libres: `9090` (Prometheus), `3000` (Grafana).
- Backend accesible en `http://127.0.0.1:8000` con `/metrics` y `/health`.

Nota: Compose v2 muestra el warning "`version` is obsolete" si el archivo incluye `version:`. Es cosmético; puedes eliminar esa línea cuando te convenga.

## Arranque rápido
```bash
# Prometheus
docker compose -f docker-compose.observabilidad.yml up -d prometheus

# Grafana
docker compose -f docker-compose.observabilidad.yml -f docker-compose.observabilidad.grafana.yml up -d grafana
```

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

Recomendado en Grafana: definir `GF_SECURITY_ADMIN_PASSWORD` vía Compose/entorno.

## Configuración de Prometheus (targets)
Para macOS, los contenedores acceden al host usando `host.docker.internal`. Ajusta `observabilidad/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'assistant-backend'
    metrics_path: /metrics
    static_configs:
      - targets: ['host.docker.internal:8000']
```

Si usas Linux y `host.docker.internal` no responde, puedes:
- Añadir `extra_hosts: ["host.docker.internal:host-gateway"]` en el servicio.
- Usar la IP del host directamente.
- Validar firewall (UFW) y permisos de red.

## Validación de salud
```bash
# Prometheus
curl -sf http://localhost:9090/-/healthy

# Grafana
curl -sf http://localhost:3000/api/health

# Backend
curl -sf http://127.0.0.1:8000/health
curl -sf 'http://127.0.0.1:8000/metrics?format=prometheus' | head -n 20
```

En Prometheus: abre `http://localhost:9090/targets` y verifica que el job `assistant-backend` esté `UP`.

## Consultas útiles (PromQL)
- Tráfico de API por segundo (si usas counter `api_requests_total`):
  ```promql
  sum(rate(api_requests_total[5m]))
  ```
- Error rate (si expones `api_request_errors_total`):
  ```promql
  sum(rate(api_request_errors_total[5m]))
  /
  sum(rate(api_requests_total[5m]))
  ```
- Latencia P95: recomienda histograma `api_latency_seconds_bucket`:
  ```promql
  histogram_quantile(0.95, sum(rate(api_latency_seconds_bucket[5m])) by (le))
  ```
  Si aún usas `summary`, considera migrar a histogramas para P90/P95/P99 consistentes.
- Carga y memoria (si el backend expone `system_load_*`, `process_resident_memory_bytes`):
  ```promql
  avg(system_load_1m)
  max(process_resident_memory_bytes)
  ```

## Grafana (datasource y dashboards)
- Datasource Prometheus apuntando a `http://prometheus:9090` desde Grafana (en Docker) o `http://localhost:9090` si accedes desde tu navegador.
- Provisioning recomendado: mantén dashboards y datasources en código (`/etc/grafana/provisioning`).
- Paneles sugeridos:
  - Tráfico y error rate de API.
  - Latencia P95/P99 por endpoint.
  - Carga, memoria y disco (si hay exporters). 

## Alertas iniciales
- API error rate > 1% (5m): alerta `warning`.
- Latencia P95 > 2s (5m): alerta `warning`.
- Target `assistant-backend` DOWN (2m): alerta `critical`.
- Espacio en disco bajo: si tienes node exporter; si no, usa señales del backend y logs.

Ejemplo (adaptar nombres de métricas):
```yaml
groups:
- name: api-alerts
  rules:
  - alert: ApiHighErrorRate
    expr: (sum(rate(api_request_errors_total[5m])) / sum(rate(api_requests_total[5m]))) > 0.01
    for: 5m
    labels: { severity: "warning" }
    annotations: { summary: "Error rate >1%" }

  - alert: ApiLatencyP95High
    expr: histogram_quantile(0.95, sum(rate(api_latency_seconds_bucket[5m])) by (le)) > 2
    for: 5m
    labels: { severity: "warning" }
    annotations: { summary: "P95 > 2s" }
```

Para notificaciones, levanta Alertmanager y configura `alerting` y `rule_files` en `prometheus.yml`.

## Troubleshooting
- "`version` is obsolete": warning de Compose v2; no bloquea.
- `DOWN` en targets:
  - Verifica que el backend esté en `127.0.0.1:8000`.
  - En macOS, usa `host.docker.internal:8000`.
  - Revisa puertos y firewall.
- Espacio en disco:
  ```bash
  docker system df
  docker system prune -af --volumes
  ```
- Logs útiles:
  ```bash
  docker compose logs --tail=200 prometheus grafana
  ```
- Red en Linux: si usas redes personalizadas, valida `extra_hosts: host-gateway` y que el host permita conexiones.

## Buenas prácticas (2024–2025)
- Evita alta cardinalidad en labels; usa etiquetas estables (endpoint, status).
- Prefiere histogramas para latencia; usa `histogram_quantile` en ventanas móviles.
- Define retención TSDB acorde a disco (por ejemplo `--storage.tsdb.retention.time=15d`).
- Versiona dashboards y datasources (provisioning) para reproducibilidad.
- Documenta procedimientos de verificación (`/-/healthy`, `/targets`, consultas clave) y de limpieza de disco.