# Leonel Responde - Fase 1

## Asistente Multimodal Offline

Este proyecto implementa un asistente multimodal offline diseñado para funcionar en dispositivos como Jetson Nano sin necesidad de conexión a internet. La Fase 1 se centra en el motor LLM local con memoria y base de conocimiento.

## Características de la Fase 1

- **Motor LLM Local**: Implementación de un motor de lenguaje local utilizando modelos GGUF cuantizados a través de `llama-cpp-python`.
- **Sistema de Memoria Avanzado**: 
  - Memoria a corto plazo (50 interacciones con persistencia automática)
  - Transición automática a largo plazo (25 interacciones)
  - Organización por grupos conceptuales
  - Gestión granular con metadatos enriquecidos
  - Guardado automático después de cada interacción
  - Sistema de respaldo automático cada 20 interacciones
- **Base de Conocimiento**: Sistema de recuperación de información basado en embeddings utilizando FAISS y SentenceTransformers.
- **Interfaces de Usuario Múltiples**:
  - Interfaz de consola tradicional para servidores y desarrollo
  - Interfaz gráfica moderna con PySide6 para uso desktop
  - Capa de abstracción que permite cambiar entre interfaces sin modificar la lógica de negocio
- **API REST**: Interfaz REST para interactuar con el sistema desde aplicaciones externas.
- **Documentación Consolidada**: Documentación organizada en directorio `docs/` con guías completas.

## Requisitos

- Python 3.11+
- Dependencias listadas en `requirements.txt`
- Modelos descargados (ver sección de modelos)

## Instalación

1. Clonar el repositorio:

```bash
git clone https://github.com/SantiEscoto/LeonelResponde.git
cd LeonelResponde/Assistant
```

2. Crear y activar entorno virtual:

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Descargar modelos necesarios (ver sección de modelos).

## Modelos

Para el funcionamiento completo, se requieren los siguientes modelos:

1. **Modelo LLM**: Descargar un modelo GGUF (recomendado Mistral-7B-Instruct cuantizado) y colocarlo en la carpeta `./models/`.

2. **Modelo de Embeddings**: El sistema descargará automáticamente el modelo `all-MiniLM-L6-v2` de SentenceTransformers la primera vez que se ejecute.

### Enlaces de descarga recomendados

- [Mistral-7B-Instruct-v0.1.Q4_K_M.gguf](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/mistral-7b-instruct-v0.1.Q4_K_M.gguf) (4.1GB)
- [Mistral-7B-Instruct.Q4_K_M.gguf](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/mistral-7b-instruct-v0.1.Q4_K_M.gguf) (3.8GB)

## Uso

### Script de arranque con autodetección

El script `scripts/start.sh` permite iniciar el sistema con autodetección de hardware y modo deseado:

```bash
# Desde la raíz del repo
./scripts/start.sh               # Arranca API con autodetección
./scripts/start.sh --interactive # Consola interactiva con autodetección
./scripts/start.sh --voice-ws    # Servidor de voz WebSocket con autodetección
./scripts/start.sh --test        # Ejecuta pruebas de integración
```

Notas:
- Usa `PYTHON_BIN` para seleccionar intérprete (por defecto `python3`).
- Pasa argumentos extras al final: `./scripts/start.sh --api --dry-init`.

### Interfaces de Usuario

El asistente ahora soporta múltiples interfaces de usuario:

#### Interfaz de Consola (Tradicional)
```bash
python main.py --ui console
```
- Interfaz por línea de comandos
- Ideal para servidores y desarrollo
- Comandos especiales con `/` (ej: `/help`, `/status`)

#### Interfaz Gráfica PySide6 (Moderna)
```bash
python main.py --ui pyside6
```
- Interfaz gráfica moderna con Qt
- Botones para controlar micrófono y TTS
- Área de conversación en tiempo real
- Controles visuales del estado del sistema

#### Demo de Interfaces
```bash
python demo_ui.py
```
- Script de demostración para probar ambas interfaces
- Información detallada sobre las características de cada interfaz

### Servidor API

Para iniciar el servidor API:

```bash
python main.py --api
```

El servidor se iniciará en `http://127.0.0.1:8000` por defecto. Endpoints disponibles:

- `GET /` - Verificar que la API está funcionando
- `GET /status` - Obtener estado del sistema
- `POST /query` - Enviar consulta al LLM
- `POST /clear-memory` - Limpiar memoria de conversación
- `POST /add-document` - Agregar documento a la base de conocimiento

#### Observabilidad y métricas (/metrics)

- Endpoint: `GET /metrics`
- Parámetros:
  - `format`: `json` (default) o `prometheus`. En `prometheus`, devuelve `Content-Type: text/plain`.
  - `category`: filtro opcional (`system`, `api`, `llm`, `memory`, `knowledge_base`, `custom`).
  - `window`: ventana de tiempo en segundos para resumen estadístico.
  - `include_points`: `true|false` para incluir puntos históricos (solo en `json`).
- Ejemplos:
  - `curl -s http://127.0.0.1:8000/metrics?format=json&category=api`
  - `curl -i http://127.0.0.1:8000/metrics?format=prometheus`
  - `curl -s 'http://127.0.0.1:8000/metrics?format=json&category=api&window=300'`
- Notas:
  - El middleware de timing registra `api.requests_total`, `api.requests_success`, `api.requests_error` y `api.latency_seconds` automáticamente.
  - Al consultar `/metrics`, también se muestrean métricas del sistema.

##### Script rápido: observabilidad local

Para levantar API + Prometheus + Grafana juntos:

```bash
bash scripts/observability_up.sh
# Abrir Prometheus: http://localhost:9090
# Abrir Grafana:    http://localhost:3000
```

Notas:
- macOS: si Prometheus no resuelve `assistant-dev`, sustituir el target por `host.docker.internal:8000` en `observability/prometheus.yml`.
- Alertas: `observability/prometheus.yml` ya incluye `rule_files` y `alerting` hacia `alertmanager:9093`; inicia Alertmanager si quieres notificaciones.

##### Ejemplo de scrape_config para Prometheus

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'leonel_responde_api'
    metrics_path: /metrics
    params:
      format: [prometheus]
    static_configs:
      - targets: ['127.0.0.1:8000']
```

##### Alertmanager y alerting (resumen)

```yaml
# prometheus.yml (fragmento)
rule_files:
  - /etc/prometheus/alerts.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

Para configuración de receptores (Slack/Email), ver `observability/alertmanager.yml`.