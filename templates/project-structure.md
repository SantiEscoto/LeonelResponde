# 🏗️ Estructura del Proyecto

## 📁 Estructura Recomendada

```
asistente-ia-universal/
├── 📄 README.md                    # Resumen ejecutivo
├── 📄 CONTEXT.md                   # Contexto del proyecto
├── 📄 .gitignore                   # Archivos a ignorar
├── 📄 .env.example                 # Variables de entorno ejemplo
├── 📄 docker-compose.yml           # Docker Compose
├── 📄 docker-compose.prod.yml      # Docker Compose producción
├── 📄 Dockerfile                   # Docker para desarrollo
├── 📄 Dockerfile.prod              # Docker para producción
├── 📄 pyproject.toml               # Configuración Python
├── 📄 package.json                 # Configuración Node.js
├── 📄 tsconfig.json                # Configuración TypeScript
├── 📄 tailwind.config.js          # Configuración Tailwind
├── 📄 vite.config.ts               # Configuración Vite
├── 📄 playwright.config.ts         # Configuración Playwright
├── 📄 jest.config.js               # Configuración Jest
├── 📄 pytest.ini                  # Configuración pytest
├── 📄 mypy.ini                    # Configuración mypy
├── 📄 ruff.toml                   # Configuración ruff
├── 📄 .pre-commit-config.yaml      # Configuración pre-commit
├── 📄 .github/                     # GitHub Actions
│   ├── 📄 workflows/
│   │   ├── 📄 test.yml
│   │   ├── 📄 build.yml
│   │   └── 📄 deploy.yml
│   └── 📄 ISSUE_TEMPLATE/
│       ├── 📄 bug_report.md
│       └── 📄 feature_request.md
├── 📁 docs/                       # Documentación por fases
│   ├── 📄 01-planificacion.md      # Fase 1: Planificación
│   ├── 📄 02-backend-llm.md        # Fase 2: Backend LLM
│   ├── 📄 03-conocimiento-rag.md   # Fase 3: Base de Conocimiento
│   ├── 📄 04-finetuning.md         # Fase 4: Fine-tuning
│   ├── 📄 05-frontend-ui.md        # Fase 5: Frontend UI
│   ├── 📄 06-voz-audio.md          # Fase 6: Sistema de Voz
│   ├── 📄 07-vision.md             # Fase 7: Sistema de Visión
│   ├── 📄 08-integracion.md        # Fase 8: Integración
│   ├── 📄 09-optimizacion.md       # Fase 9: Optimización
│   └── 📄 10-mantenimiento.md      # Fase 10: Mantenimiento
├── 📁 templates/                  # Templates reutilizables
│   ├── 📄 checklist.md             # Checklist por fase
│   ├── 📄 quick-reference.md      # Comandos esenciales
│   └── 📄 project-structure.md   # Esta estructura
├── 📁 scripts/                    # Scripts de automatización
│   ├── 📄 setup-windows.ps1        # Setup Windows
│   ├── 📄 setup-linux.sh           # Setup Linux
│   ├── 📄 setup-macos.sh           # Setup macOS
│   ├── 📄 build.sh                 # Build del proyecto
│   ├── 📄 deploy.sh                # Deploy del proyecto
│   ├── 📄 test.sh                  # Testing completo
│   └── 📄 cleanup.sh                # Limpieza del proyecto
├── 📁 config/                     # Configuraciones
│   ├── 📄 development.yaml         # Configuración desarrollo
│   ├── 📄 production.yaml          # Configuración producción
│   ├── 📄 staging.yaml             # Configuración staging
│   └── 📁 hardware/                # Configuraciones por hardware
│       ├── 📄 jetson-nano.yaml     # Jetson Nano
│       ├── 📄 raspberry-pi.yaml   # Raspberry Pi
│       ├── 📄 desktop.yaml         # Desktop
│       └── 📄 laptop.yaml          # Laptop
├── 📁 backend/                     # Backend Python
│   ├── 📄 requirements.txt         # Dependencias Python
│   ├── 📄 requirements-dev.txt     # Dependencias desarrollo
│   ├── 📄 requirements-finetuning.txt # Dependencias fine-tuning
│   ├── 📄 requirements-optional.txt # Dependencias opcionales
│   ├── 📄 pyproject.toml           # Configuración Poetry
│   ├── 📄 poetry.lock              # Lock file Poetry
│   ├── 📄 setup.py                 # Setup del paquete
│   ├── 📄 MANIFEST.in              # Archivos a incluir
│   ├── 📄 .env                     # Variables de entorno
│   ├── 📄 .env.example             # Variables de entorno ejemplo
│   ├── 📄 Dockerfile               # Docker para backend
│   ├── 📄 docker-compose.yml       # Docker Compose backend
│   ├── 📄 alembic.ini             # Configuración Alembic
│   ├── 📄 pytest.ini              # Configuración pytest
│   ├── 📄 mypy.ini                # Configuración mypy
│   ├── 📄 ruff.toml               # Configuración ruff
│   ├── 📄 .pre-commit-config.yaml  # Configuración pre-commit
│   ├── 📁 app/                    # Aplicación principal
│   │   ├── 📄 __init__.py
│   │   ├── 📄 main.py              # Punto de entrada
│   │   ├── 📄 config.py           # Configuración
│   │   ├── 📄 database.py         # Base de datos
│   │   ├── 📄 auth.py              # Autenticación
│   │   ├── 📄 middleware.py        # Middleware
│   │   ├── 📄 exceptions.py        # Excepciones
│   │   ├── 📁 api/                 # API REST
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 chat.py          # Endpoints de chat
│   │   │   ├── 📄 users.py         # Endpoints de usuarios
│   │   │   ├── 📄 memory.py        # Endpoints de memoria
│   │   │   ├── 📄 finetuning.py    # Endpoints de fine-tuning
│   │   │   ├── 📄 voice.py         # Endpoints de voz
│   │   │   ├── 📄 vision.py        # Endpoints de visión
│   │   │   └── 📄 health.py        # Health check
│   │   ├── 📁 core/                # Core del sistema
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 config.py        # Configuración
│   │   │   ├── 📄 database.py      # Base de datos
│   │   │   ├── 📄 auth.py          # Autenticación
│   │   │   ├── 📄 security.py       # Seguridad
│   │   │   ├── 📄 hardware_detector.py # Detector de hardware
│   │   │   ├── 📄 resource_monitor.py # Monitor de recursos
│   │   │   ├── 📄 lora_finetuning.py # Fine-tuning LoRA
│   │   │   ├── 📄 qlora_finetuning.py # Fine-tuning QLoRA
│   │   │   ├── 📄 finetuning_tools.py # Herramientas fine-tuning
│   │   │   └── 📄 agentic_foundation.py # Fundación agéntica
│   │   ├── 📁 services/             # Servicios
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 chat_service.py  # Servicio de chat
│   │   │   ├── 📄 memory_service.py # Servicio de memoria
│   │   │   ├── 📄 user_service.py  # Servicio de usuarios
│   │   │   ├── 📄 finetuning_service.py # Servicio fine-tuning
│   │   │   ├── 📄 voice_service.py # Servicio de voz
│   │   │   ├── 📄 vision_service.py # Servicio de visión
│   │   │   └── 📄 notification_service.py # Servicio notificaciones
│   │   ├── 📁 models/               # Modelos de datos
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 user.py          # Modelo de usuario
│   │   │   ├── 📄 chat.py           # Modelo de chat
│   │   │   ├── 📄 memory.py        # Modelo de memoria
│   │   │   ├── 📄 finetuning.py     # Modelo de fine-tuning
│   │   │   └── 📄 base.py           # Modelo base
│   │   ├── 📁 schemas/              # Esquemas Pydantic
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 user.py          # Esquema de usuario
│   │   │   ├── 📄 chat.py           # Esquema de chat
│   │   │   ├── 📄 memory.py        # Esquema de memoria
│   │   │   ├── 📄 finetuning.py     # Esquema de fine-tuning
│   │   │   └── 📄 base.py           # Esquema base
│   │   ├── 📁 utils/                # Utilidades
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 logger.py         # Logger
│   │   │   ├── 📄 validators.py     # Validadores
│   │   │   ├── 📄 helpers.py        # Helpers
│   │   │   ├── 📄 decorators.py     # Decoradores
│   │   │   ├── 📄 resource_monitor.py # Monitor de recursos
│   │   │   └── 📄 performance.py    # Performance
│   │   └── 📁 data/                  # Datos
│   │       ├── 📄 __init__.py
│   │       ├── 📄 identity_data.py  # Datos de identidad
│   │       ├── 📄 knowledge_data.py # Datos de conocimiento
│   │       └── 📄 training_data.py  # Datos de entrenamiento
│   ├── 📁 tests/                    # Tests
│   │   ├── 📄 __init__.py
│   │   ├── 📄 conftest.py          # Configuración pytest
│   │   ├── 📁 unit/                 # Tests unitarios
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 test_chat.py
│   │   │   ├── 📄 test_memory.py
│   │   │   ├── 📄 test_finetuning.py
│   │   │   └── 📄 test_utils.py
│   │   ├── 📁 integration/          # Tests de integración
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 test_api.py
│   │   │   ├── 📄 test_database.py
│   │   │   └── 📄 test_services.py
│   │   ├── 📁 performance/          # Tests de rendimiento
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 test_benchmark.py
│   │   │   └── 📄 test_load.py
│   │   └── 📁 fixtures/             # Fixtures
│   │       ├── 📄 __init__.py
│   │       ├── 📄 user_fixtures.py
│   │       └── 📄 chat_fixtures.py
│   ├── 📁 migrations/               # Migraciones Alembic
│   │   ├── 📄 env.py
│   │   ├── 📄 script.py.mako
│   │   └── 📁 versions/
│   │       ├── 📄 001_initial.py
│   │       └── 📄 002_add_memory.py
│   └── 📁 logs/                     # Logs
│       ├── 📄 backend.log
│       ├── 📄 error.log
│       └── 📄 access.log
├── 📁 frontend/                     # Frontend React
│   ├── 📄 package.json              # Dependencias Node.js
│   ├── 📄 package-lock.json        # Lock file
│   ├── 📄 tsconfig.json             # Configuración TypeScript
│   ├── 📄 tailwind.config.js        # Configuración Tailwind
│   ├── 📄 vite.config.ts            # Configuración Vite
│   ├── 📄 playwright.config.ts      # Configuración Playwright
│   ├── 📄 jest.config.js            # Configuración Jest
│   ├── 📄 .eslintrc.js              # Configuración ESLint
│   ├── 📄 .prettierrc               # Configuración Prettier
│   ├── 📄 .env                      # Variables de entorno
│   ├── 📄 .env.example              # Variables de entorno ejemplo
│   ├── 📄 Dockerfile               # Docker para frontend
│   ├── 📄 docker-compose.yml       # Docker Compose frontend
│   ├── 📁 public/                   # Archivos públicos
│   │   ├── 📄 index.html
│   │   ├── 📄 favicon.ico
│   │   ├── 📄 manifest.json
│   │   └── 📁 assets/
│   │       ├── 📁 images/
│   │       ├── 📁 icons/
│   │       └── 📁 fonts/
│   ├── 📁 src/                      # Código fuente
│   │   ├── 📄 main.tsx              # Punto de entrada
│   │   ├── 📄 App.tsx               # Componente principal
│   │   ├── 📄 index.css             # Estilos globales
│   │   ├── 📄 vite-env.d.ts         # Tipos de Vite
│   │   ├── 📁 components/           # Componentes
│   │   │   ├── 📄 ChatInterface.tsx # Interfaz de chat
│   │   │   ├── 📄 MessageBubble.tsx  # Burbuja de mensaje
│   │   │   ├── 📄 InputField.tsx    # Campo de entrada
│   │   │   ├── 📄 StatusIndicator.tsx # Indicador de estado
│   │   │   ├── 📄 VoiceInterface.tsx # Interfaz de voz
│   │   │   ├── 📄 VisionInterface.tsx # Interfaz de visión
│   │   │   ├── 📄 DeveloperPersonalization.tsx # Personalización
│   │   │   ├── 📄 AttentionIndicator.tsx # Indicador de atención
│   │   │   ├── 📄 SocialStatus.tsx  # Estado social
│   │   │   └── 📄 UserProfile.tsx   # Perfil de usuario
│   │   ├── 📁 pages/                # Páginas
│   │   │   ├── 📄 ChatPage.tsx      # Página de chat
│   │   │   ├── 📄 SettingsPage.tsx  # Página de configuración
│   │   │   ├── 📄 DeveloperPage.tsx  # Página de desarrollador
│   │   │   └── 📄 ProfilePage.tsx    # Página de perfil
│   │   ├── 📁 hooks/                # Hooks personalizados
│   │   │   ├── 📄 useChat.ts        # Hook de chat
│   │   │   ├── 📄 useMemory.ts      # Hook de memoria
│   │   │   ├── 📄 useVoice.ts       # Hook de voz
│   │   │   ├── 📄 useVision.ts      # Hook de visión
│   │   │   └── 📄 useFinetuning.ts  # Hook de fine-tuning
│   │   ├── 📁 services/             # Servicios
│   │   │   ├── 📄 api.ts            # Cliente API
│   │   │   ├── 📄 websocket.ts      # WebSocket
│   │   │   ├── 📄 storage.ts        # Almacenamiento
│   │   │   └── 📄 notification.ts  # Notificaciones
│   │   ├── 📁 store/                # Estado global
│   │   │   ├── 📄 index.ts         # Store principal
│   │   │   ├── 📄 chatStore.ts      # Store de chat
│   │   │   ├── 📄 userStore.ts      # Store de usuario
│   │   │   ├── 📄 memoryStore.ts    # Store de memoria
│   │   │   └── 📄 finetuningStore.ts # Store de fine-tuning
│   │   ├── 📁 types/                # Tipos TypeScript
│   │   │   ├── 📄 index.ts         # Tipos principales
│   │   │   ├── 📄 chat.ts          # Tipos de chat
│   │   │   ├── 📄 user.ts          # Tipos de usuario
│   │   │   ├── 📄 memory.ts        # Tipos de memoria
│   │   │   └── 📄 finetuning.ts    # Tipos de fine-tuning
│   │   ├── 📁 utils/                # Utilidades
│   │   │   ├── 📄 constants.ts     # Constantes
│   │   │   ├── 📄 helpers.ts       # Helpers
│   │   │   ├── 📄 validators.ts    # Validadores
│   │   │   └── 📄 formatters.ts    # Formateadores
│   │   └── 📁 styles/               # Estilos
│   │       ├── 📄 globals.css       # Estilos globales
│   │       ├── 📄 components.css   # Estilos de componentes
│   │       └── 📄 utilities.css    # Utilidades CSS
│   ├── 📁 tests/                    # Tests
│   │   ├── 📄 setup.ts             # Configuración tests
│   │   ├── 📁 unit/                 # Tests unitarios
│   │   │   ├── 📄 ChatInterface.test.tsx
│   │   │   ├── 📄 MessageBubble.test.tsx
│   │   │   └── 📄 InputField.test.tsx
│   │   ├── 📁 integration/          # Tests de integración
│   │   │   ├── 📄 chat.test.tsx
│   │   │   └── 📄 api.test.tsx
│   │   ├── 📁 e2e/                  # Tests end-to-end
│   │   │   ├── 📄 chat.spec.ts
│   │   │   └── 📄 user.spec.ts
│   │   └── 📁 fixtures/             # Fixtures
│   │       ├── 📄 userFixtures.ts
│   │       └── 📄 chatFixtures.ts
│   └── 📁 logs/                     # Logs
│       ├── 📄 frontend.log
│       └── 📄 error.log
├── 📁 ai/                          # IA y ML
│   ├── 📄 requirements.txt         # Dependencias AI
│   ├── 📄 Dockerfile               # Docker para AI
│   ├── 📄 docker-compose.yml       # Docker Compose AI
│   ├── 📁 llm/                     # Modelos de lenguaje
│   │   ├── 📄 __init__.py
│   │   ├── 📄 ollama_service.py    # Servicio Ollama
│   │   ├── 📄 langchain_service.py  # Servicio LangChain
│   │   ├── 📄 model_manager.py     # Gestor de modelos
│   │   └── 📄 quantization.py      # Cuantización
│   ├── 📁 memory/                  # Sistema de memoria
│   │   ├── 📄 __init__.py
│   │   ├── 📄 user_memory.py        # Memoria por usuario
│   │   ├── 📄 social_memory.py     # Memoria social
│   │   ├── 📄 attention_manager.py # Gestor de atención
│   │   └── 📄 relationship_manager.py # Gestor de relaciones
│   ├── 📁 knowledge/               # Base de conocimiento
│   │   ├── 📄 __init__.py
│   │   ├── 📄 rag_service.py       # Servicio RAG
│   │   ├── 📄 embeddings.py         # Embeddings
│   │   ├── 📄 vector_db.py         # Base de datos vectorial
│   │   └── 📄 document_processor.py # Procesador de documentos
│   ├── 📁 voice/                   # Sistema de voz
│   │   ├── 📄 __init__.py
│   │   ├── 📄 stt_service.py       # Speech-to-Text
│   │   ├── 📄 tts_service.py       # Text-to-Speech
│   │   ├── 📄 audio_processor.py   # Procesador de audio
│   │   └── 📄 voice_recognition.py # Reconocimiento de voz
│   ├── 📁 vision/                  # Sistema de visión
│   │   ├── 📄 __init__.py
│   │   ├── 📄 yolo_service.py      # YOLO
│   │   ├── 📄 ocr_service.py       # OCR
│   │   ├── 📄 face_recognition.py # Reconocimiento facial
│   │   └── 📄 image_processor.py   # Procesador de imágenes
│   ├── 📁 finetuning/              # Fine-tuning
│   │   ├── 📄 __init__.py
│   │   ├── 📄 lora_trainer.py      # Entrenador LoRA
│   │   ├── 📄 qlora_trainer.py     # Entrenador QLoRA
│   │   ├── 📄 data_preparation.py  # Preparación de datos
│   │   └── 📄 model_evaluation.py  # Evaluación de modelos
│   ├── 📁 models/                   # Modelos entrenados
│   │   ├── 📄 __init__.py
│   │   ├── 📁 personalized/         # Modelos personalizados
│   │   │   ├── 📄 user_1/
│   │   │   ├── 📄 user_2/
│   │   │   └── 📄 user_3/
│   │   └── 📁 base/                 # Modelos base
│   │       ├── 📄 mistral_7b/
│   │       └── 📄 phi3_medium/
│   ├── 📁 data/                     # Datos
│   │   ├── 📄 __init__.py
│   │   ├── 📁 training/             # Datos de entrenamiento
│   │   │   ├── 📄 identity/
│   │   │   ├── 📄 knowledge/
│   │   │   └── 📄 conversations/
│   │   ├── 📁 knowledge/             # Base de conocimiento
│   │   │   ├── 📄 documents/
│   │   │   ├── 📄 processed/
│   │   │   └── 📄 vectors/
│   │   └── 📁 memory/               # Memorias
│   │       ├── 📄 users/
│   │       └── 📄 relationships/
│   └── 📁 tests/                    # Tests
│       ├── 📄 __init__.py
│       ├── 📁 unit/                 # Tests unitarios
│       │   ├── 📄 test_llm.py
│       │   ├── 📄 test_memory.py
│       │   └── 📄 test_finetuning.py
│       └── 📁 integration/          # Tests de integración
│           ├── 📄 test_rag.py
│           └── 📄 test_voice.py
├── 📁 logs/                        # Logs del sistema
│   ├── 📄 system.log               # Logs del sistema
│   ├── 📄 error.log                # Logs de errores
│   ├── 📄 access.log               # Logs de acceso
│   ├── 📄 performance.log           # Logs de rendimiento
│   └── 📄 finetuning.log           # Logs de fine-tuning
├── 📁 data/                        # Datos del sistema
│   ├── 📁 users/                   # Datos de usuarios
│   ├── 📁 conversations/           # Conversaciones
│   ├── 📁 memories/                # Memorias
│   └── 📁 models/                  # Modelos
├── 📁 backups/                     # Backups
│   ├── 📁 daily/                   # Backups diarios
│   ├── 📁 weekly/                  # Backups semanales
│   └── 📁 monthly/                 # Backups mensuales
└── 📁 monitoring/                  # Monitoreo
    ├── 📄 metrics.json             # Métricas
    ├── 📄 alerts.json              # Alertas
    └── 📄 dashboards/              # Dashboards
        ├── 📄 system.json
        └── 📄 performance.json
```

## 🎯 Convenciones de Nomenclatura

### **Archivos y Directorios**
- **Python**: `snake_case` (ej: `chat_service.py`)
- **TypeScript**: `camelCase` (ej: `chatService.ts`)
- **Componentes React**: `PascalCase` (ej: `ChatInterface.tsx`)
- **Archivos de configuración**: `kebab-case` (ej: `docker-compose.yml`)

### **Variables y Funciones**
- **Python**: `snake_case` (ej: `user_id`, `get_memory`)
- **TypeScript**: `camelCase` (ej: `userId`, `getMemory`)
- **Constantes**: `UPPER_SNAKE_CASE` (ej: `MAX_USERS`, `API_URL`)

### **Clases y Interfaces**
- **Python**: `PascalCase` (ej: `ChatService`, `UserModel`)
- **TypeScript**: `PascalCase` (ej: `ChatService`, `UserModel`)

## 🔧 Configuración de Herramientas

### **Python**
- **Formateo**: `black`, `ruff`
- **Linting**: `flake8`, `pylint`
- **Type checking**: `mypy`
- **Testing**: `pytest`
- **Dependency management**: `poetry`

### **TypeScript/React**
- **Formateo**: `prettier`
- **Linting**: `eslint`
- **Type checking**: `typescript`
- **Testing**: `jest`, `playwright`
- **Bundling**: `vite`

### **Docker**
- **Multi-stage builds** para optimización
- **Health checks** para monitoreo
- **Volumes** para persistencia
- **Networks** para comunicación

## 📊 Métricas de Calidad

### **Cobertura de Código**
- **Backend**: > 90%
- **Frontend**: > 85%
- **AI/ML**: > 80%

### **Performance**
- **Tiempo de respuesta**: < 2s
- **Memoria**: < 512MB
- **CPU**: < 25%
- **Bundle size**: < 1MB

### **Seguridad**
- **Vulnerabilidades**: 0 críticas
- **Dependencies**: Actualizadas
- **Secrets**: No en código
- **HTTPS**: Obligatorio

---

**🎉 ¡Con esta estructura tendrás un proyecto bien organizado y escalable!**

*Recuerda: La estructura es la base de un proyecto exitoso. Manténla organizada y documentada.* 🚀
