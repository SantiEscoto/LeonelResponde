import os
from pathlib import Path

# Importar torch de forma segura
try:
    import torch
    TORCH_AVAILABLE = True
    MPS_AVAILABLE = torch.backends.mps.is_available() if hasattr(torch.backends, 'mps') else False
except ImportError:
    TORCH_AVAILABLE = False
    MPS_AVAILABLE = False

# Rutas del proyecto
PROJECT_ROOT = Path(__file__).parent
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"

# Configuración LLM
LLM_CONFIG = {
    "model_name": "llama-2-7b-chat.Q4_K_M.gguf",  # Modelo GGUF cuantizado
    "max_tokens": 150,    # Tokens máximos más reducidos para respuestas más rápidas
    "temperature": 0.7,   # Ajustado para balance entre creatividad y velocidad
    "top_p": 0.9,        # Parámetro de muestreo optimizado
    "top_k": 40,         # Reducido para mejor rendimiento
    "repeat_penalty": 1.1,  # Añadido para evitar repeticiones
    "n_gpu_layers": 15,  # Más capas GPU para mejor rendimiento
    "n_ctx": 1024,       # Contexto más reducido para mayor velocidad
    "n_threads": 4,      # Número de hilos para procesamiento paralelo
    "device": "auto",    # Detección automática del mejor dispositivo
    "response_timeout": 45  # Timeout reducido para respuestas más rápidas
}

# Configuración del sistema
SYSTEM_CONFIG = {
    "log_level": "INFO",
    "api_host": "127.0.0.1",
    "api_port": 8000,
    "debug_mode": True
}

# Configuración de la base de conocimiento
KB_CONFIG = {
    "embedding_model": "all-MiniLM-L6-v2",  # Modelo de embeddings ligero
    "index_path": str(MODELS_DIR / "knowledge" / "faiss_index.bin"),
    "documents_path": str(MODELS_DIR / "knowledge" / "documents.json")
}

# Configuración de la memoria
MEMORY_CONFIG = {
    "memory_file": str(MODELS_DIR / "memory" / "conversation_history.json"),
    "memory_groups_file": str(MODELS_DIR / "memory" / "memory_groups.json"),
    "memory_backup_dir": str(MODELS_DIR / "memory" / "backups"),
    "max_short_term_memory": 50,  # Aumentado de 20 a 50 interacciones
    "auto_transition_threshold": 25,  # Reducido para transiciones más frecuentes
    "summary_interval": 8,        # Más frecuente para mejor organización
    "auto_save": True,           # Guardar automáticamente después de cada interacción
    "backup_frequency": 20       # Crear backup cada 20 interacciones
}

# Crear directorios si no existen
MODELS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Variables de entorno para API
API_HOST = SYSTEM_CONFIG["api_host"]
API_PORT = SYSTEM_CONFIG["api_port"]
DEBUG_MODE = SYSTEM_CONFIG["debug_mode"]

print(f"🔧 Configuración cargada:")
print(f"   📁 Modelos: {MODELS_DIR}")
print(f"   📁 Logs: {LOGS_DIR}")
print(f"   🧠 Device: {LLM_CONFIG['device']}")
print(f"   🤖 Modelo: {LLM_CONFIG['model_name']}")
print(f"   📚 Embedding: {KB_CONFIG['embedding_model']}")
if MPS_AVAILABLE:
    print(f"   🚀 Apple Silicon MPS: ✅ Activado")
else:
    print(f"   💻 Usando CPU (normal en Mac Intel)")
