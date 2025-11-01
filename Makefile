# LeonelResponde - Voice Dev Workflows

HOST ?= localhost
HTTP_PORT ?= 8000
WS_PORT ?= 8765
SERVICE := assistant-dev

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  voice-env                  Build voice-ready Docker image (Python 3.11)"
	@echo "  voice-env-local            Create local venv and install voice deps (Py3.9)"
	@echo "  docker-build               Build Docker image"
	@echo "  docker-shell               Open interactive shell in container"
	@echo "  docker-voice-server        Run HTTP voice server"
	@echo "  docker-voice-ws-server     Run WebSocket voice server (assistant-dev)"
	@echo "  docker-voice-ws-up         Start dedicated voice-ws service (port $(WS_PORT))"
	@echo "  docker-voice-ws-logs       Tail logs for voice-ws service"
	@echo "  docker-voice-ws-down       Stop and remove voice-ws service"
	@echo "  backend-up                 Start assistant-dev backend (build if needed)"
	@echo "  backend-logs               Tail logs for assistant-dev backend"
	@echo "  backend-down               Stop and remove assistant-dev backend"
	@echo "  backend-restart            Restart assistant-dev backend"
	@echo "  backend-status             GET /status from assistant-dev backend"
	@echo "  backend-health             GET /health from assistant-dev backend"
	@echo "  voice-status               GET /status from HTTP voice server"
	@echo "  voice-health               GET /health from HTTP voice server"
	@echo "  tts-demo                   Generate WAV via HTTP /tts"
	@echo "  ws-tts-demo                Generate WAV via WS /ws/tts (HOST=$(HOST) PORT=$(WS_PORT))"
	@echo "  ws-stt-demo                Transcribe WAV via WS /ws/stt (HOST=$(HOST) PORT=$(WS_PORT))"
	@echo "  ws-stt-demo-binary         Transcribe WAV via WS /ws/stt sending binary chunks"
	@echo "  frontend-dev               Start frontend dev server (Vite)"
	@echo ""
	@echo "Variables: HOST=$(HOST) HTTP_PORT=$(HTTP_PORT) WS_PORT=$(WS_PORT) TEXT='...' OUTPUT=salida.wav INPUT=Assistant/data/voice_samples/ws_tts_16k.wav"

.PHONY: voice-env
voice-env:
	@echo "Construyendo imagen Docker de voz (Python 3.11)..."
	docker compose build
	@echo "Listo. Usa 'make docker-voice-ws-up' para arrancar el servidor WS."

.PHONY: voice-env-local
voice-env-local:
	@echo "Creando entorno virtual local (.venv) y instalando dependencias de voz..."
	@test -d .venv || python3 -m venv .venv
	. .venv/bin/activate && python -m pip install --upgrade pip wheel setuptools
	. .venv/bin/activate && python -m pip install -r Assistant/requirements-voice.txt
	@echo "Entorno local listo. Ejecuta WS: 'DISABLE_COQUI=1 VOSK_MODEL_PATH=./models/voice/vosk-model-small-es-0.42 python Assistant/src/mcp_servers/voice_ws_server.py'"

.PHONY: docker-build
docker-build:
	docker compose build

.PHONY: docker-shell
docker-shell:
	docker compose run --rm $(SERVICE)

.PHONY: docker-voice-server
docker-voice-server:
	docker compose run --rm --service-ports $(SERVICE) python Assistant/src/mcp_servers/voice_server.py

.PHONY: docker-voice-ws-server
docker-voice-ws-server:
	docker compose run --rm --service-ports $(SERVICE) python Assistant/src/mcp_servers/voice_ws_server.py

.PHONY: docker-voice-ws-up
docker-voice-ws-up:
	docker compose up -d voice-ws

.PHONY: docker-voice-ws-logs
docker-voice-ws-logs:
	docker compose logs -f voice-ws

.PHONY: docker-voice-ws-down
docker-voice-ws-down:
	docker compose rm -sf voice-ws

.PHONY: voice-status
voice-status:
	curl -s http://$(HOST):$(HTTP_PORT)/status | jq .

.PHONY: voice-health
voice-health:
	curl -s http://$(HOST):$(HTTP_PORT)/health | jq .

TEXT ?= Hola, ¿cómo estás?
OUTPUT ?= salida.wav
INPUT ?= Assistant/data/voice_samples/ws_tts_16k.wav

.PHONY: tts-demo
tts-demo:
	curl -s -X POST http://$(HOST):$(HTTP_PORT)/tts -H "Content-Type: application/json" -d '{"text":"$(TEXT)"}' | jq -r '.audio_base64' | python3 -c 'import sys,base64; open("$(OUTPUT)","wb").write(base64.b64decode(sys.stdin.read()))' && echo "WAV guardado en $(OUTPUT)"

.PHONY: ws-tts-demo
ws-tts-demo:
	python Assistant/scripts/ws_tts_demo.py --host $(HOST) --port $(WS_PORT) --text "$(TEXT)" --output $(OUTPUT)

.PHONY: ws-stt-demo
ws-stt-demo:
	python Assistant/scripts/ws_stt_demo.py --host $(HOST) --port $(WS_PORT) --input $(INPUT)

.PHONY: ws-stt-demo-binary
ws-stt-demo-binary:
	python Assistant/scripts/ws_stt_demo.py --host $(HOST) --port $(WS_PORT) --input $(INPUT) --binary --use-vad --vad-level 2 --frame-ms 30

.PHONY: frontend-dev
frontend-dev:
	cd frontend && npm run dev

.PHONY: backend-up
backend-up:
	docker compose up -d --build assistant-dev

.PHONY: backend-logs
backend-logs:
	docker compose logs -f assistant-dev

.PHONY: backend-down
backend-down:
	docker compose rm -sf assistant-dev

.PHONY: backend-restart
backend-restart:
	docker compose restart assistant-dev

.PHONY: backend-status
backend-status:
	curl -s http://$(HOST):$(HTTP_PORT)/status | jq .

.PHONY: backend-health
backend-health:
	curl -s http://$(HOST):$(HTTP_PORT)/health | jq .