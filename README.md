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

- **Frontend**: React + TypeScript + Electron
- **Backend**: Python + FastAPI + SQLite
- **IA**: Ollama + LangChain + LoRA/QLoRA
- **Hardware**: Universal (Jetson Nano, RPi, Desktop)
- **Personalización**: Fine-tuning con identidad y conocimiento específico

## 📚 Documentación por Fases

### **🎯 Fases Esenciales (Recomendadas)**
- [📋 **Fase 1: Planificación**](./docs/01-planificacion.md) - Análisis y arquitectura
- [🧠 **Fase 2: Backend LLM**](./docs/02-backend-llm.md) - Motor principal (Core)
- [📚 **Fase 3: Base de Conocimiento**](./docs/03-conocimiento-rag.md) - Sistema RAG
- [🎯 **Fase 4: Fine-tuning**](./docs/04-finetuning.md) - Personalización completa
- [🎨 **Fase 5: Frontend UI**](./docs/05-frontend-ui.md) - Interfaz de usuario
- [🔗 **Fase 8: Integración**](./docs/08-integracion.md) - Todos los sistemas coordinados
- [⚡ **Fase 9: Optimización**](./docs/09-optimizacion.md) - Rendimiento óptimo

### **🔧 Fases Opcionales (Avanzadas)**
- [🎤 **Fase 6: Sistema de Voz**](./docs/06-voz-audio.md) - STT/TTS (Opcional)
- [👁️ **Fase 7: Sistema de Visión**](./docs/07-vision.md) - YOLO/OCR (Opcional)
- [🛠️ **Fase 10: Mantenimiento**](./docs/10-mantenimiento.md) - Evolución continua

## 🚀 Inicio Rápido

```bash
# 1. Clonar repositorio
git clone <tu-repo>
cd asistente-ia-universal

# 2. Seguir fase por fase
# Empezar con: docs/01-planificacion.md
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

## 🛠️ Templates y Recursos

- [📋 **Checklist por Fase**](./templates/checklist.md)
- [⚡ **Quick Reference**](./templates/quick-reference.md)
- [🏗️ **Estructura del Proyecto**](./templates/project-structure.md)

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

### Observabilidad (opcional)
- Desactivada por defecto. Para ver métricas, inicia solo Prometheus:
  ```bash
  docker compose -f docker-compose.observability.yml up -d prometheus
  ```
- Notificaciones (Slack/Email) deshabilitadas por defecto. Si las quieres:
  ```bash
  docker compose -f docker-compose.observability.yml up -d alertmanager
  ```
  y añade `rule_files` y `alerting` en `observabilidad/prometheus.yml`.

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

## 🎓 Recursos de Aprendizaje

### **Documentación Esencial**
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Docs](https://react.dev/)
- [LangChain Docs](https://python.langchain.com/)
- [Ollama Docs](https://ollama.ai/)

### **Comunidades**
- [FastAPI Discord](https://discord.gg/VQjSZaeJmf)
- [React Community](https://reactjs.org/community/support.html)
- [LangChain Discord](https://discord.gg/langchain)

---

**🎉 ¡Con esta guía tendrás un asistente de IA verdaderamente personalizado y único!**

*Recuerda: La clave está en seguir las fases en orden y aplicar las mejores prácticas desde el principio. ¡Buena suerte en tu proyecto!* 🚀