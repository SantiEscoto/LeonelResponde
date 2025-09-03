# Configuración y Solución de Problemas - Leonel Responde

## Configuración del Sistema

### 1. Configuración del LLM

El archivo `config.py` contiene la configuración principal del sistema. Para asegurar respuestas consistentes en español:

```python
LLM_CONFIG = {
    "model_path": str(MODELS_DIR / "llm" / "llama-2-7b-chat.Q4_K_M.gguf"),
    "temperature": 0.7,     # Reducir para respuestas más consistentes
    "force_spanish": True,  # Forzar respuestas en español
}
```

### 2. Configuración de Memoria

Para asegurar que la memoria persista entre sesiones:

```python
MEMORY_CONFIG = {
    "auto_save": True,              # CRÍTICO: Guardar automáticamente
    "max_short_term_memory": 50,    # Memoria a corto plazo
    "auto_transition_threshold": 25, # Transición automática
    "backup_frequency": 20,         # Respaldos frecuentes
}
```

### 3. Optimización de Rendimiento

Para hardware limitado (Jetson Nano, Raspberry Pi):

```python
LLM_CONFIG = {
    "n_ctx": 2048,          # Reducir contexto
    "n_threads": 2,         # Menos hilos
    "n_gpu_layers": 0,      # Solo CPU
    "max_tokens": 256,      # Respuestas más cortas
}
```

## Problemas Comunes y Soluciones

### 1. El asistente responde en inglés

**Problema**: A pesar de la configuración, el asistente responde en inglés.

**Soluciones**:

1. **Verificar configuración del prompt**:
   - El archivo `backend/llm/model_manager.py` debe tener un prompt estricto en español
   - Asegurar que `force_spanish: True` en `config.py`

2. **Reiniciar el servidor**:
   ```bash
   # Detener el servidor actual
   pkill -f "python.*api.py"
   
   # Reiniciar
   cd /ruta/al/proyecto/Assistant
   python backend/api.py
   ```

3. **Verificar modelo**:
   - Algunos modelos tienen mejor soporte para español
   - Probar con modelos específicos para español

### 2. La memoria no persiste entre sesiones

**Problema**: El asistente no recuerda conversaciones anteriores.

**Soluciones**:

1. **Verificar archivos de memoria**:
   ```bash
   ls -la models/memory/
   # Debe mostrar: conversation_history.json
   ```

2. **Verificar permisos**:
   ```bash
   chmod 755 models/memory/
   chmod 644 models/memory/*.json
   ```

3. **Verificar configuración**:
   - `auto_save: True` en `MEMORY_CONFIG`
   - Ruta correcta del archivo de memoria

4. **Forzar guardado manual**:
   ```bash
   curl -X POST "http://localhost:8000/query" \
        -H "Content-Type: application/json" \
        -d '{"text": "/memory_save", "use_memory": true}'
   ```

### 3. Rendimiento lento

**Problema**: El asistente tarda mucho en responder.

**Soluciones**:

1. **Optimizar configuración**:
   ```python
   LLM_CONFIG = {
       "n_ctx": 2048,        # Reducir contexto
       "max_tokens": 256,    # Respuestas más cortas
       "n_threads": 4,       # Ajustar según CPU
   }
   ```

2. **Usar GPU si está disponible**:
   ```python
   LLM_CONFIG = {
       "n_gpu_layers": 20,   # Mover capas a GPU
   }
   ```

3. **Limpiar memoria regularmente**:
   ```bash
   curl -X POST "http://localhost:8000/clear-memory"
   ```

### 4. Errores de memoria insuficiente

**Problema**: El sistema se queda sin memoria RAM.

**Soluciones**:

1. **Activar modo de bajo consumo**:
   ```python
   HARDWARE_OPTIMIZATION = {
       "low_memory_mode": True,
       "reduce_context_size": True,
       "max_concurrent_requests": 1,
   }
   ```

2. **Usar modelo más pequeño**:
   - Cambiar a un modelo Q4_0 o Q3_K_S
   - Reducir `n_ctx` a 1024 o menos

3. **Configurar swap**:
   ```bash
   # En sistemas Linux
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

### 5. El servidor no inicia

**Problema**: Error al iniciar el servidor API.

**Soluciones**:

1. **Verificar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Verificar modelo**:
   ```bash
   ls -la models/llm/
   # Debe contener el archivo .gguf especificado en config.py
   ```

3. **Verificar puerto**:
   ```bash
   lsof -i :8000
   # Si está ocupado, cambiar puerto en config.py
   ```

4. **Revisar logs**:
   ```bash
   tail -f logs/leonel.log
   ```

## Comandos de Diagnóstico

### Verificar estado del sistema
```bash
curl -X GET "http://localhost:8000/status"
```

### Verificar memoria
```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"text": "/memory_count", "use_memory": true}'
```

### Limpiar memoria a corto plazo
```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"text": "/clear_short", "use_memory": true}'
```

### Verificar grupos de memoria
```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"text": "/memory_groups", "use_memory": true}'
```

## Monitoreo del Sistema

### Logs importantes
- `logs/leonel.log`: Log principal del sistema
- `models/memory/backups/`: Respaldos automáticos de memoria

### Métricas de rendimiento
```bash
# Uso de memoria del proceso
ps aux | grep python

# Uso de disco
du -sh models/

# Verificar archivos de memoria
ls -lah models/memory/
```

## Configuración Recomendada por Hardware

### Jetson Nano (4GB RAM)
```python
LLM_CONFIG = {
    "n_ctx": 1024,
    "n_threads": 2,
    "max_tokens": 128,
    "temperature": 0.6,
}

HARDWARE_OPTIMIZATION = {
    "low_memory_mode": True,
    "max_concurrent_requests": 1,
}
```

### Raspberry Pi 4 (8GB RAM)
```python
LLM_CONFIG = {
    "n_ctx": 2048,
    "n_threads": 4,
    "max_tokens": 256,
    "temperature": 0.7,
}
```

### PC Desktop (16GB+ RAM)
```python
LLM_CONFIG = {
    "n_ctx": 4096,
    "n_threads": 8,
    "n_gpu_layers": 20,  # Si tienes GPU
    "max_tokens": 512,
    "temperature": 0.7,
}
```

## Contacto y Soporte

Si los problemas persisten:
1. Revisar los logs en `logs/leonel.log`
2. Verificar la configuración en `config.py`
3. Probar con la configuración de ejemplo en `config_example.py`
4. Consultar la documentación completa en `docs/`