# Dev container for Leonel Responde (voice-ready)
# Base: Python 3.11 on Debian slim

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QT_QPA_PLATFORM=offscreen

# System packages for audio, WebRTC (PyAV), and build tooling
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ninja-build \
    ffmpeg \
    pkg-config \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    libavdevice-dev \
    libavformat-dev \
    libavfilter-dev \
    libavcodec-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    git curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy requirements first for better build caching
COPY Assistant/requirements.txt /tmp/requirements.txt
COPY Assistant/requirements-voice-docker.txt /tmp/requirements-voice.txt

# Install Python deps (base + voice)
RUN python -m pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    pip install -r /tmp/requirements-voice.txt

# Copy the rest of the project (optional; compose will mount volumes)
COPY . /workspace

# Default command: start interactive shell
CMD ["bash"]