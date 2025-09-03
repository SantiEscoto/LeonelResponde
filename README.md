# Leonel Responde

Asistente Multimodal Offline - Implementación de un asistente con LLM local, memoria y base de conocimiento.

## Descripción

Este proyecto implementa un asistente multimodal offline diseñado para funcionar en dispositivos como Jetson Nano sin necesidad de conexión a internet. El desarrollo está dividido en fases:

- **Fase 1**: Motor LLM local con memoria y base de conocimiento (actual)
- **Fase 2**: Integración de capacidades de voz (STT/TTS)
- **Fase 3**: Integración de capacidades de visión
- **Fase 4**: Interfaz gráfica y empaquetado

## Estructura del Proyecto

```
/LeonelResponde
├── Assistant/         # Implementación del asistente (Fase 1)
│   ├── backend/       # Componentes del backend
│   │   ├── llm/       # Motor LLM, memoria y base de conocimiento
│   │   └── utils/     # Utilidades (logging, etc.)
│   ├── models/        # Directorio para modelos (no incluidos en el repo)
│   ├── logs/          # Logs del sistema
│   ├── config.py      # Configuración del sistema
│   ├── main.py        # Punto de entrada principal
│   └── README.md      # Documentación específica de la Fase 1
└── README.md          # Este archivo
```

## Instalación y Uso

Consulta el README.md dentro del directorio `Assistant/` para instrucciones detalladas sobre la instalación y uso de la Fase 1.

## Licencia

Este proyecto está bajo la Licencia MIT.