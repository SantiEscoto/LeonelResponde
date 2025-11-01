# 🤖 Asistente de IA Universal - Guía de Desarrollo

## 📋 Resumen Ejecutivo

Crear un **asistente de IA offline, multiusuario, con personalización completa**, optimizado para hardware limitado (Jetson Nano, Raspberry Pi, laptop vieja) con capacidades de "persona virtual" que puede socializar y gestionar atención natural.

## 🎯 Objetivos Clave

- ✅ **Funcionamiento Universal**: Hardware limitado (Jetson Nano, Raspberry Pi, laptop vieja)
- ✅ **Multiusuario**: Conversaciones separadas simultáneas con identificación automática
- ✅ **Personalización Completa**: Fine-tuning para identidad y conocimiento específico
- ✅ **Interfaz Social**: "Persona virtual" con atención social natural
- ✅ **Capacidades Agénticas**: Futuras automatizaciones del sistema
- ✅ **Optimización Máxima**: Recursos mínimos, rendimiento máximo

## 🏗️ Stack Tecnológico

- **Frontend**: React + TypeScript
- **Backend**: Python + FastAPI + SQLite
- **IA**: llama-cpp-python + FAISS + Sentence-Transformers (RAG opcional)
- **Hardware**: Universal (Jetson Nano, RPi, Desktop)
- **Personalización**: Fine-tuning con identidad y conocimiento específico

## 📚 Documentación y Backlog

### Fases vigentes
- [🎨 Frontend UI](./docs/05-frontend-ui.md)
- [🎤 Sistema de Voz](./docs/06-voz-audio.md)

### Backlog / WIP (referencias heredadas, siguen siendo útiles para mejoras)
- [📋 Fase 1: Planificación](./docs/_archive/01-planificacion.md)
- [🧠 Fase 2: Backend LLM](./docs/_archive/02-backend-llm.md)
- [📚 Fase 3: Base de Conocimiento](./docs/_archive/03-conocimiento-rag.md)
- [🎯 Fase 4: Fine-tuning](./docs/_archive/04-finetuning.md)
- [👁️ Fase 7: Visión](./docs/_archive/07-vision.md)
- [🔗 Fase 8: Integración](./docs/_archive/08-integracion.md)
- [⚡ Fase 9: Optimización](./docs/_archive/09-optimizacion.md)
- [🛠️ Fase 10: Mantenimiento](./docs/_archive/10-mantenimiento.md)

Para más contexto: ver `docs/_archive/README.md`.

## 🚀 Inicio Rápido

```bash
# 1. Clonar repositorio
git clone <tu-repo>
cd LeonelResponde

# 2. Seguir fase por fase
# Empezar con: docs/_archive/01-planificacion.md (Backlog/WIP)
```

## 📊 Progreso del Proyecto

- [x] **Fase 1**: Planificación (Completado)
- [x] **Fase 2**: Backend LLM (MVP)
- [x] **Fase 3**: Base de Conocimiento (MVP)
- [ ] **Fase 4**: Fine-tuning (Semana 4-5)
- [x] **Fase 5**: Frontend UI (MVP)
- [x] **Fase 6**: Sistema de Voz (MVP básico)
- [ ] **Fase 7**: Sistema de Visión (Opcional)
- [x] **Fase 8**: Integración (MVP básico)
- [ ] **Fase 9**: Optimización (Semana 7-8)
- [ ] **Fase 10**: Mantenimiento (Continuo)

## 🎯 Características Únicas

### **🧠 Personalización Completa**
- **Identidad Única**: Personalidad, tono, estilo de comunicación
- **Conocimiento Específico**: Expertise en tu dominio
- **Fine-tuning Eficiente**: LoRA/QLoRA para hardware limitado
- **Interfaz de Desarrollador**: Personalización sin código

### **👥 Multiusuario Social**
- **Atención Natural**: Como una persona real
- **Identificación Automática**: Por voz y características
- **Gestión de Prioridades**: Interrupciones inteligentes
- **Memoria Separada**: Por usuario y relación

### **⚡ Optimización Universal**
- **Hardware Limitado**: Jetson Nano, Raspberry Pi, laptop vieja
- **Detección Automática**: Configuración según hardware
- **Recursos Mínimos**: Máximo rendimiento con mínimo hardware
- **Escalabilidad**: De 1 a 6 usuarios simultáneos

## 📈 Métricas de Éxito

- **Performance**: < 2s tiempo de respuesta
- **Disponibilidad**: 99.9% uptime
- **Personalización**: > 95% satisfacción con identidad
- **Usabilidad**: < 3 clics para tareas principales
- **Escalabilidad**: 1-6 usuarios simultáneos

## 🐧 Jetson Orin Nano (Docker Compose)

### Prerrequisitos
- Instala NVIDIA Container Toolkit:
  ```bash
  sudo apt-get install -y nvidia-container-toolkit \
    && sudo nvidia-ctk runtime configure --runtime=docker \
    && sudo systemctl restart docker
  ```

### Arranque rápido del API
- Con GPU y override Jetson:
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.jetson.yml up -d assistant-dev
  ```
- Verificación:
  ```bash
  curl -s -D - 'http://127.0.0.1:8000/metrics?format=prometheus' -o /dev/null
  curl 'http://127.0.0.1:8000/health'
  ```

### Observabilidad (Prometheus/Grafana)
- Docker Compose v2 avisa que `version:` está obsoleto. Es un warning cosmético y no bloquea; recomendamos eliminarlo cuando convenga.
- Arranque rápido de Prometheus y Grafana:
  ```bash
  docker compose -f docker-compose.observability.yml up -d prometheus
  docker compose -f docker-compose.observability.yml -f docker-compose.observabilidad.grafana.yml up -d grafana
  ```
- macOS: si Prometheus no resuelve `assistant-dev`, usa `host.docker.internal:8000` en `observabilidad/prometheus.yml`.
- Verificación de salud:
  ```bash
  curl -sf http://localhost:9090/-/healthy
  curl -sf http://localhost:3000/api/health
  ```
- Troubleshooting rápido (espacio en disco y logs):
  ```bash
  docker system df
  docker system prune -af --volumes
  docker compose logs --tail=200 prometheus grafana
  ```
- Guía completa y mejores prácticas: ver `./docs/07-observabilidad.md`.

### Script de ayuda
- Por defecto solo arranca el API. Opciones:
  ```bash
  ./scripts/run_jetson.sh                      # solo API
  ./scripts/run_jetson.sh --observabilidad     # + Prometheus
  ./scripts/run_jetson.sh --rebuild            # fuerza rebuild
  ```
- Para notificaciones (Alertmanager), inícialo manualmente:
  ```bash
  docker compose -f docker-compose.observability.yml up -d alertmanager
  ```

### Notas de GPU (llama-cpp)
- El contenedor instala `cmake` y `ninja-build`. Para CUDA:
  - Override ya define `CMAKE_ARGS=-DGGML_CUDA=on -DGGML_CUDA_F16=on` y `FORCE_CMAKE=1`.
  - Si prefieres CPU, elimina estas variables y usa `DISABLE_LLM_PRELOAD=1`.
- En Jetson no hay `nvidia-smi`; valida con rendimiento o `ldconfig -p | grep libcuda`.

## 🐧 Jetson Orin Nano (Bare-metal, sin Docker)

### Prerrequisitos
- Ubuntu 22.04 (JetPack actualizado)
- Paquetes del sistema:
  ```bash
  sudo apt-get update && sudo apt-get install -y \
    python3-venv python3-pip ffmpeg libasound2-dev portaudio19-dev
  ```

### Instalación
```bash
# 1) Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 2) Actualizar pip
pip install --upgrade pip

# 3) Instalar requisitos compatibles con ARM/Jetson
pip install -r Assistant/requirements-jetson.txt
```

### Ejecución
```bash
# API básica (sin RAG/FAISS ni embeddings)
DISABLE_LLM_PRELOAD=1 \
DISABLE_COQUI=1 \
python Assistant/main.py --api --dry-init

# Voice WS (ver docs/06-voz-audio.md)
# Por defecto TTS está desactivado; si instalas Coqui XTTS (TTS), se usa Coqui; `stop_tts` soportado.
# Inicia desde Docker o en otro terminal si lo necesitas.
```

### Limitaciones en Jetson (por defecto)
- RAG/Embeddings desactivados: no se instalan `faiss-cpu`, `sentence-transformers` ni `torch`.
- Si necesitas RAG, instala manualmente:
  - `faiss` desde fuente para aarch64.
  - PyTorch para Jetson (ruedas NVIDIA, según JetPack) y después `sentence-transformers`.
- TTS Coqui (XTTS) desactivado: puedes habilitarlo instalando `TTS` y sus dependencias.

### Compatibilidad de requirements
- `Assistant/requirements-jetson.txt`: API + Voz sin dependencias pesadas.
- Docker (override Jetson) pasa `build args` para instalar ese archivo automáticamente.

## 🔌 Integraciones MCP (servers.json)

- Define `mcpServers` en `servers.json` para habilitar herramientas del sistema (OS, Files).
- Ejemplo mínimo:
  ```json
  {
    "mcpServers": {
      "fs": { "command": "node", "args": ["./mcp/fs/index.js"] },
      "os": { "command": "bash", "args": ["./mcp/os.sh"], "env": { "SAFE_MODE": "1" } }
    }
  }
  ```
- No guardes secretos en `servers.json`; usa variables de entorno.
- Ubicación recomendada: `Assistant/servers.json` o raíz del proyecto.
- El backend detecta y registra servidores MCP al inicializar.

## 🎓 Recursos de Aprendizaje

### **Documentación Esencial**
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Docs](https://react.dev/)
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Sentence-Transformers](https://www.sbert.net/)

### **Comunidades**
- [FastAPI Discord](https://discord.gg/VQjSZaeJmf)
- [React Community](https://reactjs.org/community/support.html)
- [FAISS Discussions](https://github.com/facebookresearch/faiss/discussions)

---

**🎉 ¡Con esta guía tendrás un asistente de IA verdaderamente personalizado y único!**

*Recuerda: La clave está en seguir las fases en orden y aplicar las mejores prácticas desde el principio. ¡Buena suerte en tu proyecto!* 🚀

## ✅ Checklist por Áreas

- Infra / Despliegue
  - [x] Autodetección de hardware `--auto` en `Assistant/main.py`
  - [x] `docker-compose.jetson.yml` arranca API con `--auto`
  - [x] Script `scripts/start.sh` para arranque con autodetección
  - [ ] Validación CI de `scripts/start.sh` en Ubuntu/macOS

- Backend / LLM
  - [x] HealthChecker: estado por defecto, componentes arbitrarios, severidad configurable
  - [ ] Optimización de `n_ctx` y `n_threads` en ARM sin GPU (afinación)

- Voz / WebSocket
  - [x] Interrupción TTS robusta y métricas de latencia en WS
  - [x] Import de tests corregido con `pytest.ini` y `pythonpath = Assistant`

- Observabilidad
  - [x] Endpoint `/metrics` con exportación Prometheus
  - [x] Dashboard básico en Grafana (datasource Prometheus + paneles iniciales)
  - [x] Métricas TTS: `voice.tts.latency_first_chunk_ms`, `voice.tts.total_time_ms`
  - [ ] Alertas iniciales (latencia P95, error rate)

- Frontend UI
  - [x] UI React en `frontend/` (MVP)
  - [ ] Exponer health/metrics en UI (panel de estado)

Ver detalle y estados en `docs/notes/CHECKLIST_AREAS.md`. Más mejoras: `docs/notes/MEJORAS_100_PERCENT.md`.