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

1. **Modelo LLM**: Descargar un modelo GGUF (recomendado Llama-2-7B-Chat cuantizado) y colocarlo en la carpeta `models/`.

2. **Modelo de Embeddings**: El sistema descargará automáticamente el modelo `all-MiniLM-L6-v2` de SentenceTransformers la primera vez que se ejecute.

### Enlaces de descarga recomendados

- [Llama-2-7B-Chat.Q4_K_M.gguf](https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf) (2.9GB)
- [Mistral-7B-Instruct.Q4_K_M.gguf](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/mistral-7b-instruct-v0.1.Q4_K_M.gguf) (3.8GB)

## Uso

### Modo Interactivo

Para iniciar el asistente en modo interactivo:

```bash
python main.py --interactive
```

Comandos especiales en modo interactivo:
- `/salir` - Terminar la sesión
- `/status` - Ver estado del sistema
- `/clear` - Limpiar memoria de conversación completa
- `/clear_short` - Limpiar solo memoria a corto plazo
- `/clear_long` - Limpiar solo memoria a largo plazo
- `/memory_short` - Ver memorias a corto plazo actuales
- `/memory_count` - Ver cantidad de memorias en cada tipo
- `/memory_list` - Listar memorias a largo plazo
- `/memory_delete <índice>` - Eliminar memoria específica
- `/memory_create_group <nombre>` - Crear nuevo grupo de memoria
- `/memory_transition` - Forzar transición de memoria corta a larga
- `/rag on|off` - Activar/desactivar búsqueda en base de conocimiento
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

### Pruebas

Para ejecutar las pruebas automatizadas del sistema de memoria:

```bash
python tests/test_memoria_automatico.py
```

Para pruebas manuales paso a paso, consulta la documentación en:
- `docs/PLAN_PRUEBAS_MEMORIA.md` - Plan completo de pruebas
- `docs/GUIA_PRUEBAS_MANUAL.md` - Guía de pruebas manuales

## Documentación

La documentación completa del proyecto se encuentra en el directorio `docs/`:

- **[docs/README.md](docs/README.md)** - Índice de toda la documentación
- **[docs/MEMORIA_SISTEMA_ACTUALIZADO.md](docs/MEMORIA_SISTEMA_ACTUALIZADO.md)** - Sistema de memoria mejorado
- **[docs/PLAN_PRUEBAS_MEMORIA.md](docs/PLAN_PRUEBAS_MEMORIA.md)** - Plan de pruebas automatizado
- **[docs/GUIA_PRUEBAS_MANUAL.md](docs/GUIA_PRUEBAS_MANUAL.md)** - Guía de pruebas manuales
- **[docs/GUIA_COMANDOS_MEMORIA.md](docs/GUIA_COMANDOS_MEMORIA.md)** - Guía completa de comandos para administrar memoria durante conversaciones
- **[CONTEXT.md](CONTEXT.md)** - Contexto técnico completo del proyecto

## Configuración

La configuración del sistema se encuentra en el archivo `config.py`. Principales parámetros:

- `LLM_CONFIG`: Configuración del modelo de lenguaje (nombre, tokens máximos, temperatura, etc.)
- `KB_CONFIG`: Configuración de la base de conocimiento (modelo de embeddings, rutas de archivos)
- `MEMORY_CONFIG`: Configuración de la memoria mejorada (archivo, límites, transición automática)
- `SYSTEM_CONFIG`: Configuración general del sistema (nivel de log, host/puerto API, etc.)

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
├── config.py                   # Configuración del sistema
├── main.py                     # Punto de entrada principal
├── CONTEXT.md                  # Contexto del proyecto
└── requirements.txt            # Dependencias
```

## Próximos Pasos

La Fase 2 incluirá:
- Integración de sistema de voz (STT/TTS)
- Mejoras en la interfaz de usuario
- Optimizaciones de rendimiento

## Licencia

Este proyecto está licenciado bajo [Licencia MIT](LICENSE).