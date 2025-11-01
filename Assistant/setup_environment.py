#!/usr/bin/env python3
"""
🔧 Script de Configuración del Entorno
=====================================

Configura el entorno de desarrollo para el asistente de IA
Implementa las fases faltantes según nuestro plan
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header(title):
    """Imprimir encabezado con estilo"""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print(f"{'='*60}")

def run_command(command, description):
    """Ejecutar comando y mostrar resultado"""
    print(f"\n📋 {description}")
    print(f"💻 Ejecutando: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Completado")
        if result.stdout:
            print(f"📤 Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}")
        print(f"📤 Error: {e.stderr}")
        return False

def create_directory_structure():
    """Crear estructura de directorios necesaria"""
    print_header("Creando Estructura de Directorios")
    
    directories = [
        "src/backend/voice",
        "src/backend/vision", 
        "src/backend/finetuning",
        "src/backend/social",
        "models/voice",
        "models/vision",
        "data/voice_samples",
        "data/vision_samples",
        "logs/voice",
        "logs/vision"
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Creado: {directory}")

def install_dependencies():
    """Instalar dependencias necesarias"""
    print_header("Instalando Dependencias")
    
    # Dependencias base
    base_deps = [
        "pip install --upgrade pip",
        "pip install -r requirements.txt"
    ]
    
    # Dependencias de voz
    voice_deps = [
        "pip install -r requirements-voice.txt"
    ]
    
    # Dependencias de visión
    vision_deps = [
        "pip install -r requirements-vision.txt"
    ]
    
    # Dependencias de fine-tuning
    finetuning_deps = [
        "pip install -r requirements-finetuning.txt"
    ]
    
    # Instalar dependencias base
    for dep in base_deps:
        if not run_command(dep, f"Instalando dependencia: {dep}"):
            print(f"⚠️ Advertencia: Error instalando {dep}")
    
    # Instalar dependencias de voz
    print("\n🎤 Instalando dependencias de voz...")
    for dep in voice_deps:
        if not run_command(dep, f"Instalando dependencia de voz: {dep}"):
            print(f"⚠️ Advertencia: Error instalando {dep}")
    
    # Instalar dependencias de visión
    print("\n👁️ Instalando dependencias de visión...")
    for dep in vision_deps:
        if not run_command(dep, f"Instalando dependencia de visión: {dep}"):
            print(f"⚠️ Advertencia: Error instalando {dep}")
    
    # Instalar dependencias de fine-tuning
    print("\n🎯 Instalando dependencias de fine-tuning...")
    for dep in finetuning_deps:
        if not run_command(dep, f"Instalando dependencia de fine-tuning: {dep}"):
            print(f"⚠️ Advertencia: Error instalando {dep}")

def setup_environment_file():
    """Configurar archivo de entorno"""
    print_header("Configurando Variables de Entorno")
    
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if env_example.exists() and not env_file.exists():
        shutil.copy(env_example, env_file)
        print("✅ Archivo .env creado desde env.example")
        print("📝 Recuerda configurar las variables en .env")
    elif env_file.exists():
        print("✅ Archivo .env ya existe")
    else:
        print("⚠️ No se encontró env.example")

def download_models():
    """Descargar modelos necesarios"""
    print_header("Descargando Modelos")
    
    models_to_download = [
        {
            "name": "Whisper Base",
            "command": "python -c \"import whisper; whisper.load_model('base')\"",
            "description": "Descargando modelo Whisper base"
        },
        {
            "name": "YOLO Nano",
            "command": "python -c \"from ultralytics import YOLO; YOLO('yolov8n.pt')\"",
            "description": "Descargando modelo YOLO nano"
        }
    ]
    
    for model in models_to_download:
        print(f"\n📥 {model['description']}")
        if not run_command(model['command'], model['description']):
            print(f"⚠️ Advertencia: Error descargando {model['name']}")

def create_initial_files():
    """Crear archivos iniciales necesarios"""
    print_header("Creando Archivos Iniciales")
    
    # Crear __init__.py en directorios de backend
    init_files = [
        "src/backend/voice/__init__.py",
        "src/backend/vision/__init__.py",
        "src/backend/finetuning/__init__.py",
        "src/backend/social/__init__.py"
    ]
    
    for init_file in init_files:
        path = Path(init_file)
        if not path.exists():
            path.touch()
            print(f"📄 Creado: {init_file}")

def validate_installation():
    """Validar que la instalación fue exitosa"""
    print_header("Validando Instalación")
    
    validation_commands = [
        {
            "command": "python -c \"import torch; print(f'PyTorch: {torch.__version__}')\"",
            "description": "Validando PyTorch"
        },
        {
            "command": "python -c \"import fastapi; print(f'FastAPI: {fastapi.__version__}')\"",
            "description": "Validando FastAPI"
        },
        {
            "command": "python -c \"import whisper; print('Whisper: OK')\"",
            "description": "Validando Whisper"
        },
        {
            "command": "python -c \"import cv2; print(f'OpenCV: {cv2.__version__}')\"",
            "description": "Validando OpenCV"
        }
    ]
    
    success_count = 0
    for validation in validation_commands:
        if run_command(validation['command'], validation['description']):
            success_count += 1
    
    print(f"\n📊 Validación: {success_count}/{len(validation_commands)} exitosas")
    
    if success_count == len(validation_commands):
        print("🎉 ¡Instalación completada exitosamente!")
    else:
        print("⚠️ Algunas validaciones fallaron. Revisa los errores arriba.")

def main():
    """Función principal"""
    print_header("Configuración del Entorno de Desarrollo")
    print("🚀 Configurando asistente de IA con capacidades completas")
    
    # Cambiar al directorio del proyecto
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    print(f"📁 Directorio de trabajo: {project_dir}")
    
    # Ejecutar pasos de configuración
    try:
        create_directory_structure()
        setup_environment_file()
        create_initial_files()
        install_dependencies()
        download_models()
        validate_installation()
        
        print_header("Configuración Completada")
        print("✅ Entorno configurado exitosamente")
        print("\n📋 Próximos pasos:")
        print("1. Configura las variables en .env")
        print("2. Ejecuta: python main.py")
        print("3. Implementa las fases faltantes según IMPLEMENTATION_PLAN.md")
        
    except Exception as e:
        print(f"\n❌ Error durante la configuración: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

