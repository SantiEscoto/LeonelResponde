# Guía de instalación y ejecución en Jetson Orin Nano

Esta guía explica cómo preparar el entorno, instalar dependencias y ejecutar el asistente offline en Jetson Orin Nano, con foco en rendimiento y en mantener el proyecto mínimo indispensable.

## Requisitos

- JetPack 6.1 o 6.2 instalado (incluye CUDA 12.x)
- Python 3.11 (preferible)
- 8 GB de RAM recomendado (4 GB funciona con modelos pequeños)
- Acceso a Internet inicial para instalar dependencias y descargar modelos (luego funciona offline)

## 1. Actualizar sistema y herramientas

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip build-essential ffmpeg portaudio19-dev git
```

## 2. Crear entorno virtual

```bash
cd /path/a/LeonelResponde
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## 3. Instalar dependencias para Jetson

Usa el archivo de dependencias optimizado para Jetson:

```bash
pip install -r Assistant/requirements-jetson.txt
```

Notas:
- Si usas Piper TTS con GPU, instala `onnxruntime-gpu` compatible con tu JetPack. Si falla, usa `onnxruntime` CPU.
- Para LLM acelerados, revisa TensorRT-LLM en Jetson AGX/Orin. En Orin Nano, prioriza modelos pequeños/quantizados.

## 4. Descargar modelos offline

### Vosk (STT español offline, ligero)

```bash
mkdir -p models/voice
cd models/voice
wget https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
unzip vosk-model-small-es-0.42.zip && rm vosk-model-small-es-0.42.zip
```

Estructura esperada:

```
models/
  voice/
    vosk-model-small-es-0.42/
```

> Los modelos en `models/voice/` están ignorados por git; se descargan localmente.

### Piper (opcional, TTS español)

Descarga una voz española desde el repositorio de voces de Piper (es_ES, es_AR, es_MX) y coloca los archivos `.onnx` y `.onnx.json` en una carpeta accesible. Puedes configurar la ruta en el archivo de configuración del asistente.

## 5. Configuración mínima

- Las rutas de modelos por defecto apuntan a `Assistant/data/models`. Para Vosk/Piper, se usan rutas dedicadas bajo `models/voice/` (externo al paquete Assistant).
- Variables `.env`: si necesitas valores locales, crea `Assistant/.env` (no se versiona).

## 6. Ejecutar el backend

```bash
source .venv/bin/activate
python Assistant/main.py
```

Por defecto expone la API en `http://0.0.0.0:8000`.

### Endpoints útiles

- Salud: `GET /health`
- Estado: `GET /status`
- Métricas: `GET /metrics` (formato Prometheus, `Content-Type: text/plain; version=0.0.4; charset=utf-8`)

## 7. Verificación rápida

```bash
curl -s http://localhost:8000/status | jq
curl -s -H 'Accept: text/plain' http://localhost:8000/metrics | head -n 20
```

Si usas STT/TTS, valida que las rutas a modelos existen y que el dispositivo de audio (`portaudio`) reconoce tu entrada/salida.

## 8. Consejos de rendimiento

- STT: usa Vosk `small` para baja latencia en Orin Nano.
- TTS: Piper con `onnxruntime` CPU es estable; con GPU mejora latencia si `onnxruntime-gpu` es compatible con tu JetPack.
- LLM: emplea modelos pequeños/quantizados (por ejemplo vía `llama.cpp` o motores ligeros). Para TensorRT-LLM, considera construir motores en un host más potente.

## 9. Problemas comunes

- `onnxruntime-gpu` no carga: verifica versión de CUDA/JetPack; usa `onnxruntime` CPU como fallback.
- Latencia alta en Whisper: en Orin Nano, prefiere Vosk para STT en tiempo real.
- Audio no funciona: revisa `arecord -l`/`aplay -l` y permisos de `portaudio`.

## 10. Modo offline

Tras instalar dependencias y descargar modelos, el asistente funciona completamente offline. No se usan APIs en la nube.