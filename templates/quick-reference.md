# ⚡ Quick Reference - Comandos Esenciales

## 🚀 Inicio Rápido

### **1. Configuración del Proyecto**
```bash
# Clonar repositorio
git clone <tu-repo>
cd asistente-ia-universal

# Configurar entorno Python
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-finetuning.txt
```

### **2. Configuración del Backend**
```bash
# Configurar Ollama
ollama pull mistral:7b
ollama pull phi3:medium

# Iniciar backend
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### **3. Configuración del Frontend**
```bash
# Instalar dependencias
cd frontend
npm install

# Iniciar desarrollo
npm run dev

# Build para producción
npm run build
```

## 🔧 Comandos de Desarrollo

### **Backend (Python)**
```bash
# Ejecutar tests
pytest
pytest --cov=app tests/

# Formatear código
black app/
flake8 app/

# Type checking
mypy app/

# Linting
ruff check app/
ruff format app/
```

### **Frontend (React/TypeScript)**
```bash
# Ejecutar tests
npm test
npm run test:coverage

# Linting
npm run lint
npm run lint:fix

# Type checking
npm run type-check

# Build
npm run build
npm run build:analyze
```

### **AI/ML**
```bash
# Fine-tuning
python -m app.core.lora_finetuning
python -m app.core.qlora_finetuning

# Evaluación
python -m app.core.evaluate_model

# Optimización
python -m app.core.optimize_model
```

## 🐳 Docker

### **Desarrollo**
```bash
# Build imagen
docker build -t asistente-ia .

# Ejecutar contenedor
docker run -p 8000:8000 -p 3000:3000 asistente-ia

# Con volúmenes
docker run -v $(pwd):/app -p 8000:8000 -p 3000:3000 asistente-ia
```

### **Producción**
```bash
# Build para producción
docker build -f Dockerfile.prod -t asistente-ia:prod .

# Ejecutar en producción
docker run -d --name asistente-ia-prod -p 8000:8000 asistente-ia:prod
```

## 📊 Monitoreo y Debugging

### **Logs**
```bash
# Ver logs del backend
tail -f logs/backend.log

# Ver logs del frontend
tail -f logs/frontend.log

# Ver logs de AI
tail -f logs/ai.log
```

### **Métricas**
```bash
# Monitoreo de recursos
python -m app.utils.resource_monitor

# Métricas de rendimiento
python -m app.utils.performance_monitor

# Análisis de memoria
python -m app.utils.memory_analyzer
```

### **Debugging**
```bash
# Debug del backend
python -m debugpy --listen 5678 --wait-for-client app/main.py

# Debug del frontend
npm run debug

# Profiling
python -m cProfile -o profile.stats app/main.py
```

## 🧪 Testing

### **Tests Unitarios**
```bash
# Backend
pytest tests/unit/
pytest tests/unit/ -v --cov=app

# Frontend
npm run test:unit
npm run test:unit -- --coverage
```

### **Tests de Integración**
```bash
# Backend
pytest tests/integration/
pytest tests/integration/ -v

# Frontend
npm run test:integration
npm run test:e2e
```

### **Tests de Rendimiento**
```bash
# Backend
pytest tests/performance/ -v
python -m app.tests.performance.benchmark

# Frontend
npm run test:performance
npm run lighthouse
```

## 🔄 CI/CD

### **GitHub Actions**
```bash
# Ejecutar workflow localmente
act -j test
act -j build
act -j deploy

# Verificar workflow
act --dry-run
```

### **Docker Compose**
```bash
# Desarrollo
docker-compose up -d

# Producción
docker-compose -f docker-compose.prod.yml up -d

# Logs
docker-compose logs -f
```

## 🎯 Fine-tuning

### **LoRA**
```bash
# Entrenar con LoRA
python -m app.core.lora_finetuning --model mistral:7b --data data/training/

# Evaluar modelo
python -m app.core.evaluate_model --model personalized_model/

# Desplegar modelo
python -m app.core.deploy_model --model personalized_model/
```

### **QLoRA**
```bash
# Entrenar con QLoRA
python -m app.core.qlora_finetuning --model mistral:7b --data data/training/

# Cuantización
python -m app.core.quantize_model --model mistral:7b --quantization 4bit
```

## 📱 Desarrollo Multiplataforma

### **Windows**
```bash
# PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\setup-windows.ps1
```

### **Linux**
```bash
# Bash
chmod +x scripts/setup-linux.sh
./scripts/setup-linux.sh
```

### **macOS**
```bash
# Bash
chmod +x scripts/setup-macos.sh
./scripts/setup-macos.sh
```

## 🚀 Deploy

### **Desarrollo**
```bash
# Iniciar todo
npm run dev:all
python -m app.main

# Con Docker
docker-compose up -d
```

### **Producción**
```bash
# Build completo
npm run build:all
python -m app.main --env production

# Con Docker
docker-compose -f docker-compose.prod.yml up -d
```

## 🔧 Troubleshooting

### **Problemas Comunes**
```bash
# Puerto ocupado
lsof -i :8000
kill -9 $(lsof -t -i:8000)

# Memoria insuficiente
python -m app.utils.optimize_memory

# Modelo no carga
ollama pull mistral:7b
ollama list
```

### **Logs de Error**
```bash
# Backend
grep -i error logs/backend.log
grep -i exception logs/backend.log

# Frontend
grep -i error logs/frontend.log
grep -i warning logs/frontend.log
```

### **Performance**
```bash
# CPU alto
top -p $(pgrep -f "python.*app.main")
htop

# Memoria alta
free -h
ps aux --sort=-%mem | head
```

## 📚 Recursos Útiles

### **Documentación**
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Docs](https://react.dev/)
- [LangChain Docs](https://python.langchain.com/)
- [Ollama Docs](https://ollama.ai/)

### **Comunidades**
- [FastAPI Discord](https://discord.gg/VQjSZaeJmf)
- [React Community](https://reactjs.org/community/support.html)
- [LangChain Discord](https://discord.gg/langchain)

### **Herramientas**
- [Postman](https://www.postman.com/) - Testing API
- [Insomnia](https://insomnia.rest/) - API Client
- [Wireshark](https://www.wireshark.org/) - Network Analysis
- [htop](https://htop.dev/) - System Monitor

---

**🎉 ¡Con estos comandos tendrás todo lo necesario para desarrollar tu asistente de IA!**

*Recuerda: Mantén este quick reference a mano durante el desarrollo.* 🚀
