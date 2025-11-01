# ✅ Checklist por Áreas

Estado y pendientes de iniciativas clave por área del proyecto.

## Infra / Despliegue
- [x] Autodetección de hardware `--auto` en `Assistant/main.py`
- [x] `docker-compose.jetson.yml` arranca API con `--auto`
- [x] Script `scripts/start.sh` para arranque con autodetección
- [ ] Validación CI de `scripts/start.sh` en Ubuntu/macOS

## Backend / LLM
- [x] Integración de autodetección con `LLMConfig` (device, n_gpu_layers, n_threads)
- [ ] Afinar `n_ctx` y `n_threads` en ARM sin GPU (heurísticas adicionales)
- [x] HealthChecker configurable (estado por defecto, componentes arbitrarios, severidad)

## Voz / WebSocket
- [x] Servidor de voz WS funcional (modo demo)
- [x] Import en `tests/test_voice_ws_tts_interrupt.py` corregido (`pytest.ini`/`pythonpath`)
- [x] Tests de interrupción TTS robustos (incluye prueba de estrés)

## Observabilidad
- [x] Endpoint `/metrics` con exportación Prometheus
- [x] Dashboard básico en Grafana para API y sistema
- [ ] Alertas iniciales (latencia P95, error rate)

## Frontend UI
- [x] UI React en `frontend/` (MVP)
- [ ] Exponer health/metrics en UI (panel de estado)

## Próximos pasos sugeridos
- [ ] Documentar `scripts/start.sh` en `Assistant/README.md` (uso y modos)
- [ ] Agregar job de CI que ejecute `scripts/start.sh --test`