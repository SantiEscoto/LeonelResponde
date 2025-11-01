# Guía de configuración para Jetson/Raspberry Pi (modo mínimo)

Esta guía adapta el asistente para ejecutarse en dispositivos con recursos limitados (Jetson Nano/Orin y Raspberry Pi), priorizando operación 100% offline y bajo consumo.

## Requisitos

- Python 3.10–3.11 (en Jetson Nano suele ser 3.10)
- `pip` y `venv`
- Modelo GGUF pequeño copiado localmente (sin descarga online)

## Instalación de dependencias mínimas

Usa el perfil mínimo sin RAG/FAISS/embeddings:

```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r Assistant/requirements-jetson.txt
```

Notas:
- `llama-cpp-python` se instala en modo CPU por defecto. Si tu dispositivo no soporta GPU, mantén `n_gpu_layers=0`.
- Paquetes como `transformers`, `sentence-transformers`, `faiss-cpu` y `TTS` están excluidos para reducir tamaño y evitar errores.

## Modelo LLM recomendado (GGUF pequeño)

Coloca el archivo del modelo en `Assistant/data/models/` y selecciona uno de bajo tamaño:

- `llama-3.2-1B-Instruct.Q4_K_M.gguf` (muy ligero, respuestas aceptables)
- `qwen2.5-1.5b-instruct.Q4_K_M.gguf` (ligero, buen balance)
- `phi-2.Q4_K_M.gguf` (compacto, clásico)

Ejemplo de copia offline:

```
mkdir -p Assistant/data/models
cp /ruta/al/modelo.gguf Assistant/data/models/
```

### Override del modelo por variable de entorno

Ahora puedes definir el modelo sin editar código:

```
export LLM_MODEL_NAME="llama-3.2-1B-Instruct.Q4_K_M.gguf"
```

El sistema usará `Assistant/data/models/$LLM_MODEL_NAME`.

## Desactivar Knowledge Base (evitar FAISS/embeddings)

Para un entorno mínimo (sin RAG), desactiva la base de conocimiento:

```
export DISABLE_KNOWLEDGE_BASE=1
```

Esto evita errores como `No module named 'faiss'` o `sentence-transformers` ausentes y reduce memoria/CPU.

## Configuración MCP (opcional)

Si usas servidores MCP locales (por ejemplo, para audio/voz), asegúrate de tener el archivo `Assistant/mcp_config.json` con la configuración deseada.

Ejemplo mínimo (compatible con loader del backend):

```
{
  "mcp_servers": [
    {
      "name": "voice_server",
      "enabled": true,
      "config": {
        "host": "0.0.0.0",
        "port": 8765,
        "vosk_model_path": "/ruta/a/vosk-model"
      }
    }
  ],
  "mcpServers": {
    "voice": {
      "command": "python",
      "args": ["-m", "src.backend.voice.server"],
      "description": "Servidor de voz offline",
      "enabled": true
    }
  },
  "version": "1.0.0",
  "description": "Configuración MCP para modo offline mínimo"
}
```

Si no usas MCP, puedes omitir el archivo; el sistema seguirá funcionando.

## Ejecución

Con el entorno activado y variables definidas:

```
source .venv/bin/activate
export DISABLE_KNOWLEDGE_BASE=1
export LLM_MODEL_NAME="llama-3.2-1B-Instruct.Q4_K_M.gguf"
python Assistant/main.py
```

También puedes usar `scripts/run_jetson.sh` si está disponible en tu proyecto.

## Consejos de rendimiento

- Reduce `n_ctx` y `n_threads` en `unified_config.py` si notas lentitud.
- Mantén `n_gpu_layers=0` en dispositivos sin aceleración.
- Evita logs verbosos (`SystemConfig.log_level = "WARNING"`).

## Solución de problemas

- "PyTorch not available: using CPU-only mode": esperado en Jetson/RPi, no es crítico.
- Salud del sistema muestra "Knowledge Base not initialized": normal con `DISABLE_KNOWLEDGE_BASE=1`.
- Error al cargar modelo: verifica `Assistant/data/models/$LLM_MODEL_NAME` existe y nombre coincide.

---

Con esta configuración mínima, el asistente se ejecuta 100% offline y con baja huella en CPU/RAM, ideal para Jetson/RPi.