# 🤖 CONTEXT.md – Asistente Multimodal Offline para Jetson Nano

## 📋 Resumen Ejecutivo
**Proyecto:** Asistente conversacional offline modular para Jetson Nano  
**Stack Principal:** Python (backend) + React/TypeScript (frontend) + Tauri (empaquetado nativo)  
**Objetivo:** Sistema completo de voz, visión y chat con LLM local, optimizado para hardware limitado

## 🎯 Funcionalidades Core
- **Voz:** STT bidireccional + TTS con interrupción dinámica
- **LLM:** Modelo local (1-3B parámetros) con memoria persistente
- **Memoria:** Sistema inteligente con transición automática corto/largo plazo y gestión granular
- **Visión:** Detección objetos (YOLO), OCR, reconocimiento facial, DOA
- **UI:** Interfaz minimalista retro con rostro animado
- **Conocimiento:** Base de datos vectorial offline (FAISS + embeddings)

---

## 📐 Arquitectura del Sistema

### 🔗 Flujo de Datos Principal
```
Audio Input → STT → Text → LLM + Memory + Knowledge → Response → TTS → Audio Output
Camera Input → Vision Processing → Context → LLM → Visual Response
Text Input → LLM + Memory → Text Output
```

### 🏗️ Estructura de Módulos
```
Assistant/
├── main.py                      # Punto de entrada, orquestador principal
├── requirements.txt             # Dependencias Python
├── README.md                    # Documentación principal
├── backend/
│   ├── llm/                    # Motor de lenguaje natural
│   │   ├── model_manager.py    # Carga y manejo del modelo LLM
│   │   ├── memory_manager.py   # Memoria corto/largo plazo mejorado
│   │   ├── knowledge_base.py   # Base de conocimiento vectorial
│   │   └── embeddings.py       # Generación de embeddings
│   ├── voice/                  # Procesamiento de audio
│   │   ├── stt_processor.py    # Speech-to-Text (Vosk)
│   │   ├── tts_processor.py    # Text-to-Speech (xTTS/Coqui)
│   │   └── audio_manager.py    # Gestión de flujos de audio
│   ├── vision/                 # Procesamiento visual
│   │   ├── object_detector.py  # YOLO + TensorRT
│   │   ├── ocr_processor.py    # Reconocimiento de texto
│   │   ├── face_processor.py   # Reconocimiento facial
│   │   └── camera_manager.py   # Gestión de cámara
│   ├── core/                   # Lógica central
│   │   ├── event_handler.py    # Orquestador de eventos
│   │   ├── state_manager.py    # Estado global del sistema
│   │   └── command_parser.py   # Parsing de comandos
│   └── utils/
│       ├── config.py          # Configuración global
│       ├── logger.py          # Sistema de logging
│       └── hardware.py        # Interfaces hardware (GPIO, motores)
├── docs/                       # Documentación del proyecto
│   ├── MEMORIA_SISTEMA_ACTUALIZADO.md
│   ├── PLAN_PRUEBAS_MEMORIA.md
│   ├── GUIA_PRUEBAS_MANUAL.md
│   └── INSTRUCCIONES_MEMORIA.md
├── tests/                      # Pruebas automatizadas
│   └── test_memoria_automatico.py
├── frontend/                   # Interfaz de usuario
│   ├── src/
│   │   ├── App.tsx            # Componente principal
│   │   ├── components/
│   │   │   ├── Face.tsx       # Rostro animado
│   │   │   ├── Controls.tsx   # Panel de controles
│   │   │   ├── Chat.tsx       # Interfaz de chat
│   │   │   └── StatusBar.tsx  # Barra de estado
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts # Comunicación con backend
│   │   │   └── useAnimations.ts # Animaciones faciales
│   │   └── types/
│   │       └── index.ts       # Tipos TypeScript
│   ├── package.json
│   └── tailwind.config.js
├── tauri.conf.json            # Configuración Tauri
├── models/                    # Modelos de IA
│   ├── llm/                  # Modelos de lenguaje
│   ├── stt/                  # Modelos speech-to-text
│   ├── tts/                  # Modelos text-to-speech
│   ├── vision/               # Modelos de visión
│   ├── knowledge/            # Datos de base de conocimiento
│   └── memory/               # Datos de memoria conversacional
└── data/
    ├── knowledge/            # Documentos para base de conocimiento
    ├── conversations/        # Historial de conversaciones
    └── embeddings/           # Cache de embeddings
```

---

## 🚀 Roadmap de Desarrollo (7 Fases)

### ✅ Fase 1: Backend LLM Local (COMPLETADA)
**Objetivo:** Motor de texto → respuesta funcional

**Entregables:**
- ✅ Modelo LLM cuantizado cargado (GGUF/TensorRT)
- ✅ Sistema de memoria avanzado con gestión granular
- ✅ Base de conocimiento con embeddings (FAISS)
- ✅ Comandos de gestión de memoria implementados
- ✅ Prompt optimizado para respuestas concisas
- ✅ Sistema de ayuda integral (`/help`)
- ✅ API REST básica para testing

**Criterios de Aceptación:**
```python
# Test básico que debe funcionar
from backend.llm.model_manager import LLMManager
llm = LLMManager("models/llm/llama-2-7b-chat.gguf")
response = llm.query("¿Cómo estás?", context=[])
assert len(response) > 0
```

**Dependencias Clave:**
```
llama-cpp-python==0.2.19
langchain==0.0.350
faiss-cpu==1.7.4
sentence-transformers==2.2.2
```

---

### ✅ Fase 2: Sistema de Voz
**Objetivo:** STT + TTS con interrupción dinámica

**Entregables:**
- STT continuo con Vosk (modelo español)
- TTS con xTTS-v2 o Coqui
- Sistema de interrupción: STT puede pausar TTS
- WebSocket para comunicación tiempo real

**Criterios de Aceptación:**
```python
# Flujo voz completo
audio_input → stt.process() → text → llm.query(text) → response → tts.speak(response)
# Interrupción: mientras TTS habla, STT puede interrumpir
```

**Configuración Audio:**
```python
# Configuración recomendada Jetson Nano
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024
AUDIO_FORMAT = pyaudio.paInt16
```

---

### ✅ Fase 3: Base de Conocimiento
**Objetivo:** Consultas semánticas a documentos offline

**Entregables:**
- Indexador de documentos (.txt, .md, .pdf)
- Generador de embeddings optimizado
- Sistema de consulta semántica (top-k similarity)
- Integración con LLM para RAG (Retrieval Augmented Generation)

**Criterios de Aceptación:**
```python
# Pipeline de conocimiento
docs = ["doc1.txt", "doc2.md"]
kb = KnowledgeBase()
kb.index_documents(docs)
relevant_docs = kb.query("¿Cómo configurar Jetson Nano?", top_k=3)
response = llm.query_with_context(user_query, relevant_docs)
```

---

### ✅ Fase 4: Sistema de Visión
**Objetivo:** Visión por computadora contextual

**Entregables:**
- Detección de objetos (YOLOv5/v8 + TensorRT)
- OCR multilenguaje (EasyOCR)
- Reconocimiento facial básico
- DOA (Direction of Arrival) para orientación

**Criterios de Aceptación:**
```python
# Pipeline de visión
frame = camera.capture()
objects = yolo.detect(frame)  # [{"class": "person", "confidence": 0.89, "bbox": [x,y,w,h]}]
text = ocr.extract_text(frame)  # "Texto detectado en imagen"
faces = face_detector.detect(frame)  # [{"name": "unknown", "bbox": [x,y,w,h]}]
```

**Optimizaciones Jetson:**
```python
# Configuración TensorRT
INPUT_SHAPE = (1, 3, 640, 640)  # YOLOv5 estándar
PRECISION = "fp16"  # Mejor balance velocidad/precisión
```

---

### ✅ Fase 5: UI Retrofuturista
**Objetivo:** Interfaz minimalista con rostro animado

**Entregables:**
- Rostro SVG animado (ojos, boca, cejas)
- Panel de controles toggle (Mic/Vision/Voice/Chat)
- Chat interface con historial
- Animaciones sincronizadas con TTS
- Tema oscuro retro

**Componentes React:**
```tsx
// Estructura de estado principal
interface AppState {
  modules: {
    microphone: boolean;
    vision: boolean;
    speech: boolean;
    chat: boolean;
  };
  face: {
    eyes: 'open' | 'closed' | 'winking';
    mouth: 'neutral' | 'smile' | 'talking' | 'frown';
    eyebrows: 'neutral' | 'raised' | 'furrowed';
  };
  conversation: Message[];
  status: 'idle' | 'listening' | 'thinking' | 'speaking';
}
```

**Paleta de Colores Retro:**
```css
:root {
  --primary: #00ff41;      /* Verde terminal */
  --secondary: #ff6b00;    /* Naranja neón */
  --background: #0a0a0a;   /* Negro profundo */
  --surface: #1a1a1a;     /* Gris oscuro */
  --accent: #00d4ff;      /* Azul cian */
}
```

---

### ✅ Fase 6: Integración Total
**Objetivo:** Todos los sistemas funcionando coordinadamente

**Entregables:**
- EventHandler central que orquesta todos los módulos
- Estados mutuamente excluyentes (chat manual vs STT)
- Activación contextual de visión
- Sistema de prioridades para interrupciones
- Logging y debug comprehensivo

**Flujos Principales:**
```python
# Flujo 1: Conversación por voz
usuario_habla → STT → texto → LLM + memoria → respuesta → TTS

# Flujo 2: Consulta visual
usuario_pregunta_sobre_imagen → activar_cámara → procesar_visión → contexto_visual → LLM → respuesta

# Flujo 3: Chat manual
usuario_escribe → desactivar_STT → LLM + memoria → respuesta_texto

# Flujo 4: Interrupción
TTS_hablando + usuario_interrumpe → pausar_TTS → activar_STT → nueva_consulta
```

---

### ✅ Fase 7: Optimización y Deploy
**Objetivo:** Rendimiento óptimo en Jetson Nano

**Entregables:**
- Cuantización INT8 de todos los modelos
- Gestión de memoria optimizada
- Monitoreo de recursos (CPU, GPU, RAM)
- Empaquetado final con Tauri
- Scripts de instalación automática

**Métricas Objetivo:**
```
- Latencia STT: < 100ms
- Latencia LLM: < 2s (respuestas cortas)
- Latencia TTS: < 500ms
- FPS Visión: 10-15 FPS
- RAM Total: < 3GB
- GPU Utilization: < 80%
```

---

## 🔧 Especificaciones Técnicas Detalladas

### Dependencias Python (requirements.txt)
```txt
# LLM y NLP
llama-cpp-python==0.2.19
langchain==0.0.350
sentence-transformers==2.2.2
torch==2.0.1
transformers==4.35.2

# Audio
vosk==0.3.45
pyaudio==0.2.11
pydub==0.25.1
TTS==0.18.2

# Visión
opencv-python==4.8.1.78
ultralytics==8.0.196
easyocr==1.7.0
Pillow==10.0.1

# Base de datos y búsqueda
faiss-cpu==1.7.4
chromadb==0.4.15

# Comunicación y utils
websockets==11.0.3
fastapi==0.104.1
uvicorn==0.24.0
numpy==1.24.3
pydantic==2.4.2
python-dotenv==1.0.0
```

### Configuración Hardware
```python
# config.py - Configuración optimizada Jetson Nano
JETSON_CONFIG = {
    "CPU_CORES": 4,
    "GPU_MEMORY": 2048,  # MB
    "RAM_LIMIT": 3072,   # MB
    "SWAP_SIZE": 6144,   # MB
    "CAMERA_DEVICE": "/dev/video0",
    "AUDIO_DEVICE": "hw:1,0",
    "GPIO_PINS": {
        "LED_STATUS": 18,
        "BUTTON_WAKE": 16,
        "SERVO_PAN": 32,
        "SERVO_TILT": 33
    }
}
```

### API Endpoints Backend
```python
# FastAPI routes principales
GET    /api/status              # Estado del sistema
POST   /api/chat               # Chat manual
POST   /api/voice/start        # Iniciar STT
POST   /api/voice/stop         # Detener STT
POST   /api/vision/capture     # Captura y análisis de imagen
GET    /api/conversation       # Historial de conversación
POST   /api/knowledge/query    # Consulta base de conocimiento
WebSocket /ws                  # Comunicación tiempo real
```

---

## 🎮 Guía de Comandos de Voz

### Comandos del Sistema
- **"Hey asistente"** → Activar escucha
- **"Detente"** → Pausar TTS actual
- **"Silencio"** → Desactivar TTS temporalmente
- **"Mira esto"** → Activar cámara y analizar
- **"¿Qué ves?"** → Describir entorno visual
- **"Recuerda esto: [texto]"** → Guardar en memoria largo plazo
- **"¿Qué sabes sobre [tema]?"** → Consultar base de conocimiento

### Comandos de Control
- **"Activa la cámara"** → vision: true
- **"Desactiva el micrófono"** → microphone: false  
- **"Modo texto solamente"** → chat: true, speech: false
- **"Estado del sistema"** → Reporte de módulos activos

## 🎤 Comandos de Voz Disponibles

### Comandos Básicos
- `/help` - Mostrar ayuda
- `/status` - Estado del sistema
- `/clear` - Limpiar conversación
- `/exit` - Salir del programa

### Comandos de Memoria Mejorados ✅
- `/memory` - Ver memoria actual (corto plazo)
- `/list_short` - Listar todas las interacciones de memoria a corto plazo con índices
- `/list_long` - Listar todas las interacciones de memoria a largo plazo con índices
- `/delete_short [índice]` - Eliminar interacción específica de memoria a corto plazo
- `/delete_long [índice]` - Eliminar interacción específica de memoria a largo plazo
- `/clear` - Limpiar memoria a corto plazo completamente
- `/forget` - Olvidar conversación actual
- `/remember [texto]` - Recordar información específica

### Comandos de Conocimiento
- `/rag [consulta]` - Buscar en base de conocimiento usando RAG
- `/add [archivo]` - Agregar documento a la base de conocimiento

---

## 🔄 Estado Actual del Desarrollo (Actualizado)

### ✅ Implementaciones Completadas Recientemente

#### Sistema de Memoria Granular
- **Gestión avanzada de memoria:** Implementados comandos `/list_short`, `/list_long`, `/delete_short`, `/delete_long`
- **Validación robusta:** Manejo de errores y validación de índices (comenzando en 1)
- **Persistencia automática:** Los cambios se guardan automáticamente usando `_save_memory()`
- **Interfaz mejorada:** Comandos con numeración clara para facilitar la gestión

#### Optimización del LLM
- **Prompt optimizado:** Respuestas más concisas y directas
  - Máximo 2-3 oraciones para preguntas simples
  - Máximo 100 palabras para consultas complejas
  - Estilo directo y conversacional
- **Mejor contexto:** Integración mejorada de memoria y conocimiento

#### Comando de Ayuda Integral
- **`/help` implementado:** Lista organizada de todos los comandos disponibles
- **Categorización clara:** Comandos de sistema, memoria y conocimiento
- **Documentación en tiempo real:** Ayuda contextual integrada

#### Correcciones y Mejoras
- **Bugs corregidos:** Solucionado error de método `save_memory` → `_save_memory`
- **Consistencia de índices:** Todos los comandos de borrado usan índices base-1
- **Manejo de errores:** Validación completa de parámetros y estados

### 🔧 Archivos Modificados
- `main.py`: Comandos de gestión de memoria, comando `/help`, correcciones de bugs
- `model_manager.py`: Optimización del prompt del sistema para respuestas concisas
- `memory_manager.py`: Sistema de memoria con métodos privados `_save_memory`

### 📊 Métricas de Funcionalidad
- **Comandos implementados:** 12+ comandos funcionales
- **Gestión de memoria:** 100% operativa con CRUD completo
- **Base de conocimiento:** RAG funcional con embeddings
- **Interfaz de usuario:** CLI mejorada con ayuda contextual

---

## 🧪 Casos de Uso y Testing

### Caso 1: Conversación Básica
```
Usuario: "Hola, ¿cómo estás?"
Sistema: [STT] → [LLM] → "¡Hola! Estoy funcionando correctamente. ¿En qué puedo ayudarte?"
```

### Caso 2: Consulta Visual
```
Usuario: "¿Qué ves en esta imagen?"
Sistema: [Activar cámara] → [YOLO + OCR] → [LLM con contexto visual] → "Veo una persona sentada en un escritorio con una computadora portátil. También hay texto que dice 'Jetson Nano Development Kit'."
```

### Caso 3: Base de Conocimiento
```
Usuario: "¿Cómo instalo TensorRT en Jetson Nano?"
Sistema: [Consulta embeddings] → [Recupera documentos relevantes] → [LLM + RAG] → "Según la documentación, primero debes..."
```

### Caso 4: Interrupción Dinámica
```
Sistema: [TTS hablando] "Para instalar TensorRT necesitas primero..."
Usuario: [Interrumpe] "Espera, ya lo tengo instalado"
Sistema: [Pausa TTS] → [STT] → [LLM] → "Perfecto, entonces podemos continuar con..."
```

---

## 🐛 Debug y Troubleshooting

### Logs Principales
```python
# logger.py - Configuración de logging
LOGS = {
    "llm.log": "Consultas y respuestas del LLM",
    "audio.log": "STT/TTS eventos y errores", 
    "vision.log": "Detecciones y procesamiento visual",
    "system.log": "Estado general y recursos",
    "errors.log": "Errores críticos del sistema"
}
```

### Comandos de Diagnóstico
```bash
# Verificar modelos cargados
python -m backend.utils.check_models

# Test individual de componentes
python -m backend.llm.test_model
python -m backend.voice.test_stt
python -m backend.vision.test_yolo

# Monitor de recursos
python -m backend.utils.monitor_resources
```

---

## 📚 Referencias y Documentación

### Modelos Recomendados
- **LLM:** Llama-2-7B-Chat-GGUF (cuantizado Q4_K_M)
- **STT:** vosk-model-es-0.42 (español, 39MB)
- **TTS:** tts_models/es/mai/tacotron2-DDC (español)
- **Vision:** YOLOv5s (28MB) o YOLOv8n (6MB)
- **Embeddings:** all-MiniLM-L6-v2 (80MB)

### Links de Descarga
```bash
# Scripts de descarga automática
wget -O models/llm/llama-2-7b-chat.Q4_K_M.gguf \
  https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf

wget -O models/stt/vosk-model-es.zip \
  https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip
```

### Configuración Jetson Nano
```bash
# Optimizaciones recomendadas
sudo nvpmodel -m 0  # Modo máximo rendimiento
sudo jetson_clocks   # Máxima frecuencia CPU/GPU
echo 'export CUDA_VISIBLE_DEVICES=0' >> ~/.bashrc
```

---

## ✨ Próximos Pasos de Implementación

### 🎯 Estado Actual: Fase 1 Completada

**✅ Ya implementado:**
- Backend LLM completamente funcional
- Sistema de memoria granular con CRUD completo
- Base de conocimiento con RAG
- Interfaz CLI con comandos avanzados
- Gestión de errores y validación robusta

### 🚀 Siguiente: Fase 2 - Sistema de Voz

**Próximos pasos recomendados:**

1. **Implementar STT (Speech-to-Text):**
   - Integrar Vosk con modelo español
   - Configurar captura de audio continua
   - Implementar detección de actividad de voz

2. **Implementar TTS (Text-to-Speech):**
   - Integrar xTTS-v2 o Coqui TTS
   - Configurar síntesis de voz en español
   - Implementar sistema de interrupción dinámica

3. **WebSocket para comunicación tiempo real:**
   - Establecer comunicación bidireccional
   - Sincronizar STT/TTS con interfaz
   - Implementar estados de audio (escuchando/hablando)

**Comando de inicio actual:**
```bash
cd Assistant
python main.py  # Sistema completamente funcional
```

**Comandos disponibles para testing:**
```bash
/help           # Ver todos los comandos
/list_short     # Ver memoria a corto plazo
/list_long      # Ver memoria a largo plazo
/rag [consulta] # Buscar en base de conocimiento
```
