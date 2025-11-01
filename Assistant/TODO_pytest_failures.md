# TODO: Revisar fallos de pytest en tests/test_improvements.py

Contexto:
- Tras hacer opcional el import de KnowledgeBase en `src/backend/api.py`, la API arranca y funciona con estado `DEGRADED` cuando LLM no está precargado y KB no está inicializada.
- El script `Assistant/validate_improvements.py` ejecuta 7 validaciones y pasa con exit code 0.
- Sin embargo, ejecutar `pytest Assistant/tests/test_improvements.py -q` falla con `AssertionError` en `TestHealthChecker` (`test_health_check_basic` y `test_health_check_with_components`). El estado reportado es `UNHEALTHY/UNKNOWN` por LLM Manager y KB no inicializados.

Reproducción:
- Comando: `pytest Assistant/tests/test_improvements.py -q`
- Entorno sugerido: `TOKENIZERS_PARALLELISM=false`, `OMP_NUM_THREADS=1`, `DISABLE_LLM_PRELOAD=1`.

Observado:
- Expectativas de los tests asumen ciertos componentes inicializados (LLM Manager, Memory Manager, KB), o estados más permisivos.
- La inicialización real, con `--dry-init` y carga perezosa, produce estado `DEGRADED`/`UNHEALTHY` que no coincide con las aserciones.

Hipótesis:
- Los tests deberían contemplar la configuración de carga perezosa y KB opcional, o inicializar explícitamente stubs/mocks de LLM/KB para escenarios de `HEALTHY`.
- Alternativamente, separar en dos grupos (unitarios vs contexto) como se sugiere en `README_TESTS.md`.

Plan de acción propuesto:
1) Revisar aserciones en `tests/test_improvements.py` para alinearlas con modos `lazy` y KB opcional.
2) Añadir fixtures/mocks que simulen `LLMManager` cargado y `KnowledgeBase` disponible cuando el test lo requiera.
3) Si procede, mover checks más pesados a grupo `--forked`.
4) Documentar en `README_TESTS.md` las expectativas/entornos de cada test.

Estado:
- Pendiente de revisión y ajuste.