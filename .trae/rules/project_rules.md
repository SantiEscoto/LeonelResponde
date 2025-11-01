# Project Rules Guide for Assistant Multimodal Offline

## 1. Framework and Dependencies
- Backend: Python 3.11+
- Frontend: React 18 + TailwindCSS 3
- Packaging: Tauri for native offline app
- Key Python libraries:
  - vosk (STT offline)
  - sounddevice (audio capture)
  - numpy
  - xTTS-v2 (TTS offline)
  - TensorRT + PyTorch (LLM acceleration)
  - langchain (memory management)
  - easyocr, face_recognition, yolo (vision)
  - FAISS or similar for vector DB

## 2. Testing Framework
- Use `pytest` for Python modules
- Include unit tests for:
  - STT and TTS
  - LLM query and memory
  - Vision detection functions
- Frontend tests: Jest + React Testing Library

## 3. Code Standards
- Python: `snake_case` for functions/variables, `PascalCase` for classes
- Type hints required for all functions and methods
- Docstrings for all classes and methods
- Modular structure: backend modules separated by function (voice, vision, llm, events, utils)
- Frontend: Components modularized, reusable, with Tailwind classes
- Maintain consistent file/folder structure as in `CONTEXT.md`

## 4. APIs and Libraries to Avoid
- No cloud APIs; the assistant must run fully offline
- Avoid deprecated or experimental packages

## 5. Performance Guidelines
- Optimize for Jetson Nano / Raspberry Pi
- Minimize CPU/GPU load
- Avoid blocking loops; prefer async/event-driven patterns