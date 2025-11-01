# Mejoras Implementadas al 100%

Este documento resume las mejoras implementadas recientemente y cómo utilizarlas/configurarlas.

## Voz / WebSocket TTS

- Métricas nuevas registradas:
  - `voice.tts.latency_first_chunk_ms` (histograma)
    - Mide el tiempo desde `tts_start` hasta el primer `audio_chunk`.
    - Etiquetas: `provider`.
  - `voice.tts.total_time_ms` (histograma)
    - Mide el tiempo total desde `tts_start` hasta `tts_end` o `tts_interrupted`.
    - Etiquetas: `provider`, `interrupted` (`true`/`false`).
- Implementación: `Assistant/src/mcp_servers/voice_ws_server.py` integra `MetricsCollector` y registra/recoge los valores.
- Consulta de métricas:
  - Si el API expone `/metrics`, usa: `curl 'http://127.0.0.1:8000/metrics?format=prometheus'`.
  - En entorno Docker/Jetson, puedes habilitar Prometheus con `docker-compose.observabilidad.yml`.
- Robustez de interrupción:
  - El flujo de TTS fue reestructurado para procesar `stop_tts` en paralelo al streaming y emitir `tts_interrupted` con menor condición de carrera.
  - Prueba de estrés añadida: `Assistant/tests/test_voice_ws_tts_interrupt_stress.py`.

## HealthChecker configurable

- Nuevos parámetros de configuración en `HealthChecker` (archivo `Assistant/src/backend/utils/health_checker.py`):
  - `critical_components`: lista de nombres de componentes que, si fallan, elevan el estado global a `UNHEALTHY`.
  - `component_severity`: dict de overrides de severidad por nombre de componente, útil para tratar `DEGRADED` como `HEALTHY` o elevarlo a `UNHEALTHY` según el contexto.
- Ajustes clave:
  - Estado por defecto ahora depende de errores/advertencias cuando no hay componentes registrados (no retorna `UNKNOWN` arbitrariamente).
  - Soporte para componentes arbitrarios con método `get_status()` para mapear su estado a `HEALTHY/DEGRADED/UNHEALTHY`.
- Ejemplo de uso:
  ```python
  from Assistant.src.backend.utils.health_checker import HealthChecker, ComponentStatus

  hc = HealthChecker(
      critical_components=["llm", "memory"],
      component_severity={
          "llm": {ComponentStatus.DEGRADED: ComponentStatus.HEALTHY},
          "tts": {ComponentStatus.DEGRADED: ComponentStatus.UNHEALTHY},
      }
  )
  health = hc.check_system_health(components=[my_llm_component, my_tts_component])
  print(health.status)
  ```

## Observabilidad lista (Prometheus + Grafana)

- Prometheus configurado para scrapear `assistant-dev:8000/metrics?format=prometheus`.
- Grafana provisionado automáticamente:
  - Datasource `Prometheus` apuntando a `http://prometheus:9090`.
  - Dashboards iniciales en `observability/grafana/dashboards/assistant-overview.json`.
- Alertas habilitadas:
  - `observability/prometheus.yml` incluye `rule_files` y `alerting` hacia `alertmanager:9093`.
  - Reglas en `observability/alerts.yml` (error rate y latencia P95 con niveles warning/critical).
- Lanzamiento conjunto: `bash scripts/observability_up.sh`.
  - Accesos: Prometheus `http://localhost:9090`, Grafana `http://localhost:3000`.
  - Nota macOS: si Prometheus no resuelve `assistant-dev`, usar `host.docker.internal:8000` en `observability/prometheus.yml`.

## Pruebas y validación

- Ejecutar pruebas unitarias:
  - Completo: `pytest -q`
  - Solo voz/estrés: `pytest -q Assistant/tests/test_voice_ws_tts_interrupt_stress.py`
- Estado actual: toda la suite pasa en local, con aviso deprecado de `pkg_resources` (aceptable por ahora).

## Próximos pasos sugeridos

- Añadir paneles para HealthChecker y RateLimiter en Grafana.
- Documentar métricas y HealthChecker en el README (sección Observabilidad y Backend) — ya reflejado en README principal.
- Añadir más escenarios de estrés (interrupciones repetidas, mensajes fuera de orden) si es necesario.
