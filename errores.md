(.venv) santi@santi-desktop:~/LeonelResponde$ python Assistant/main.py
08:42:08.414 | 📝 INFO | CONFIG | PyTorch not available, using CPU-only mode
08:42:08.431 | ⚠️ WARNING | CONFIG | MCP config file not found: /home/santi/LeonelResponde/Assistant/mcp_config.json
08:42:08.433 | 📝 INFO | CONFIG | 🔧 Unified configuration initialized
08:42:08.433 | 📝 INFO | CONFIG | 📁 Models directory: /home/santi/LeonelResponde/Assistant/data/models
08:42:08.433 | 📝 INFO | CONFIG | 📁 Logs directory: /home/santi/LeonelResponde/Assistant/logs
08:42:08.433 | 📝 INFO | CONFIG | 🧠 Device: auto
08:42:08.433 | 📝 INFO | CONFIG | 🤖 Model: mistral-7b-instruct-v0.1.Q4_K_M.gguf
08:42:08.434 | 📝 INFO | CONFIG | 📚 Embedding model: all-MiniLM-L6-v2
08:42:08.434 | 📝 INFO | CONFIG | 💻 Using CPU (normal on Intel/CPU systems)
08:42:08.435 | 📝 INFO | MAIN | 🔧 Configurando entorno del sistema...
08:42:08.436 | 📝 INFO | MAIN | 📁 Directorio de trabajo: /home/santi/LeonelResponde/Assistant
08:42:08.436 | 📝 INFO | MAIN | 🗂️ Directorio temporal: /tmp
08:42:08.436 | 📝 INFO | MAIN | 🧠 Modelo LLM configurado: mistral-7b-instruct-v0.1.Q4_K_M.gguf
08:42:08.436 | 📝 INFO | MAIN | 💻 Dispositivo de procesamiento: auto
08:42:08.436 | 📝 INFO | MAIN | 📊 Trazado de rendimiento habilitado: /home/santi/LeonelResponde/Assistant/logs/trace_data.jsonl
🤖 ASISTENTE MULTIMODAL OFFLINE - FASE 1
==================================================
Motor de IA local con memoria persistente y base de conocimiento
==================================================
08:42:08.446 | 📝 INFO | MAIN | 📊 Inicializando sistema de métricas...
08:42:08.485 | 📝 INFO | METRICS | 📊 Metrics Collector inicializado (interval: 10.0s)
08:42:08.489 | 📝 INFO | MAIN | 📊 Recolectando métricas iniciales del sistema...
08:42:08.590 | ⚠️ WARNING | METRICS | ⚠️ Métrica 'system.load_avg_1m' no registrada, creando automáticamente
08:42:08.591 | ⚠️ WARNING | METRICS | ⚠️ Métrica 'system.load_avg_5m' no registrada, creando automáticamente
08:42:08.591 | ⚠️ WARNING | METRICS | ⚠️ Métrica 'system.load_avg_15m' no registrada, creando automáticamente
08:42:08.592 | 📝 INFO | MAIN | 📊 Métricas iniciales - CPU: 6.6%, Memoria: 47.9%
08:42:08.592 | 📝 INFO | MAIN | ✅ Metrics Collector inicializado (interval: 10.0s)
08:42:08.592 | 📝 INFO | MAIN | 🚀 Inicializando sistema optimizado...
⚠️ PyTorch no disponible, saltando optimizaciones específicas
⚠️ PyTorch no disponible, saltando optimizaciones específicas
⚠️ Monitoreo de rendimiento ya está activo
08:42:08.710 | 📝 INFO | MAIN | ✅ Sistema optimizado inicializado en 0.00s
08:42:08.711 | 📝 INFO | MAIN | 📊 Optimizaciones aplicadas: 12
08:42:08.711 | 📝 INFO | MAIN | 🛡️ Inicializando sistema de protección...
08:42:08.722 | 📝 INFO | MAIN | ✅ Sistema de protección contra kernel panics activado
08:42:08.723 | 📝 INFO | MAIN | 🔍 Validando configuración del sistema...
08:42:08.731 | 📝 INFO | MAIN | ✅ Configuración del sistema validada correctamente
08:42:08.731 | 📝 INFO | MAIN | 🧩 Inicializando componentes del sistema...
08:42:08.768 | 📝 INFO | LLM | 🧠 Inicializando LLMManager con modelo: /home/santi/LeonelResponde/Assistant/data/models/mistral-7b-instruct-v0.1.Q4_K_M.gguf
08:42:08.769 | 📝 INFO | MODEL_VERSIONING | ✅ Cargadas 1 versiones desde /home/santi/LeonelResponde/Assistant/src/models/versions/model_versions.json
08:42:08.769 | 📝 INFO | MODEL_VERSIONING | 📚 Model Version Manager inicializado (archivo: /home/santi/LeonelResponde/Assistant/src/models/versions/model_versions.json)
08:42:08.769 | 📝 INFO | LLM | 📚 Model Version Manager integrado
08:42:08.770 | 📝 INFO | MemoryLimiter | 🔧 MemoryLimiter initialized with 2048MB limit
08:42:08.770 | 📝 INFO | MemoryLimiter | 📦 Cache registered: llm_model
08:42:08.770 | 📝 INFO | MemoryLimiter | 📦 Cache registered: conversation_history
08:42:08.770 | 📝 INFO | MemoryLimiter | 📝 Cleanup callback registered: llm_manager
08:42:08.771 | 📝 INFO | LLM | 🔗 LLMManager registrado con MemoryLimiter
08:42:08.918 | 📝 INFO | MemoryLimiter | 📦 Cache registered: embedding_model
08:42:08.919 | 📝 INFO | MemoryLimiter | 📦 Cache registered: faiss_index
08:42:08.919 | 📝 INFO | MemoryLimiter | 📦 Cache registered: documents
08:42:08.919 | 📝 INFO | MemoryLimiter | 📦 Cache registered: embedding_cache
08:42:08.920 | 📝 INFO | MemoryLimiter | 📝 Cleanup callback registered: knowledge_base
08:42:08.920 | 📝 INFO | Knowledge | 🧠 Inicializando KnowledgeBase con modelo all-MiniLM-L6-v2
08:42:08.920 | 📝 INFO | Knowledge | 📥 Cargando modelo de embeddings all-MiniLM-L6-v2...
08:42:08.921 | ❌ ERROR | Knowledge | ❌ Error cargando modelo de embeddings: No module named 'sentence_transformers'
08:42:08.989 | 📝 INFO | BackupManager | 💾 BackupManager inicializado en /home/santi/LeonelResponde/Assistant/data/models/backups
08:42:08.990 | 📝 INFO | BackupManager | 🧠 Configurado respaldo de memoria desde /home/santi/LeonelResponde/Assistant/data/models/memory
08:42:08.991 | 📝 INFO | BackupManager | 📚 Configurado respaldo de Knowledge Base desde /home/santi/LeonelResponde/Assistant/data/models/knowledge
08:42:08.991 | 📝 INFO | BackupManager | 🔄 Sistema de respaldos automáticos iniciado (cada 24h)
08:42:08.992 | 📝 INFO | BackupManager | 🔄 Iniciando respaldo: backup_20251101_084208
08:42:08.995 | 📝 INFO | MAIN | ✅ Todos los componentes del sistema inicializados
08:42:08.995 | 📝 INFO | MAIN | 🛡️ Inicializando graceful shutdown...
08:42:08.996 | 📝 INFO | BackupManager | 💾 Respaldo completado: /home/santi/LeonelResponde/Assistant/data/models/backups/backup_20251101_084208.zip
08:42:09.005 | 📝 INFO | SHUTDOWN | 🛡️ Graceful Shutdown Manager inicializado (timeout: 30.0s, force: 5.0s)
08:42:09.006 | 📝 INFO | SHUTDOWN | ✅ Callback registrado: cleanup_llm_manager (priority: 5, timeout: 5.0s, critical: True)
08:42:09.007 | 📝 INFO | SHUTDOWN | ✅ Callback registrado: cleanup_knowledge_base (priority: 4, timeout: 2.0s, critical: False)
08:42:09.007 | 📝 INFO | SHUTDOWN | ✅ Callback registrado: finalize_metrics_report (priority: 2, timeout: 4.0s, critical: False)
08:42:09.007 | 📝 INFO | SHUTDOWN | ✅ Callback registrado: finalize_shutdown (priority: 1, timeout: 1.0s, critical: False)
08:42:09.008 | 📝 INFO | SHUTDOWN | ✅ Manejadores de señales configurados (SIGINT, SIGTERM)
08:42:09.008 | 📝 INFO | MAIN | ✅ Graceful Shutdown Manager inicializado
08:42:09.008 | 📝 INFO | MAIN | ⏱️ Timeouts: graceful=30.0s, force=5.0s
08:42:09.008 | 📝 INFO | MAIN | 🏥 Inicializando health checker...
08:42:09.018 | 📝 INFO | HEALTH | 🏥 Health Checker inicializado
08:42:09.019 | 📝 INFO | HEALTH | 📊 Umbrales de alerta: {'cpu_percent': 90.0, 'memory_percent': 85.0, 'disk_percent': 90.0, 'response_time': 5.0}
08:42:09.019 | 📝 INFO | MAIN | 🏥 Ejecutando health check inicial del sistema...
08:42:09.121 | 📝 INFO | HEALTH | ❌ Health Check: UNHEALTHY (8 components checked)
08:42:09.121 | ❌ ERROR | HEALTH |   ❌ Memory Manager not initialized
08:42:09.122 | ⚠️ WARNING | HEALTH |   ⚠️ LLM not loaded (lazy loading enabled)
08:42:09.122 | 📝 INFO | HEALTH |   📊 Resources: CPU 18.3%, Memory 47.9%, Disk 25.2%
08:42:09.122 | 📝 INFO | MAIN | 🏥 Health Checker inicializado - Estado: unhealthy
08:42:09.223 | 📝 INFO | MAIN | 📊 Métricas post-inicialización recolectadas
08:42:09.224 | 📝 INFO | MAIN | 💬 Iniciando modo interactivo con UI: console...
⚠️ Carpeta de conocimiento no encontrada: data/knowledge

🤖 Asistente Personal Leonel - Modo Interactivo
==================================================
📋 Comandos disponibles:
  /help - Mostrar ayuda completa
  /status - Ver estado del sistema
  /mic on|off - Activar/desactivar micrófono
  /tts on|off - Activar/desactivar síntesis de voz
  /salir - Terminar sesión
==================================================
💬 Escribe tu mensaje o usa un comando:

👤 Tú: ✅ ¡Listo para chatear!

👤 Tú: Hola
08:42:13.965 | ❌ ERROR | LLM | ❌ Modelo no encontrado en: /home/santi/LeonelResponde/Assistant/data/models/mistral-7b-instruct-v0.1.Q4_K_M.gguf
08:42:13.967 | ❌ ERROR | ErrorHandler | [MEDIUM] system: ErrorContext.__init__() got an unexpected keyword argument 'severity'
08:42:13.968 | ❌ ERROR | AdaptiveInteractiveMode | ❌ Operation failed with exception: llm_generation
08:42:13.999 | ❌ ERROR | AdaptiveInteractiveMode | 💥 Operation failed: llm_generation

❌ Error en interfaz de consola: ErrorContext.__init__() got an unexpected keyword argument 'severity'

🧹 Limpiando interfaz de consola...
08:42:14.103 | 📝 INFO | HEALTH | ❌ Health Check: UNHEALTHY (8 components checked)
08:42:14.104 | ❌ ERROR | HEALTH |   ❌ Memory Manager not initialized
08:42:14.104 | ⚠️ WARNING | HEALTH |   ⚠️ LLM not loaded (lazy loading enabled)
08:42:14.105 | 📝 INFO | HEALTH |   📊 Resources: CPU 15.0%, Memory 48.1%, Disk 25.2%
08:42:24.140 | ❌ ERROR | Knowledge | ❌ Error guardando índice y documentos: No module named 'faiss'


