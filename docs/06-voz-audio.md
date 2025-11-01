# 🎤 Fase 6: Sistema de Voz (FUNDAMENTAL)

## Estado Actual

- WS de voz activo en local: `ws://127.0.0.1:8765` con `/ws/tts` y `/ws/stt`.
- TTS (Coqui XTTS v2) probado, WAV generado a `22050 Hz` (`provider=coqui`).
- STT (Vosk) probado, parciales correctos; el final puede ser vacío según VAD/pausas.
- Clientes frontend TTS/STT listos: `TtsWsClient.tsx` y `VoiceWsClient.tsx` (PCM 16-bit mono 16 kHz, ping/pong y ACK/backpressure desde UI).
- Recomendado para STT final: WAV mono `16 kHz` + VAD (`--binary --use-vad --vad-level 2 --frame-ms 30`).
- Docker listo: servicio `voice-ws` en `docker-compose.yml` y targets en `Makefile` (`voice-env`, `docker-voice-ws-up`).
- En este host, Docker no está instalado; usar `.venv` local hasta instalar Docker.

Comandos rápidos (host):
- TTS: `make ws-tts-demo TEXT="Hola" OUTPUT=ws_tts.wav`
- STT: `make ws-stt-demo INPUT=ws_tts.wav`

Siguientes pasos:
- Migrar localmente a Python 3.11 o usar Docker para evitar conflictos de `numpy/librosa`.
- Mejorar VAD/resampling a `16 kHz` y ajustar chunking para finalizar con texto.
- Integrar WS de voz con la UI web/PySide6.

## 🐳 Docker (Python 3.11) para Voz

> Recomendado para evitar conflictos locales y habilitar XTTS/aiortc/pyaudio.
- Construir imagen: `docker compose build`
- Abrir shell: `docker compose run --rm assistant-dev`
- Dentro del contenedor, ejecutar pruebas de voz o backend.
- Nota: UI PySide6 en contenedor requiere entorno gráfico; usa el navegador en host o ejecuta la UI en host.

### Servidor de Voz (Docker)

Con el contenedor ya construido, puedes levantar el servidor de voz (STT/TTS):

- Ejecutar servidor: `docker compose run --rm --service-ports assistant-dev python Assistant/src/mcp_servers/voice_server.py`
  - Variables opcionales: `-e VOICE_SERVER_HOST=0.0.0.0 -e VOICE_SERVER_PORT=8000`

Endpoints disponibles:
- `GET /status` — Estado del servidor
- `GET /info` — Información del sistema de audio
- `GET /devices` — Dispositivos de entrada (si el contenedor tiene acceso)
- `GET /health` — Comprobación de salud
- `POST /record` — Graba audio del micrófono
- `POST /transcribe` — Transcribe archivo WAV mono 16 kHz
- `POST /record_and_transcribe` — Graba y transcribe
- `POST /tts` — TTS (Coqui XTTS → fallback pyttsx3)

Ejemplos rápidos:
- Estado: `curl http://localhost:8000/status`
- TTS y guardar WAV:
  `curl -s -X POST http://localhost:8000/tts -H "Content-Type: application/json" -d '{"text":"Hola, ¿cómo estás?"}' | jq -r '.audio_base64' | base64 -d > salida.wav`
- Transcribir archivo montado en el repo:
  `curl -s -X POST http://localhost:8000/transcribe -H "Content-Type: application/json" -d '{"audio_file_path":"Assistant/data/voice_samples/ws_tts_16k.wav"}'`

Nota sobre micrófono en Docker (macOS):
- El acceso directo al micrófono desde contenedores suele estar restringido. `POST /record` puede no funcionar; usa `POST /transcribe` con archivos montados o ejecuta la UI nativa en host.
- En Linux, con permisos y `portaudio` instalados (el Dockerfile ya incluye `libportaudio2` y `portaudio19-dev`), `sounddevice` puede funcionar dentro del contenedor.

### Streaming por WebSocket (Listo para pruebas)

Ya contamos con un servidor WS básico para TTS/STT con soporte de audio binario y VAD:

- Levantar servidor WS (local): `VOSK_MODEL_PATH=./models/voice/vosk-model-small-es-0.42 VOICE_WS_HOST=0.0.0.0 VOICE_WS_PORT=8010 python -m Assistant.src.mcp_servers.voice_ws_server` (ws://localhost:8010)
+ Levantar servidor WS (local): `VOSK_MODEL_PATH=./models/voice/vosk-model-small-es-0.42 VOICE_WS_HOST=0.0.0.0 VOICE_WS_PORT=8010 python -m Assistant.src.mcp_servers.voice_ws_server` (ws://localhost:8010)
  - Alternativa Docker: `make docker-voice-ws-server` (ws://localhost:8765)
  - Endpoints WS:
    - `ws://localhost:8010/ws/tts` — TTS por WebSocket (chunks de audio, con control de interrupción)
    - `ws://localhost:8010/ws/stt` — STT por WebSocket con chunks base64 o binarios

Protocolo TTS:
- Cliente → `{"type":"tts_request","text":"Hola mundo"}`
- Interrupción (opcional) → Cliente puede enviar `{"type":"stop_tts"}` en cualquier momento
- Servidor → `{"type":"tts_start"}` → múltiples `{"type":"audio_chunk","seq":N,"data_base64":"..."}` → `{"type":"tts_end","provider":"coqui|pyttsx3","format":"wav","sample_rate":22050}`
- Si se interrumpe → `{"type":"tts_interrupted"}`
- Servidor → `{"type":"tts_start"}` → múltiples `{"type":"audio_chunk","seq":N,"data_base64":"..."}` → `{"type":"tts_end","provider":"coqui|pyttsx3","format":"wav","sample_rate":22050}`

Protocolo STT (actualizado):
- Inicio → `{"type":"stt_start","sample_rate":16000,"use_vad":true,"vad_level":2,"frame_ms":30}`
  - `use_vad` (opcional, por defecto `true`): activa VAD en servidor
  - `vad_level` (0–3, por defecto 2): agresividad del VAD
  - `frame_ms` (por defecto 30 ms): tamaño de frame para VAD
- Audio:
  - Base64 → `{"type":"audio_chunk","data_base64":"..."}`
  - Binario → enviar bytes PCM mono 16-bit directamente tras `stt_start`
- Fin → `{"type":"stt_end"}`
- Respuestas del servidor:
  - Parciales → `{"type":"partial","text":"..."}`
  - Final → `{"type":"final","text":"...","confidence":0.0}`
  - Keepalive → `{"type":"pong","ts":<cliente>,"server_ts":<servidor>}` (respuesta a `{"type":"ping"}`)
  - Backpressure → `{"type":"ack","seq":N,"accepted":true|false}` por cada chunk (el cliente envía el siguiente chunk al recibir `ack`)

Estado actual:
- Soporte de audio binario y VAD en STT ✅
- Keepalive (ping/pong) en el servidor WS ✅
- Backpressure básico mediante ACK por chunk ✅
- Servidor WS STT activo en `ws://localhost:8010/ws/stt` con modelo Vosk pequeño ✅
- TTS operativo vía Coqui XTTS v2 en `/ws/tts` (speaker_wav temporal) ✅
- Fallback a `pyttsx3` disponible; `DISABLE_COQUI=1` fuerza fallback ✅
- Parche PyTorch 2.6 `safe_globals` aplicado: `XttsConfig`, `XttsAudioConfig`, `BaseDatasetConfig`, `XttsArgs` ✅

Nota (STT offline con Vosk):
- Descarga un modelo de español y colócalo en `./models/voice/`.
- Puedes usar `VOSK_MODEL_PATH` para apuntar al modelo sin renombrar:
  - Ejemplo: `VOSK_MODEL_PATH=./models/voice/vosk-model-small-es-0.42`
- Modelos: https://alphacephei.com/vosk/models (recomendado `vosk-model-small-es-0.42`).

Demo TTS por WS:
- Host: `make ws-tts-demo TEXT="Hola" OUTPUT=ws_tts.wav`
- Cliente en contenedor: `make ws-tts-demo HOST=host.docker.internal TEXT="Hola"`
+ Puertos:
+ - Local (host): `VOICE_WS_PORT=8010` → ws://localhost:8010
+ - Docker Compose: `VOICE_WS_PORT=8765` → ws://localhost:8765
- Interrupción manual en clientes personalizados: envía `{"type":"stop_tts"}` tras recibir los primeros `audio_chunk`.
+ Ejecución directa (host): `python Assistant/scripts/ws_tts_demo.py --host localhost --port 8010 --text "Hola" --output out_tts.wav --ping-interval 60 --ping-timeout 600`
- Host: `make ws-stt-demo INPUT=Assistant/data/voice_samples/ws_tts_16k.wav`
- Recomendado: WAV mono PCM 16-bit; en contenedor usa `HOST=host.docker.internal`

Resumen de validación TTS:
- `/ws/tts` probado con ping `60s` y timeout `600s`, estable.
- Texto corto y largo generados; salida en `out_tts_coqui.wav` y `out_tts_long.wav`.
- Dos solicitudes consecutivas funcionaron sin reinicios del servidor.
- Coqui XTTS v2 activo con `speaker_wav` temporal; `provider=coqui` confirmado.
- Fallback a `pyttsx3` operativo; usar `DISABLE_COQUI=1` para forzar.

Demo STT por WS (base64):
- Host: `make ws-stt-demo INPUT=Assistant/data/voice_samples/ws_tts_16k.wav`
- Recomendado: WAV mono PCM 16-bit; en contenedor usa `HOST=host.docker.internal`

Demo STT por WS (binario + VAD):
- Host: `make ws-stt-demo-binary INPUT=Assistant/data/voice_samples/ws_tts_16k.wav`
- Flags en cliente: `--binary --use-vad --vad-level 2 --frame-ms 30`

Cliente WebAudio mínimo (frontend):
- El componente `frontend/src/components/VoiceWsClient.tsx` captura audio con WebAudio y envía PCM 16-bit mono por WS a `/ws/stt`.
- Integra VAD (configurable), ping/pong y backpressure por ACK (solo envía el siguiente chunk tras recibir `ack`).
- Prueba rápida:
  - Backend WS: `make docker-voice-ws-server`
  - Frontend: `make frontend-dev` → abre `http://localhost:5173/` (por defecto Vite)
  - En la app, usa el bloque "Prueba de Voz por WebSocket" para conectar, iniciar y observar parciales/finales; revisa "Backpressure" en el estado.

Notas prácticas:
- Para binario, asegúrate de WAV 16-bit mono; el `sample_rate` del `stt_start` debe coincidir.
- En macOS con Docker, usa `HOST=host.docker.internal` desde clientes dentro del contenedor.
- Vosk suele trabajar mejor a `16000 Hz`. WebAudio en navegadores trabaja a `44100/48000 Hz`. Para pruebas es válido, pero en producción conviene hacer resampling a `16000 Hz` o usar un modelo que coincida con tu `sample_rate`.

Siguientes pasos de streaming:
- Ajustar latencia y resampling en el cliente WebAudio
- Keepalive/heartbeat y tuning de timeouts (ya disponible)
- Backpressure y frecuencia de parciales (ACK ya disponible; ajustar tamaños de buffer/frames)
- Integración con UI WebAudio mínima para prueba end-to-end (listo)

## 🎯 Objetivos de esta Fase

- **Implementar STT/TTS de nivel comercial** para interacción natural
- **Sistema de interrupción** dinámica y natural como persona real
- **Grabación y procesamiento** de audio en tiempo real optimizado
- **Integración perfecta con chat** para conversaciones fluidas
- **Voz humana y expresiva** que suene natural
- **Testing completo** del sistema de voz

## ⏱️ Tiempo Estimado

**2 semanas** (10 días de trabajo)

## 📋 Checklist de Tareas

### **Semana 1: STT/TTS de Nivel Comercial**
- [ ] **Día 1-2: STT con Whisper**
  - [ ] Configurar Whisper optimizado para hardware limitado
  - [x] Implementar streaming de audio en tiempo real (WS STT funcionando)
  - [x] Sistema de detección de voz activa (VAD) (WS STT con webrtcvad)
  - [ ] Procesamiento de audio con noise reduction
  - [x] Servidor WS STT operativo (puerto 8010) con Vosk

- [ ] **Día 3-4: TTS de Alta Calidad**
  - [ ] Implementar ElevenLabs API para TTS comercial
  - [ ] Configurar Coqui TTS como alternativa open source
  - [ ] Integrar Coqui XTTS en PySide6 Web UI (respuesta con voz)
  - [ ] Sistema de clonación de voz personalizada
  - [ ] Múltiples voces y estilos expresivos

- [ ] **Día 5: Integración STT/TTS**
  - [ ] Pipeline completo de voz a voz
  - [ ] Sincronización perfecta entre STT y TTS
  - [ ] Sistema de caché de audio para respuestas frecuentes
  - [ ] Optimización de latencia

### **Semana 2: Interacción Natural y Avanzada**
- [ ] **Día 6-7: Interrupción Dinámica**
  - [ ] Sistema de detección de interrupciones inteligente
  - [ ] Gestión de prioridades como persona real
  - [ ] Pausa y reanudación natural
  - [ ] Feedback visual y auditivo avanzado

- [ ] **Día 8-9: Integración con Chat**
  - [ ] WebSocket optimizado para audio streaming
  - [ ] Sincronización perfecta con sistema de chat
  - [ ] Gestión de sesiones de voz multiusuario
  - [ ] Manejo inteligente de errores de audio

- [ ] **Día 10: Testing y Optimización**
  - [ ] Testing completo del sistema de voz
  - [ ] Optimización para hardware limitado
  - [ ] Documentación de la API
  - [ ] Preparación para siguiente fase

## 🔧 Herramientas Necesarias

### **STT (Speech-to-Text) - RECOMENDADO**
- **Whisper (OpenAI)**: STT de alta calidad, open source
- **Google Cloud Speech-to-Text**: Alternativa comercial
- **Azure Speech Services**: Microsoft alternativa
- **DeepSpeech (Mozilla)**: Open source alternativo

### **TTS (Text-to-Speech) - ESTRATEGIA HÍBRIDA**
- **ElevenLabs**: TTS comercial de máxima calidad (recomendado)
- **Coqui TTS**: Open source de alta calidad
- **Tortoise TTS**: Open source avanzado
- **Bark TTS**: Open source con expresividad
- **Google Cloud TTS**: Alternativa comercial
- **Azure TTS**: Microsoft alternativa

### **Procesamiento de Audio**
- **librosa**: Análisis de audio avanzado
- **soundfile**: Manipulación de archivos
- **webrtcvad**: Detección de voz activa
- **noisereduce**: Reducción de ruido
- **numpy**: Cálculos numéricos
- **scipy**: Procesamiento de señales

### **Frontend**
- **Web Audio API**: Audio en navegador
- **MediaRecorder**: Grabación de alta calidad
- **WebSocket**: Streaming optimizado
- **Canvas**: Visualización de audio en tiempo real

## 🏗️ Arquitectura del Sistema de Voz

### **📐 Componentes Principales**

```
┌─────────────────────────────────────────────────────────────┐
│                    VOICE SYSTEM                            │
├─────────────────────────────────────────────────────────────┤
│  Whisper + TTS + WebRTC + Audio Processing                │
│  • STT en tiempo real con Whisper                         │
│  • TTS con múltiples voces                                │
│  • Interrupción dinámica y natural                        │
│  • Streaming de audio optimizado                          │
└─────────────────────────────────────────────────────────────┘
                                ↕️
┌─────────────────────────────────────────────────────────────┐
│                    CHAT INTEGRATION                        │
├─────────────────────────────────────────────────────────────┤
│  WebSocket + Audio Streaming + Session Management         │
│  • Sincronización con sistema de chat                     │
│  • Gestión de sesiones de voz                             │
│  • Manejo de interrupciones                               │
│  • Feedback visual y auditivo                             │
└─────────────────────────────────────────────────────────────┘
```

### **🔄 Flujo de Audio**

```
Audio Input → STT → Text → LLM → Response → TTS → Audio Output
```

## 🎯 Estrategia de TTS: Híbrida Comercial + Open Source

### **📊 Análisis de Opciones TTS 2025 - ENFOQUE GRATUITO**

| **Opción** | **Calidad** | **Costo** | **Licencia** | **Recomendación** |
|------------|-------------|-----------|--------------|-------------------|
| **XTTTS (Coqui)** | ⭐⭐⭐⭐⭐ | Gratis | MPL-2.0 | ✅ **PRINCIPAL** |
| **Tortoise TTS** | ⭐⭐⭐⭐ | Gratis | MIT | ✅ **BACKUP** |
| **Bark TTS** | ⭐⭐⭐⭐ | Gratis | MIT | ✅ **BACKUP** |
| **MaryTTS** | ⭐⭐⭐ | Gratis | BSD | ⚠️ **ALTERNATIVA** |
| **Vosk (STT)** | ⭐⭐⭐⭐ | Gratis | Apache 2.0 | ✅ **STT PRINCIPAL** |
| **Whisper** | ⭐⭐⭐⭐⭐ | Gratis | MIT | ✅ **STT ALTERNATIVO** |

### **🎯 Estrategia Recomendada - 100% GRATUITA**

#### **1. XTTTS (Coqui) como Principal (Recomendado)**
```python
# Ventajas de XTTTS:
# ✅ Calidad de voz humana excepcional
# ✅ Clonación de voz con solo 3-10 segundos de audio
# ✅ Soporte para 1,100+ idiomas
# ✅ Completamente gratuito
# ✅ Licencia MPL-2.0 (uso comercial permitido)
# ✅ Fork activo por Idiap (mantenimiento continuo)
```

#### **2. Tortoise TTS como Backup**
```python
# Ventajas de Tortoise TTS:
# ✅ Calidad muy alta
# ✅ Licencia MIT (sin restricciones)
# ✅ Clonación de voz avanzada
# ✅ Completamente gratuito
# ✅ Control total del código
```

#### **3. Vosk + Whisper para STT**
```python
# Ventajas de Vosk:
# ✅ STT offline (sin internet)
# ✅ Múltiples idiomas
# ✅ Ligero y eficiente
# ✅ Licencia Apache 2.0
# ✅ Funciona en hardware limitado

# Ventajas de Whisper:
# ✅ Calidad excepcional
# ✅ Licencia MIT
# ✅ Multilingüe
# ✅ Open source de OpenAI
```

#### **4. Implementación Híbrida Gratuita**
```python
# Estrategia de fallback GRATUITA:
# 1. Intentar XTTTS (máxima calidad, gratis)
# 2. Si falla, usar Tortoise TTS (backup, gratis)
# 3. Si falla, usar Bark TTS (emergencia, gratis)
# 4. STT: Vosk (offline) + Whisper (online)
# 5. Cache de audio para respuestas frecuentes
```

## 🚀 Implementación

### **1. Dependencias para Voz**

> Nota de compatibilidad macOS/Python 3.9:
> - Para evitar conflictos entre `TTS`/`librosa` y `numpy`, ajusté `requirements-voice.txt` a `numpy==1.22.0`, `pandas==1.5.3`, `librosa==0.9.2`.
> - Dejé temporalmente fuera `TTS`, `aiortc` y `pyaudio` por incompatibilidades de entorno (Coqui XTTS opcional; WebRTC y captura de micrófono requieren librerías del sistema).
> - Para habilitar XTTS y streaming en este entorno: usa Python 3.11, instala `pkg-config` y `ffmpeg` con Homebrew y `portaudio` si quieres `pyaudio`.
>   - `brew install pkg-config ffmpeg portaudio`
>   - Vuelve a activar las líneas correspondientes en `Assistant/requirements-voice.txt` y reinstala.

```python
# requirements-voice.txt
# STT (Speech-to-Text) - 100% Gratuito
openai-whisper==20231117  # Whisper (MIT License)
vosk==0.3.45             # Vosk (Apache 2.0)
webrtcvad==2.0.10        # Voice Activity Detection

# TTS (Text-to-Speech) - 100% Gratuito
TTS==0.22.0              # XTTTS/Coqui TTS (MPL-2.0)
tortoise-tts==2.4.0      # Tortoise TTS (MIT)
bark==1.4.0              # Bark TTS (MIT)
marytts==5.2             # MaryTTS (BSD)

# Audio Processing
pyaudio==0.2.11
librosa==0.10.1
soundfile==0.12.1
noisereduce==3.0.0
scipy==1.11.4

# WebRTC y Streaming
aiortc==1.6.0
websockets==12.0

# Utilities
numpy==1.24.3
pandas==2.0.3
tqdm==4.65.0
```

### **2. Servicio STT con Whisper**

```python
# backend/app/ai/voice/stt_service.py
import whisper
import numpy as np
import io
import tempfile
from typing import Optional, Dict, Any
import torch

class STTService:
    """Servicio de Speech-to-Text con Whisper"""
    
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Cargar modelo Whisper"""
        try:
            self.model = whisper.load_model(self.model_size)
        except Exception as e:
            print(f"Error cargando modelo Whisper: {e}")
            # Fallback a modelo más pequeño
            self.model = whisper.load_model("tiny")
    
    def transcribe_audio(self, audio_data: bytes, language: str = "es") -> Dict[str, Any]:
        """Transcribir audio a texto"""
        try:
            # Guardar audio temporalmente
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()
                
                # Transcribir con Whisper
                result = self.model.transcribe(
                    temp_file.name,
                    language=language,
                    fp16=False  # Para hardware limitado
                )
                
                return {
                    "text": result["text"].strip(),
                    "language": result["language"],
                    "confidence": self._calculate_confidence(result),
                    "segments": result.get("segments", [])
                }
        except Exception as e:
            return {
                "text": "",
                "language": language,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _calculate_confidence(self, result: Dict) -> float:
        """Calcular confianza promedio"""
        if "segments" in result and result["segments"]:
            confidences = [seg.get("avg_logprob", 0) for seg in result["segments"]]
            return np.mean(confidences) if confidences else 0.0
        return 0.0
    
    def transcribe_streaming(self, audio_chunk: bytes, language: str = "es") -> Dict[str, Any]:
        """Transcribir audio en streaming"""
        # Para streaming, usar modelo más pequeño
        if self.model_size != "tiny":
            temp_model = whisper.load_model("tiny")
        else:
            temp_model = self.model
        
        try:
            result = temp_model.transcribe(
                io.BytesIO(audio_chunk),
                language=language,
                fp16=False
            )
            
            return {
                "text": result["text"].strip(),
                "language": result["language"],
                "confidence": self._calculate_confidence(result),
                "is_final": False  # Para streaming
            }
        except Exception as e:
            return {
                "text": "",
                "language": language,
                "confidence": 0.0,
                "error": str(e),
                "is_final": False
            }
```

### **3. Servicio TTS 100% Gratuito (Open Source)**

```python
# backend/app/ai/voice/tts_service.py
import asyncio
import tempfile
import io
from typing import Optional, Dict, Any, List
import threading
import queue
import os
from TTS.api import TTS as CoquiTTS
import torch

class FreeTTSService:
    """Servicio TTS 100% gratuito con Open Source"""
    
    def __init__(self):
        # Configuración TTS Open Source
        self.xttts = None          # XTTTS (Coqui) - Principal
        self.tortoise_tts = None  # Tortoise TTS - Backup
        self.bark_tts = None      # Bark TTS - Emergencia
        self.mary_tts = None      # MaryTTS - Alternativa
        
        # Estado
        self.is_speaking = False
        self.speech_queue = queue.Queue()
        self.audio_cache = {}
        
        # Inicializar servicios
        self._initialize_services()
    
    def _initialize_services(self):
        """Inicializar todos los servicios TTS gratuitos"""
        try:
            # Inicializar XTTTS (Coqui) - Principal
            self.xttts = CoquiTTS("tts_models/multilingual/multi-dataset/xtts_v2")
            print("✅ XTTTS (Coqui) inicializado - Calidad máxima")
        except Exception as e:
            print(f"⚠️ Error inicializando XTTTS: {e}")
        
        try:
            # Inicializar Tortoise TTS - Backup
            from tortoise.api import TextToSpeech
            self.tortoise_tts = TextToSpeech()
            print("✅ Tortoise TTS inicializado - Backup de alta calidad")
        except Exception as e:
            print(f"⚠️ Error inicializando Tortoise TTS: {e}")
        
        try:
            # Inicializar Bark TTS - Emergencia
            from bark import SAMPLE_RATE, generate_audio, preload_models
            preload_models()
            self.bark_tts = True
            print("✅ Bark TTS inicializado - Emergencia con expresividad")
        except Exception as e:
            print(f"⚠️ Error inicializando Bark TTS: {e}")
        
        try:
            # Inicializar MaryTTS - Alternativa
            from marytts import MaryTTS
            self.mary_tts = MaryTTS()
            print("✅ MaryTTS inicializado - Alternativa estable")
        except Exception as e:
            print(f"⚠️ Error inicializando MaryTTS: {e}")
    
    async def speak_text(self, text: str, voice: Optional[str] = None, 
                        quality: str = "high") -> Dict[str, Any]:
        """Convertir texto a voz con estrategia 100% gratuita"""
        
        # Verificar caché primero
        cache_key = f"{text}_{voice}_{quality}"
        if cache_key in self.audio_cache:
            return {
                "success": True,
                "audio_data": self.audio_cache[cache_key],
                "text": text,
                "voice": voice,
                "provider": "cache"
            }
        
        # Estrategia de fallback GRATUITA
        providers = []
        
        if quality == "high" and self.xttts:
            providers.append(("xttts", self._speak_xttts))
        
        providers.extend([
            ("tortoise", self._speak_tortoise),
            ("bark", self._speak_bark),
            ("mary", self._speak_mary)
        ])
        
        # Intentar cada proveedor
        for provider_name, provider_func in providers:
            try:
                result = await provider_func(text, voice)
                if result["success"]:
                    # Guardar en caché
                    self.audio_cache[cache_key] = result["audio_data"]
                    result["provider"] = provider_name
                    return result
            except Exception as e:
                print(f"⚠️ Error con {provider_name}: {e}")
                continue
        
        return {
            "success": False,
            "error": "Todos los proveedores TTS gratuitos fallaron",
            "text": text
        }
    
    async def _speak_xttts(self, text: str, voice: Optional[str] = None) -> Dict[str, Any]:
        """Usar XTTTS (Coqui) para TTS de máxima calidad GRATUITO"""
        if not self.xttts:
            raise Exception("XTTTS no inicializado")
        
        try:
            # Generar audio con XTTTS
            audio_data = self.xttts.tts(text)
            
            # Convertir a bytes
            import soundfile as sf
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                sf.write(temp_file.name, audio_data, 22050)
                with open(temp_file.name, 'rb') as f:
                    audio_bytes = f.read()
                os.unlink(temp_file.name)
            
            return {
                "success": True,
                "audio_data": audio_bytes,
                "text": text,
                "voice": voice or "xttts_default"
            }
        except Exception as e:
            raise Exception(f"Error con XTTTS: {e}")
    
    async def _speak_tortoise(self, text: str, voice: Optional[str] = None) -> Dict[str, Any]:
        """Usar Tortoise TTS como backup GRATUITO"""
        if not self.tortoise_tts:
            raise Exception("Tortoise TTS no inicializado")
        
        try:
            # Generar audio con Tortoise TTS
            audio_data = self.tortoise_tts.tts_with_preset(
                text, 
                voice_samples=None,  # Usar voz por defecto
                conditioning_latents=None,
                preset='fast'
            )
            
            # Convertir a bytes
            import soundfile as sf
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                sf.write(temp_file.name, audio_data, 24000)
                with open(temp_file.name, 'rb') as f:
                    audio_bytes = f.read()
                os.unlink(temp_file.name)
            
            return {
                "success": True,
                "audio_data": audio_bytes,
                "text": text,
                "voice": voice or "tortoise_default"
            }
        except Exception as e:
            raise Exception(f"Error con Tortoise TTS: {e}")
    
    async def _speak_bark(self, text: str, voice: Optional[str] = None) -> Dict[str, Any]:
        """Usar Bark TTS como emergencia GRATUITO"""
        if not self.bark_tts:
            raise Exception("Bark TTS no inicializado")
        
        try:
            from bark import SAMPLE_RATE, generate_audio, preload_models
            
            # Generar audio con Bark TTS
            audio_data = generate_audio(text)
            
            # Convertir a bytes
            import soundfile as sf
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                sf.write(temp_file.name, audio_data, SAMPLE_RATE)
                with open(temp_file.name, 'rb') as f:
                    audio_bytes = f.read()
                os.unlink(temp_file.name)
            
            return {
                "success": True,
                "audio_data": audio_bytes,
                "text": text,
                "voice": voice or "bark_default"
            }
        except Exception as e:
            raise Exception(f"Error con Bark TTS: {e}")
    
    async def _speak_mary(self, text: str, voice: Optional[str] = None) -> Dict[str, Any]:
        """Usar MaryTTS como alternativa GRATUITO"""
        if not self.mary_tts:
            raise Exception("MaryTTS no inicializado")
        
        try:
            # Generar audio con MaryTTS
            audio_data = self.mary_tts.speak(text)
            
            # Convertir a bytes
            import soundfile as sf
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                sf.write(temp_file.name, audio_data, 16000)
                with open(temp_file.name, 'rb') as f:
                    audio_bytes = f.read()
                os.unlink(temp_file.name)
            
            return {
                "success": True,
                "audio_data": audio_bytes,
                "text": text,
                "voice": voice or "mary_default"
            }
        except Exception as e:
            raise Exception(f"Error con MaryTTS: {e}")
    
    async def speak_async(self, text: str, voice: Optional[str] = None, 
                         callback=None, quality: str = "high"):
        """Hablar texto de forma asíncrona"""
        def _speak():
            try:
                self.is_speaking = True
                result = asyncio.run(self.speak_text(text, voice, quality))
                self.is_speaking = False
                
                if callback:
                    callback(result)
            except Exception as e:
                self.is_speaking = False
                if callback:
                    callback({"success": False, "error": str(e)})
        
        thread = threading.Thread(target=_speak)
        thread.daemon = True
        thread.start()
    
    def stop_speaking(self):
        """Detener habla actual"""
        self.is_speaking = False
    
    def get_available_voices(self) -> Dict[str, List[str]]:
        """Obtener voces disponibles por proveedor GRATUITO"""
        voices = {
            "xttts": ["xttts_default", "xttts_multilingual"],
            "tortoise": ["tortoise_default", "tortoise_fast", "tortoise_standard"],
            "bark": ["bark_default", "bark_expressive"],
            "mary": ["mary_default", "mary_spanish", "mary_english"]
        }
        return voices
    
    def set_voice_properties(self, rate: int = 150, volume: float = 0.8):
        """Configurar propiedades de voz"""
        # Implementar configuración de propiedades
        pass
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del caché"""
        return {
            "cache_size": len(self.audio_cache),
            "cache_keys": list(self.audio_cache.keys())
        }
```

### **4. Sistema de Interrupción Dinámica**

```python
# backend/app/ai/voice/interruption_manager.py
import threading
import time
from typing import Dict, Any, Optional
from enum import Enum

class InterruptionLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class InterruptionManager:
    """Gestor de interrupciones dinámicas"""
    
    def __init__(self):
        self.is_speaking = False
        self.is_listening = False
        self.interruption_level = InterruptionLevel.NONE
        self.interruption_queue = []
        self.lock = threading.Lock()
    
    def detect_interruption(self, audio_data: bytes, current_speaker: str) -> Dict[str, Any]:
        """Detectar interrupción en audio"""
        try:
            # Análisis básico de audio para detectar interrupciones
            interruption_level = self._analyze_audio_interruption(audio_data)
            
            if interruption_level != InterruptionLevel.NONE:
                return {
                    "interrupted": True,
                    "level": interruption_level.value,
                    "current_speaker": current_speaker,
                    "timestamp": time.time(),
                    "action": self._get_interruption_action(interruption_level)
                }
            
            return {
                "interrupted": False,
                "level": "none",
                "current_speaker": current_speaker,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "interrupted": False,
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _analyze_audio_interruption(self, audio_data: bytes) -> InterruptionLevel:
        """Analizar audio para detectar interrupciones"""
        # Implementación simplificada
        # En producción, usar análisis más sofisticado
        
        if len(audio_data) < 1000:  # Audio muy corto
            return InterruptionLevel.LOW
        
        # Análisis de volumen (simplificado)
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        volume = np.mean(np.abs(audio_array))
        
        if volume > 0.8:  # Volumen alto
            return InterruptionLevel.HIGH
        elif volume > 0.5:  # Volumen medio
            return InterruptionLevel.MEDIUM
        elif volume > 0.2:  # Volumen bajo
            return InterruptionLevel.LOW
        
        return InterruptionLevel.NONE
    
    def _get_interruption_action(self, level: InterruptionLevel) -> str:
        """Obtener acción para nivel de interrupción"""
        actions = {
            InterruptionLevel.LOW: "continue",
            InterruptionLevel.MEDIUM: "pause",
            InterruptionLevel.HIGH: "stop",
            InterruptionLevel.CRITICAL: "immediate_stop"
        }
        return actions.get(level, "continue")
    
    def handle_interruption(self, interruption_data: Dict[str, Any]) -> Dict[str, Any]:
        """Manejar interrupción detectada"""
        with self.lock:
            if interruption_data["interrupted"]:
                level = InterruptionLevel(interruption_data["level"])
                action = interruption_data["action"]
                
                # Agregar a cola de interrupciones
                self.interruption_queue.append(interruption_data)
                
                # Ejecutar acción
                if action == "immediate_stop":
                    self._immediate_stop()
                elif action == "stop":
                    self._stop_speaking()
                elif action == "pause":
                    self._pause_speaking()
                
                return {
                    "handled": True,
                    "action": action,
                    "queue_length": len(self.interruption_queue)
                }
            
            return {
                "handled": False,
                "reason": "no_interruption"
            }
    
    def _immediate_stop(self):
        """Detener inmediatamente"""
        self.is_speaking = False
        self.is_listening = False
    
    def _stop_speaking(self):
        """Detener habla"""
        self.is_speaking = False
    
    def _pause_speaking(self):
        """Pausar habla"""
        # Implementar pausa
        pass
    
    def resume_speaking(self):
        """Reanudar habla"""
        if self.interruption_queue:
            self.interruption_queue.pop(0)
        self.is_speaking = True
    
    def get_interruption_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de interrupciones"""
        return {
            "total_interruptions": len(self.interruption_queue),
            "is_speaking": self.is_speaking,
            "is_listening": self.is_listening,
            "current_level": self.interruption_level.value
        }
```

### **5. API REST para Voz**

```python
# backend/app/api/voice.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..ai.voice.stt_service import STTService
from ..ai.voice.tts_service import TTSService
from ..ai.voice.interruption_manager import InterruptionManager
import io

router = APIRouter(prefix="/api/voice", tags=["voice"])

class STTRequest(BaseModel):
    language: str = "es"
    model: str = "base"

class STTResponse(BaseModel):
    text: str
    language: str
    confidence: float
    success: bool
    error: Optional[str] = None

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    rate: int = 150
    volume: float = 0.8

class TTSResponse(BaseModel):
    success: bool
    audio_data: Optional[bytes] = None
    error: Optional[str] = None

# Instancias de servicios
stt_service = STTService()
tts_service = TTSService()
interruption_manager = InterruptionManager()

@router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    file: UploadFile = File(...),
    language: str = "es"
):
    """Convertir audio a texto"""
    try:
        # Leer audio
        audio_data = await file.read()
        
        # Transcribir
        result = stt_service.transcribe_audio(audio_data, language)
        
        return STTResponse(
            text=result["text"],
            language=result["language"],
            confidence=result["confidence"],
            success=True
        )
    except Exception as e:
        return STTResponse(
            text="",
            language=language,
            confidence=0.0,
            success=False,
            error=str(e)
        )

@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """Convertir texto a voz"""
    try:
        # Configurar propiedades de voz
        tts_service.set_voice_properties(request.rate, request.volume)
        
        # Generar audio
        result = tts_service.speak_text(request.text, request.voice)
        
        if result["success"]:
            return TTSResponse(
                success=True,
                audio_data=result["audio_data"]
            )
        else:
            return TTSResponse(
                success=False,
                error=result["error"]
            )
    except Exception as e:
        return TTSResponse(
            success=False,
            error=str(e)
        )

@router.post("/interrupt")
async def handle_interruption(audio_data: bytes, current_speaker: str):
    """Manejar interrupción de audio"""
    try:
        # Detectar interrupción
        interruption_data = interruption_manager.detect_interruption(
            audio_data, current_speaker
        )
        
        # Manejar interrupción
        result = interruption_manager.handle_interruption(interruption_data)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voices")
async def get_available_voices():
    """Obtener voces disponibles"""
    try:
        voices = tts_service.get_available_voices()
        return {"voices": voices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_voice_stats():
    """Obtener estadísticas del sistema de voz"""
    try:
        interruption_stats = interruption_manager.get_interruption_stats()
        return {
            "interruption_stats": interruption_stats,
            "tts_available": tts_service.engine is not None,
            "stt_available": stt_service.model is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### **6. Frontend: Componente de Voz**

```typescript
// src/components/VoiceInterface.tsx
import React, { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Mic, MicOff, Volume2, VolumeX } from 'lucide-react'

interface VoiceInterfaceProps {
  onTranscript: (text: string) => void
  onAudio: (audioData: Blob) => void
  disabled?: boolean
}

export const VoiceInterface: React.FC<VoiceInterfaceProps> = ({
  onTranscript,
  onAudio,
  disabled = false
}) => {
  const [isRecording, setIsRecording] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)
  const [transcript, setTranscript] = useState('')
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const animationRef = useRef<number>()

  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      })
      
      streamRef.current = stream
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }
      
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' })
        onAudio(audioBlob)
        audioChunksRef.current = []
      }
      
      mediaRecorder.start(100) // Chunks cada 100ms
      setIsRecording(true)
      setIsListening(true)
      
      // Monitorear nivel de audio
      monitorAudioLevel(stream)
      
    } catch (error) {
      console.error('Error accediendo al micrófono:', error)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      setIsListening(false)
      
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }

  const monitorAudioLevel = (stream: MediaStream) => {
    const audioContext = new AudioContext()
    const analyser = audioContext.createAnalyser()
    const microphone = audioContext.createMediaStreamSource(stream)
    const dataArray = new Uint8Array(analyser.frequencyBinCount)
    
    microphone.connect(analyser)
    analyser.fftSize = 256
    
    const updateLevel = () => {
      if (isListening) {
        analyser.getByteFrequencyData(dataArray)
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length
        setAudioLevel(average)
        animationRef.current = requestAnimationFrame(updateLevel)
      }
    }
    
    updateLevel()
  }

  const handleToggleRecording = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  return (
    <div className="voice-interface">
      <div className="flex items-center space-x-4">
        {/* Botón de grabación */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleToggleRecording}
          disabled={disabled}
          className={`p-4 rounded-full transition-colors ${
            isRecording
              ? 'bg-red-500 text-white hover:bg-red-600'
              : 'bg-blue-500 text-white hover:bg-blue-600'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {isRecording ? <MicOff size={24} /> : <Mic size={24} />}
        </motion.button>

        {/* Indicador de nivel de audio */}
        {isListening && (
          <div className="flex items-center space-x-2">
            <Volume2 size={16} className="text-gray-600" />
            <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-green-500 rounded-full"
                style={{ width: `${(audioLevel / 255) * 100}%` }}
                transition={{ duration: 0.1 }}
              />
            </div>
          </div>
        )}

        {/* Estado de grabación */}
        <div className="text-sm text-gray-600">
          {isRecording ? 'Grabando...' : 'Presiona para grabar'}
        </div>
      </div>

      {/* Transcript en tiempo real */}
      {transcript && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 p-3 bg-gray-100 rounded-lg"
        >
          <p className="text-sm text-gray-700">{transcript}</p>
        </motion.div>
      )}
    </div>
  )
}
```

## 🧪 Testing del Sistema de Voz

### **1. Tests de STT/TTS**

```python
# backend/tests/test_voice.py
import pytest
from app.ai.voice.stt_service import STTService
from app.ai.voice.tts_service import TTSService
from app.ai.voice.interruption_manager import InterruptionManager

def test_stt_service():
    """Test que el servicio STT funcione"""
    stt_service = STTService()
    
    # Test con audio de prueba
    test_audio = b"fake_audio_data"
    result = stt_service.transcribe_audio(test_audio, "es")
    
    assert "text" in result
    assert "language" in result
    assert "confidence" in result

def test_tts_service():
    """Test que el servicio TTS funcione"""
    tts_service = TTSService()
    
    # Test generación de audio
    result = tts_service.speak_text("Hello world")
    
    assert result["success"] is True
    assert "audio_data" in result

def test_interruption_manager():
    """Test que el gestor de interrupciones funcione"""
    manager = InterruptionManager()
    
    # Test detección de interrupción
    test_audio = b"fake_audio_data"
    result = manager.detect_interruption(test_audio, "user")
    
    assert "interrupted" in result
    assert "level" in result
    assert "current_speaker" in result
```

### **2. Tests de API**

```python
# backend/tests/test_voice_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_stt_endpoint():
    """Test endpoint de STT"""
    # Crear archivo de audio de prueba
    test_audio = b"fake_audio_data"
    
    response = client.post(
        "/api/voice/stt",
        files={"file": ("test.wav", test_audio, "audio/wav")},
        params={"language": "es"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert "confidence" in data

def test_tts_endpoint():
    """Test endpoint de TTS"""
    response = client.post(
        "/api/voice/tts",
        json={"text": "Hello world", "voice": "default"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "success" in data

def test_voices_endpoint():
    """Test endpoint de voces disponibles"""
    response = client.get("/api/voice/voices")
    
    assert response.status_code == 200
    data = response.json()
    assert "voices" in data
```

## 💰 Configuración y Costos

### **🔧 Variables de Entorno**

```bash
# .env
# ElevenLabs (Recomendado para máxima calidad)
ELEVENLABS_API_KEY=your_api_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Google Cloud (Alternativa comercial)
GOOGLE_CLOUD_API_KEY=your_api_key_here
GOOGLE_CLOUD_PROJECT_ID=your_project_id

# Azure (Alternativa comercial)
AZURE_SPEECH_KEY=your_speech_key
AZURE_SPEECH_REGION=your_region

# Configuración de calidad
TTS_QUALITY=high  # high, medium, low
TTS_CACHE_ENABLED=true
TTS_CACHE_SIZE=100
```

### **📊 Análisis de Costos 2025 - 100% GRATUITO**

| **Proveedor** | **Costo** | **Calidad** | **Uso Recomendado** |
|---------------|-----------|-------------|---------------------|
| **XTTTS (Coqui)** | Gratis | ⭐⭐⭐⭐⭐ | Producción principal |
| **Tortoise TTS** | Gratis | ⭐⭐⭐⭐ | Backup local |
| **Bark TTS** | Gratis | ⭐⭐⭐⭐ | Emergencia expresiva |
| **MaryTTS** | Gratis | ⭐⭐⭐ | Alternativa estable |
| **Vosk (STT)** | Gratis | ⭐⭐⭐⭐ | STT offline |
| **Whisper (STT)** | Gratis | ⭐⭐⭐⭐⭐ | STT online |

### **💡 Estrategia de Costos 100% Gratuita**

```python
# Estrategia de costos para 1000 usuarios/mes:
# 1. XTTTS: $0 (máxima calidad, gratis)
# 2. Tortoise TTS: $0 (backup, gratis)
# 3. Bark TTS: $0 (emergencia, gratis)
# 4. Vosk: $0 (STT offline, gratis)
# 5. Whisper: $0 (STT online, gratis)
# 6. Total: $0/mes para 1000 usuarios

# Comparación con alternativas comerciales:
# ElevenLabs: $22/mes (calidad similar)
# Google TTS: $40/mes (calidad similar)
# Azure TTS: $40/mes (calidad similar)
# Nuestra estrategia: $0/mes (calidad comparable)
```

## 📊 Métricas de Éxito

### **🎯 Objetivos Técnicos**
- **Latencia STT**: < 1s (Whisper optimizado)
- **Latencia TTS**: < 2s (ElevenLabs) / < 5s (Open Source)
- **Calidad de Audio**: > 95% claridad (ElevenLabs)
- **Detección de Interrupciones**: > 90% precisión
- **Memoria**: < 512MB para audio
- **Costo**: < $0.50 por usuario/mes

### **🎯 Objetivos de Funcionalidad**
- **STT/TTS**: Funcionando correctamente
- **Interrupciones**: Detección natural como persona real
- **Streaming**: Audio en tiempo real
- **Integración**: Perfecta con sistema de chat
- **Voz Humana**: Sonido natural y expresivo
- **Testing**: > 90% cobertura de código

## ✅ Criterios de Éxito

### **📋 Checklist de Validación**
- [ ] **STT con Whisper** funcionando
- [ ] **TTS** con múltiples voces
- [ ] **Sistema de interrupciones** operativo
- [ ] **API REST** documentada
- [ ] **Frontend de voz** funcional
- [ ] **Testing completo** pasando
- [ ] **Rendimiento** dentro de métricas objetivo
- [ ] **Preparación** para siguiente fase

### **🎯 Entregables de esta Fase**
- [ ] **Sistema de voz** completamente funcional
- [ ] **STT/TTS** operativo
- [ ] **Interrupciones dinámicas** implementadas
- [ ] **API de voz** robusta
- [ ] **Frontend de voz** intuitivo
- [ ] **Testing suite** completa
- [ ] **Documentación** técnica
- [ ] **Preparación** para sistema de visión

## 🚀 Siguiente Fase

Una vez completada esta fase, continuar con [**Fase 7: Sistema de Visión**](./07-vision.md) (Opcional)

### **📋 Preparación para Fase 7**
- [ ] Sistema de voz funcionando
- [ ] STT/TTS operativo
- [ ] Interrupciones dinámicas
- [ ] Testing completo
- [ ] Documentación actualizada

---

**🎉 ¡Con esta fase tendrás un asistente que suena verdaderamente humano!**

### **🎯 Por qué el Sistema de Voz es FUNDAMENTAL**

#### **✅ Experiencia Humana Real**
- **Conversación Natural**: Como hablar con una persona real
- **Voz Expresiva**: ElevenLabs proporciona la voz más humana del mercado
- **Interrupciones Inteligentes**: Gestión natural como persona real
- **Emociones en la Voz**: Tono, ritmo y expresividad humana

#### **✅ Ventaja Competitiva**
- **Diferenciación**: Pocos asistentes tienen voz verdaderamente humana
- **Adopción**: Los usuarios prefieren hablar que escribir
- **Accesibilidad**: Inclusivo para usuarios con discapacidades
- **Productividad**: Más rápido que escribir

#### **✅ Estrategia Comercial Sólida**
- **ElevenLabs**: Máxima calidad a precio razonable ($22/mes)
- **Backup Open Source**: Sin dependencias externas
- **Escalabilidad**: Funciona para 1-1000+ usuarios
- **Sin Problemas Legales**: Licencias claras y comerciales

### **🚀 Recomendación Final - 100% GRATUITA**

**Usa XTTTS (Coqui) como principal + Tortoise TTS como backup + Vosk/Whisper para STT**

Esta combinación te dará:
- **Voz humana de alta calidad** (XTTTS - gratis)
- **Respaldo sin costos** (Tortoise TTS - gratis)
- **STT offline/online** (Vosk + Whisper - gratis)
- **Control total** (100% Open Source)
- **Costo cero** ($0/mes vs $22-40+ de competidores)

#### **✅ Ventajas de la Estrategia Gratuita**
- **Sin dependencias comerciales**: Control total del código
- **Escalabilidad ilimitada**: Sin costos por usuario
- **Calidad comparable**: XTTTS rivaliza con ElevenLabs
- **Flexibilidad total**: Personalización completa
- **Sin restricciones**: Licencias permisivas (MIT, MPL-2.0, Apache 2.0)

*Recuerda: La voz es lo que hace que tu asistente sea verdaderamente como una persona. Con esta estrategia 100% gratuita, tendrás la mejor calidad sin costos.* 🚀
