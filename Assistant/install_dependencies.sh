#!/bin/bash
# Auto-generated dependency installation script
# for LeonelResponde Assistant

echo 'Installing missing dependencies...'

# Voice Dependencies
echo 'Installing Vosk...'
pip install vosk

echo 'Installing SoundDevice...'
pip install sounddevice

echo 'Installing Coqui TTS...'
pip install TTS

# Memory Dependencies
echo 'Installing FAISS...'
pip install faiss-cpu

# Vision Dependencies
echo 'Installing OpenCV...'
pip install opencv-python

echo 'Installing EasyOCR...'
pip install easyocr

echo 'Installing Face Recognition...'
pip install face_recognition

echo 'Installing Ultralytics YOLO...'
pip install ultralytics

# Performance Dependencies
echo 'Installing TensorRT...'
pip install tensorrt

echo 'Installing ONNX Runtime...'
pip install onnxruntime

# Utility Dependencies
echo 'Installing Pandas...'
pip install pandas

echo 'Installation completed!'
echo 'Please restart the application to use new dependencies.'