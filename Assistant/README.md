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

### Modo Interactivo

Para iniciar el asistente en modo interactivo:

```bash
# Interfaz de consola (tradicional)
python main.py --interactive

# Interfaz gráfica moderna (PySide6)
python main.py --ui pyside6
```

Comandos especiales en modo interactivo:

**🔧 SISTEMA:**
- `/help` - Mostrar ayuda completa de comandos
- `/salir` - Terminar la sesión
- `/status` - Ver estado de todos los componentes
- `/resources` - Ver información detallada de recursos

**💾 MEMORIA:**
- `/clear` - Limpiar toda la memoria
- `/memory` - Ver estado de la memoria
- `/list_short` - Ver interacciones de memoria a corto plazo
- `/list_long` - Ver interacciones de memoria a largo plazo
- `/delete_short [índice]` - Borrar interacción específica (corto plazo)
- `/delete_long [índice]` - Borrar interacción específica (largo plazo)

**📚 CONOCIMIENTO:**
- `/rag on|off` - Activar/desactivar búsqueda RAG
- `/add <texto>` - Agregar texto a la base de conocimiento

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

Opcional:
- Para filtrar por categoría, agrega `category` en `params` (ej. `api`).
- Si estás detrás de un reverse proxy, ajusta `metrics_path` y `targets` conforme a tu despliegue.

##### Ejemplo docker-compose.yml con Prometheus

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'leonel_responde_api'
    metrics_path: /metrics
    params:
      format: [prometheus]
    static_configs:
      - targets: ['assistant-dev:8000']
```

```yaml
# docker-compose.yml (fragmento)
services:
  assistant-dev:
    ports:
      - "8000:8000"
    # Inicia la API dentro de este servicio

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "9090:9090"
```

Notas:
- Los servicios en el mismo `docker-compose` comparten red y se resuelven por nombre.
- Ajusta `targets` si cambias el nombre del servicio o puerto.

#### Reglas de alerta (Prometheus)

Para activar reglas de alerta, añade en `prometheus.yml`:

```yaml
rule_files:
  - alerts.yml
```

Ejemplo `alerts.yml`:

```yaml
groups:
  - name: leonel_responde_alerts
    rules:
      - alert: LeonelHighErrorRate
        expr: (increase(api_requests_error[5m]) / clamp_min(increase(api_requests_total[5m]), 1)) > 0.10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Alta tasa de errores en la API (>10% en 5m)"
          description: "Error rate={{ $value | printf \"%.2f\" }} en los últimos 5m."

      - alert: LeonelHighLatencyP95
        expr: histogram_quantile(0.95, sum by (le) (rate(api_latency_seconds_bucket[5m]))) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Latencia P95 elevada (>800ms en 5m)"
          description: "P95={{ $value | printf \"%.3f\" }}s en los últimos 5m."

      - alert: LeonelCriticalErrorRate
        expr: (increase(api_requests_error[5m]) / clamp_min(increase(api_requests_total[5m]), 1)) > 0.20
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Tasa de errores crítica en la API (>20% en 5m)"
          description: "Error rate={{ $value | printf \"%.2f\" }} en los últimos 5m."

      - alert: LeonelCriticalLatencyP95
        expr: histogram_quantile(0.95, sum by (le) (rate(api_latency_seconds_bucket[5m]))) > 1.5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Latencia P95 crítica (>1.5s en 5m)"
          description: "P95={{ $value | printf \"%.3f\" }}s en los últimos 5m."
```

Notas:
- Ajusta umbrales según tu entorno (ej. 5%/15% y 500ms/1000ms).
- Para reglas críticas, duplica la regla con otro `alert` y `severity: critical`.
- Si tu Prometheus requiere nombres sin puntos, puedes normalizarlos con `metric_relabel_configs` en la `scrape_config`:

```yaml
scrape_configs:
  - job_name: 'leonel_responde_api'
    metrics_path: /metrics
    params:
      format: [prometheus]
    static_configs:
      - targets: ['assistant-dev:8000']
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: api\.requests_total
        target_label: __name__
        replacement: api_requests_total
      - source_labels: [__name__]
        regex: api\.requests_success
        target_label: __name__
        replacement: api_requests_success
      - source_labels: [__name__]
        regex: api\.requests_error
        target_label: __name__
        replacement: api_requests_error
      - source_labels: [__name__]
        regex: api\.latency_seconds(.*)
        target_label: __name__
        replacement: api_latency_seconds$1
```

##### Alertmanager y alerting

Añade el bloque de alerting en `prometheus.yml` para que Prometheus envíe alertas al Alertmanager:

```yaml
# prometheus.yml (fragmento)
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'alertmanager:9093'
```

Servicio `alertmanager` en `docker-compose.yml`:

```yaml
services:
  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    ports:
      - "9093:9093"
```

Ejemplo básico de `alertmanager.yml` (receptor webhook; reemplaza por Slack/Email según tu preferencia):

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  group_by: ['alertname', 'job']
  group_wait: 10s
  group_interval: 30s
  repeat_interval: 2h

receivers:
  - name: 'default'
    webhook_configs:
      - url: 'http://example.com/webhook'  # Reemplazar
        send_resolved: true
```

Notas:
- Asegúrate de incluir `rule_files: ['alerts.yml']` en `prometheus.yml` (ya documentado arriba).
- Cambia el receptor por `slack_configs` o `email_configs` según tu canal de notificación.
- Verifica Alertmanager en `http://localhost:9093`.

##### Plantillas de Alertmanager: Slack y Email (con variables de entorno)

Para evitar hardcodear secretos, usa expansión de variables de entorno en `alertmanager.yml` y habilítala con `--config.expand-env`.

```yaml
# alertmanager.yml (con env expansion)
global:
  resolve_timeout: 5m

route:
  receiver: 'slack'            # Slack por defecto
  group_by: ['alertname', 'job']
  group_wait: 10s
  group_interval: 30s
  repeat_interval: 2h
  routes:
    - match:
        severity: critical     # Críticas también por email
      receiver: 'email'
      continue: true

receivers:
  - name: 'slack'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '${SLACK_CHANNEL}'          # Opcional si el webhook fija canal
        text: 'Alerta {{ .CommonLabels.alertname }} ({{ .Status }})\n{{ range .Alerts }}- {{ .Annotations.summary }}{{ end }}'
        send_resolved: true

  - name: 'email'
    email_configs:
      - to: '${SMTP_TO}'
        from: '${SMTP_FROM}'
        smarthost: '${SMTP_SMARTHOST}'       # ej: smtp.example.com:587
        auth_username: '${SMTP_USERNAME}'
        auth_password: '${SMTP_PASSWORD}'
        require_tls: true
        headers:
          subject: '[ALERTA] {{ .CommonLabels.alertname }} ({{ .Status }})'
```

Servicio `alertmanager` con expansión de env y variables:

```yaml
services:
  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    environment:
      - SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
      - SLACK_CHANNEL=${SLACK_CHANNEL}
      - SMTP_SMARTHOST=${SMTP_SMARTHOST}
      - SMTP_USERNAME=${SMTP_USERNAME}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - SMTP_FROM=${SMTP_FROM}
      - SMTP_TO=${SMTP_TO}
    command:
      - --config.file=/etc/alertmanager/alertmanager.yml
      - --config.expand-env=true
    ports:
      - "9093:9093"
```

Sugerencia: define las variables en tu `.env` de Compose o como variables de entorno del sistema.

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

### Pruebas

Para ejecutar las pruebas automatizadas del sistema de memoria:

```bash
python tests/test_memoria_automatico.py
```

#### Merge Protection

Los merges hacia la rama `main` requieren que pase el workflow "CI - Safe Tests" que ejecuta tests en dos grupos seguros para evitar problemas de compatibilidad con librerías nativas. Consulta [README_TESTS.md](README_TESTS.md) para detalles completos sobre la estrategia de testing y cómo ejecutar los tests localmente.

## Documentación

La documentación completa del proyecto se encuentra en el directorio `docs/`:

- **[docs/MEMORIA_SISTEMA_ACTUALIZADO.md](docs/MEMORIA_SISTEMA_ACTUALIZADO.md)** - Sistema de memoria mejorado
- **[docs/GUIA_COMANDOS_MEMORIA.md](docs/GUIA_COMANDOS_MEMORIA.md)** - Guía completa de comandos para administrar memoria durante conversaciones
- **[docs/CONFIGURACION_Y_SOLUCION_PROBLEMAS.md](docs/CONFIGURACION_Y_SOLUCION_PROBLEMAS.md)** - Configuración y solución de problemas

## Configuración

La configuración del sistema se encuentra en el archivo `backend/utils/unified_config.py`. Principales parámetros:

**`LLM_CONFIG`**: Configuración del modelo de lenguaje
- `model_name`: Nombre del archivo del modelo GGUF
- `max_tokens`: Tokens máximos por respuesta (150)
- `temperature`: Creatividad de las respuestas (0.7)
- `n_ctx`: Tamaño del contexto (1024)
- `n_threads`: Hilos de procesamiento (4)
- `response_timeout`: Timeout de respuesta (45s)

**`KB_CONFIG`**: Configuración de la base de conocimiento
- `embedding_model`: Modelo de embeddings (all-MiniLM-L6-v2)
- `index_path`: Ruta del índice FAISS
- `documents_path`: Ruta de documentos JSON

**`MEMORY_CONFIG`**: Configuración de la memoria
- `max_short_term_memory`: Límite memoria corto plazo (50)
- `auto_transition_threshold`: Umbral transición automática (25)
- `auto_save`: Guardado automático (True)
- `backup_frequency`: Frecuencia de respaldos (20)

**`SYSTEM_CONFIG`**: Configuración general del sistema
- `log_level`: Nivel de logging (INFO)
- `api_host`: Host de la API (127.0.0.1)
- `api_port`: Puerto de la API (8000)
- `debug_mode`: Modo debug (True)

## Estructura del Proyecto

```
Assistant/
├── backend/
│   ├── llm/
│   │   ├── model_manager.py    # Gestión del LLM
│   │   ├── memory_manager.py   # Sistema de memoria mejorado
│   │   └── knowledge_base.py   # Base de conocimiento
│   ├── utils/
│   │   └── logger.py           # Sistema de logging
│   └── api.py                  # API REST
├── docs/                       # Documentación del proyecto
│   ├── README.md               # Índice de documentación
│   ├── MEMORIA_SISTEMA_ACTUALIZADO.md  # Sistema de memoria
│   ├── PLAN_PRUEBAS_MEMORIA.md # Plan de pruebas automatizado
│   └── GUIA_PRUEBAS_MANUAL.md  # Guía de pruebas manuales
├── tests/                      # Pruebas del sistema
│   └── test_memoria_automatico.py  # Pruebas automatizadas
├── models/                     # Directorio para modelos
│   ├── knowledge/              # Índices de conocimiento
│   └── memory/                 # Archivos de memoria
├── logs/                       # Directorio para logs
├── backend/utils/unified_config.py  # Configuración del sistema
├── main.py                     # Punto de entrada principal
└── requirements.txt            # Dependencias
```

## Próximos Pasos

La Fase 2 incluirá:
- Integración de sistema de voz (STT/TTS)
- Mejoras en la interfaz de usuario
- Optimizaciones de rendimiento

## Licencia

Este proyecto está licenciado bajo [Licencia MIT](LICENSE).