# Compy (Jetson) — Bootstrap rápido (sin subir modelos pesados a GitHub)

Este repo **NO** versiona modelos grandes (por ejemplo `*.gguf`) ni entornos (`venv/`, `.venv/`).
La idea es: **código y configuración en GitHub**, y **assets pesados se descargan localmente**.

## 1) Clonar

```bash
git clone https://github.com/SantiEscoto/LeonelResponde.git
cd LeonelResponde
# Si necesitas la rama de Jetson/optimización:
git checkout feat/langchain-tests-and-dev-config
```

## 2) Python venv + dependencias

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel setuptools

# Dependencias base (ajusta si tu proyecto usa otro archivo)
python -m pip install -r Assistant/requirements.txt

# Si estás en Jetson y existe requirements específico:
# python -m pip install -r Assistant/requirements-jetson.txt
```

## 3) Descargar el modelo GGUF (NO va en Git)

El proyecto espera el modelo en (puedes cambiar la ruta si ajustas config):

- `Assistant/models/mistral-7b-instruct-v0.1.Q4_K_M.gguf`

### Opción A — `huggingface-cli` (recomendado)

```bash
python -m pip install -U "huggingface_hub[cli]"

mkdir -p Assistant/models

# Descarga el archivo GGUF exacto al directorio de modelos
# Nota: el repo y el filename pueden variar según el proveedor; si falla, busca el mismo filename en HuggingFace.
huggingface-cli download \
  TheBloke/Mistral-7B-Instruct-v0.1-GGUF \
  mistral-7b-instruct-v0.1.Q4_K_M.gguf \
  --local-dir Assistant/models \
  --local-dir-use-symlinks False
```

### Opción B — desde `compy_models/` (si ya lo tienes descargado)

```bash
mkdir -p Assistant/models
cp -v /home/santi/compy_models/mistral-7b-instruct-v0.1.Q4_K_M.gguf Assistant/models/
```

## 4) Verificación rápida

```bash
ls -lh Assistant/models/*.gguf
python -c "import sys; print('python ok', sys.version)"
```

## 5) Limpieza (cuando falte espacio)

```bash
# eliminar entorno y caches regenerables
rm -rf .venv __pycache__ .pytest_cache .mypy_cache .ruff_cache

# si hay caches de modelos/índices generados, se pueden regenerar
rm -f Assistant/faiss_index.bin 2>/dev/null || true
```
