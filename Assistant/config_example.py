# Archivo de configuración de ejemplo para Leonel Responde
# Copia este archivo como config.py y ajusta los valores según tus necesidades

from pathlib import Path

# Directorio base del proyecto
BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"

# Configuración del modelo LLM
LLM_CONFIG = {
    # Modelo principal (debe estar en models/llm/)
    "model_path": str(MODELS_DIR / "llm" / "llama-2-7b-chat.Q4_K_M.gguf"),
    
    # Parámetros de contexto y rendimiento
    "n_ctx": 4096,          # Tamaño del contexto (tokens)
    "n_threads": 4,         # Hilos de CPU (ajustar según tu hardware)
    "n_gpu_layers": 0,      # Capas en GPU (0 = solo CPU, >0 para GPU)
    
    # Parámetros de generación
    "max_tokens": 512,      # Máximo tokens por respuesta
    "temperature": 0.7,     # Creatividad (0.1-1.0)
    "top_p": 0.9,          # Diversidad de tokens
    "top_k": 40,           # Limitación de vocabulario
    
    # Configuración de idioma
    "force_spanish": True,  # Forzar respuestas en español
    "assistant_name": "Leonel",  # Nombre del asistente
}

# Configuración de la memoria
MEMORY_CONFIG = {
    # Archivos de persistencia
    "memory_file": str(MODELS_DIR / "memory" / "conversation_history.json"),
    "memory_groups_file": str(MODELS_DIR / "memory" / "memory_groups.json"),
    "memory_backup_dir": str(MODELS_DIR / "memory" / "backups"),
    
    # Límites de memoria
    "max_short_term_memory": 50,     # Interacciones en memoria corta
    "auto_transition_threshold": 25,  # Umbral para transición automática
    "summary_interval": 8,           # Frecuencia de resúmenes
    
    # Configuración de persistencia
    "auto_save": True,              # Guardar automáticamente
    "backup_frequency": 20,         # Backup cada N interacciones
    "enable_memory_groups": True,   # Organización por grupos
}

# Configuración de la base de conocimiento
KNOWLEDGE_BASE_CONFIG = {
    # Directorio de documentos
    "documents_dir": str(MODELS_DIR / "knowledge_base" / "documents"),
    "index_file": str(MODELS_DIR / "knowledge_base" / "faiss_index"),
    
    # Modelo de embeddings
    "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    
    # Parámetros de búsqueda
    "max_results": 5,              # Máximo documentos por búsqueda
    "similarity_threshold": 0.7,   # Umbral de similitud
    "chunk_size": 500,            # Tamaño de fragmentos de texto
    "chunk_overlap": 50,          # Solapamiento entre fragmentos
}

# Configuración del servidor API
API_CONFIG = {
    "host": "127.0.0.1",
    "port": 8000,
    "debug": False,
    "cors_origins": ["*"],  # Orígenes permitidos para CORS
    "max_request_size": 10 * 1024 * 1024,  # 10MB
}

# Configuración de logging
LOGGING_CONFIG = {
    "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": str(BASE_DIR / "logs" / "leonel.log"),
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5,
}

# Configuración de optimización
OPTIMIZATION_CONFIG = {
    "enable_caching": True,        # Cache de respuestas
    "cache_size": 100,            # Tamaño del cache
    "enable_compression": True,    # Compresión de datos
    "memory_cleanup_interval": 300,  # Limpieza cada 5 minutos
}

# Configuración específica para hardware limitado (Jetson Nano, Raspberry Pi)
HARDWARE_OPTIMIZATION = {
    "low_memory_mode": False,      # Modo de bajo consumo de memoria
    "reduce_context_size": False,  # Reducir tamaño de contexto
    "enable_swap_usage": False,    # Permitir uso de swap
    "max_concurrent_requests": 1,  # Máximo requests simultáneos
}

# Configuración de seguridad
SECURITY_CONFIG = {
    "enable_rate_limiting": True,   # Limitación de velocidad
    "max_requests_per_minute": 60, # Máximo requests por minuto
    "enable_input_validation": True, # Validación de entrada
    "max_input_length": 2000,      # Máximo caracteres de entrada
}