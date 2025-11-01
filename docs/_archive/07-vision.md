# 👁️ Fase 7: Sistema de Visión (Opcional)
## Estado Actual
- No iniciado: sistema de visión aún pendiente.
- Prioridad actual en voz (WS) y backend LLM; se pospone visión hasta estabilizar API REST y RAG.
- Próximos pasos: preparar dependencias (OpenCV, YOLO, Tesseract) y definir API de visión.

## 🎯 Objetivos de esta Fase

- **Implementar capacidades visuales** para análisis de imágenes
- **OCR (Reconocimiento Óptico de Caracteres)** para documentos
- **Detección de objetos** y reconocimiento de patrones
- **Análisis de imágenes** con IA
- **Integración con chat** para consultas visuales
- **Testing completo** del sistema de visión

## ⏱️ Tiempo Estimado

**1 semana** (5 días de trabajo)

## 📋 Checklist de Tareas

### **Día 1: Configuración de Visión**
- [ ] Instalar OpenCV y bibliotecas de visión
- [ ] Configurar YOLO para detección de objetos
- [ ] Implementar OCR con Tesseract
- [ ] Sistema de procesamiento de imágenes

### **Día 2: Detección de Objetos**
- [ ] YOLO para detección en tiempo real
- [ ] Clasificación de objetos
- [ ] Análisis de escenas
- [ ] Integración con LLM

### **Día 3: OCR y Documentos**
- [ ] Tesseract para OCR
- [ ] Procesamiento de PDFs
- [ ] Extracción de texto
- [ ] Análisis de documentos

### **Día 4: Análisis Avanzado**
- [ ] Análisis de sentimientos en imágenes
- [ ] Reconocimiento facial básico
- [ ] Análisis de colores y patrones
- [ ] Descripción automática de imágenes

### **Día 5: Integración y Testing**
- [ ] Integración con sistema de chat
- [ ] API de visión
- [ ] Testing completo
- [ ] Documentación

## 🔧 Herramientas Necesarias

### **Visión por Computadora**
- **OpenCV**: Procesamiento de imágenes
- **YOLO**: Detección de objetos
- **Tesseract**: OCR
- **PIL/Pillow**: Manipulación de imágenes
- **scikit-image**: Análisis de imágenes

### **IA y Machine Learning**
- **torchvision**: Modelos preentrenados
- **transformers**: Modelos de visión
- **ultralytics**: YOLO moderno
- **easyocr**: OCR alternativo

### **Procesamiento de Documentos**
- **PyPDF2**: Procesamiento de PDFs
- **pdf2image**: Conversión PDF a imagen
- **pytesseract**: Interfaz Python para Tesseract

## 🏗️ Arquitectura del Sistema de Visión

### **📐 Componentes Principales**

```
┌─────────────────────────────────────────────────────────────┐
│                    SISTEMA DE VISIÓN                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Captura   │  │ Procesamiento│  │   Análisis  │        │
│  │   de Imagen │  │   de Imagen  │  │    con IA   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│         │                 │                 │              │
│         ▼                 ▼                 ▼              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Detección │  │     OCR     │  │ Descripción │        │
│  │   Objetos   │  │   Texto     │  │  Automática │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### **🔄 Flujo de Procesamiento**

```
Imagen → Preprocesamiento → Análisis → Descripción → Respuesta
```

## 🚀 Implementación

### **1. Dependencias para Visión**

```python
# requirements-vision.txt
# Visión por Computadora
opencv-python==4.8.1.78
ultralytics==8.0.196
torchvision==0.15.2
scikit-image==0.21.0

# OCR
pytesseract==0.3.10
easyocr==1.7.0
pdf2image==1.16.3
PyPDF2==3.0.1

# Procesamiento de Imágenes
Pillow==10.0.1
numpy==1.24.3
matplotlib==3.7.2

# IA y ML
transformers==4.35.0
torch==2.1.0
```

### **2. Servicio de Visión Principal**

```python
# backend/app/ai/vision/vision_service.py
import cv2
import numpy as np
from typing import Dict, List, Any, Optional
import torch
from ultralytics import YOLO
import pytesseract
from PIL import Image
import base64
import io

class VisionService:
    """Servicio de visión por computadora"""
    
    def __init__(self):
        self.yolo_model = None
        self.ocr_engine = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Inicializar modelos de visión"""
        try:
            # Inicializar YOLO
            self.yolo_model = YOLO('yolov8n.pt')  # Modelo ligero
            print("✅ YOLO inicializado")
        except Exception as e:
            print(f"⚠️ Error inicializando YOLO: {e}")
        
        try:
            # Configurar Tesseract
            pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
            print("✅ Tesseract configurado")
        except Exception as e:
            print(f"⚠️ Error configurando Tesseract: {e}")
    
    async def analyze_image(self, image_data: bytes, analysis_type: str = "full") -> Dict[str, Any]:
        """Analizar imagen con múltiples técnicas"""
        try:
            # Convertir bytes a imagen
            image = self._bytes_to_image(image_data)
            
            results = {
                "success": True,
                "image_info": self._get_image_info(image),
                "analysis": {}
            }
            
            if analysis_type in ["full", "objects"]:
                results["analysis"]["objects"] = await self._detect_objects(image)
            
            if analysis_type in ["full", "text"]:
                results["analysis"]["text"] = await self._extract_text(image)
            
            if analysis_type in ["full", "description"]:
                results["analysis"]["description"] = await self._describe_image(image)
            
            return results
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _bytes_to_image(self, image_data: bytes) -> np.ndarray:
        """Convertir bytes a imagen OpenCV"""
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return image
    
    def _get_image_info(self, image: np.ndarray) -> Dict[str, Any]:
        """Obtener información básica de la imagen"""
        height, width, channels = image.shape
        return {
            "width": width,
            "height": height,
            "channels": channels,
            "size": f"{width}x{height}",
            "format": "RGB" if channels == 3 else "Grayscale"
        }
    
    async def _detect_objects(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detectar objetos en la imagen"""
        if not self.yolo_model:
            return []
        
        try:
            # Ejecutar detección
            results = self.yolo_model(image)
            
            objects = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Obtener coordenadas y confianza
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())
                        class_name = self.yolo_model.names[class_id]
                        
                        objects.append({
                            "class": class_name,
                            "confidence": float(confidence),
                            "bbox": {
                                "x1": float(x1),
                                "y1": float(y1),
                                "x2": float(x2),
                                "y2": float(y2)
                            }
                        })
            
            return objects
            
        except Exception as e:
            print(f"Error en detección de objetos: {e}")
            return []
    
    async def _extract_text(self, image: np.ndarray) -> Dict[str, Any]:
        """Extraer texto de la imagen usando OCR"""
        try:
            # Convertir a PIL Image
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            # Extraer texto con Tesseract
            text = pytesseract.image_to_string(pil_image, lang='spa+eng')
            
            # Obtener datos estructurados
            data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
            
            # Procesar datos
            words = []
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 30:  # Solo confianza > 30%
                    words.append({
                        "text": data['text'][i],
                        "confidence": int(data['conf'][i]),
                        "bbox": {
                            "x": int(data['left'][i]),
                            "y": int(data['top'][i]),
                            "width": int(data['width'][i]),
                            "height": int(data['height'][i])
                        }
                    })
            
            return {
                "full_text": text.strip(),
                "words": words,
                "language": "spa+eng"
            }
            
        except Exception as e:
            return {
                "full_text": "",
                "words": [],
                "error": str(e)
            }
    
    async def _describe_image(self, image: np.ndarray) -> str:
        """Generar descripción automática de la imagen"""
        try:
            # Detectar objetos primero
            objects = await self._detect_objects(image)
            
            # Crear descripción basada en objetos detectados
            if objects:
                object_names = [obj["class"] for obj in objects if obj["confidence"] > 0.5]
                unique_objects = list(set(object_names))
                
                if len(unique_objects) == 1:
                    description = f"La imagen muestra {unique_objects[0]}"
                elif len(unique_objects) == 2:
                    description = f"La imagen muestra {unique_objects[0]} y {unique_objects[1]}"
                else:
                    description = f"La imagen muestra {', '.join(unique_objects[:-1])} y {unique_objects[-1]}"
            else:
                description = "No se pudieron identificar objetos específicos en la imagen"
            
            return description
            
        except Exception as e:
            return f"Error generando descripción: {str(e)}"
    
    async def process_document(self, document_data: bytes, document_type: str = "pdf") -> Dict[str, Any]:
        """Procesar documento (PDF, imagen, etc.)"""
        try:
            if document_type == "pdf":
                return await self._process_pdf(document_data)
            else:
                return await self.analyze_image(document_data, "full")
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _process_pdf(self, pdf_data: bytes) -> Dict[str, Any]:
        """Procesar PDF y extraer texto/imágenes"""
        try:
            from pdf2image import convert_from_bytes
            from PyPDF2 import PdfReader
            import io
            
            # Convertir PDF a imágenes
            images = convert_from_bytes(pdf_data)
            
            # Extraer texto del PDF
            pdf_reader = PdfReader(io.BytesIO(pdf_data))
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
            
            # Analizar cada página
            page_analyses = []
            for i, image in enumerate(images):
                # Convertir PIL a OpenCV
                opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Analizar página
                page_analysis = await self.analyze_image(
                    cv2.imencode('.jpg', opencv_image)[1].tobytes(),
                    "full"
                )
                page_analyses.append({
                    "page": i + 1,
                    "analysis": page_analysis
                })
            
            return {
                "success": True,
                "text_content": text_content,
                "pages": len(images),
                "page_analyses": page_analyses
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
```

### **3. API de Visión**

```python
# backend/app/api/vision.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from ..ai.vision.vision_service import VisionService
import base64

router = APIRouter(prefix="/api/vision", tags=["vision"])

class VisionAnalysisRequest(BaseModel):
    analysis_type: str = "full"  # full, objects, text, description
    image_format: str = "jpeg"

class VisionAnalysisResponse(BaseModel):
    success: bool
    analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.post("/analyze", response_model=VisionAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    analysis_type: str = "full"
):
    """Analizar imagen con capacidades de visión"""
    try:
        # Leer archivo
        image_data = await file.read()
        
        # Crear servicio de visión
        vision_service = VisionService()
        
        # Analizar imagen
        result = await vision_service.analyze_image(image_data, analysis_type)
        
        return VisionAnalysisResponse(
            success=result["success"],
            analysis=result if result["success"] else None,
            error=result.get("error") if not result["success"] else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-base64")
async def analyze_image_base64(
    request: Dict[str, Any]
):
    """Analizar imagen desde base64"""
    try:
        # Decodificar base64
        image_data = base64.b64decode(request["image_data"])
        
        # Crear servicio de visión
        vision_service = VisionService()
        
        # Analizar imagen
        result = await vision_service.analyze_image(
            image_data, 
            request.get("analysis_type", "full")
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-document")
async def process_document(
    file: UploadFile = File(...),
    document_type: str = "pdf"
):
    """Procesar documento (PDF, imagen, etc.)"""
    try:
        # Leer archivo
        document_data = await file.read()
        
        # Crear servicio de visión
        vision_service = VisionService()
        
        # Procesar documento
        result = await vision_service.process_document(document_data, document_type)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/capabilities")
async def get_vision_capabilities():
    """Obtener capacidades del sistema de visión"""
    return {
        "object_detection": True,
        "ocr": True,
        "image_description": True,
        "document_processing": True,
        "supported_formats": ["jpg", "png", "pdf", "tiff"],
        "languages": ["spanish", "english"]
    }
```

### **4. Integración con Chat**

```python
# backend/app/ai/vision/vision_chat_integration.py
from typing import Dict, Any, List
import base64
import io
from PIL import Image

class VisionChatIntegration:
    """Integración de visión con sistema de chat"""
    
    def __init__(self, vision_service, llm_service):
        self.vision_service = vision_service
        self.llm_service = llm_service
    
    async def process_vision_query(self, user_message: str, image_data: bytes = None) -> str:
        """Procesar consulta que incluye imagen"""
        try:
            if not image_data:
                return "No se proporcionó imagen para analizar."
            
            # Analizar imagen
            vision_result = await self.vision_service.analyze_image(image_data, "full")
            
            if not vision_result["success"]:
                return "Error analizando la imagen. Intenta con otra imagen."
            
            # Construir contexto visual
            visual_context = self._build_visual_context(vision_result)
            
            # Generar respuesta con contexto visual
            response = await self.llm_service.generate_response_for_user(
                user_id="vision_user",
                prompt=user_message,
                context=visual_context
            )
            
            return response
            
        except Exception as e:
            return f"Error procesando consulta visual: {str(e)}"
    
    def _build_visual_context(self, vision_result: Dict[str, Any]) -> str:
        """Construir contexto visual para el LLM"""
        context_parts = []
        
        # Información de la imagen
        if "image_info" in vision_result:
            info = vision_result["image_info"]
            context_parts.append(f"Imagen: {info['size']}, {info['format']}")
        
        # Objetos detectados
        if "analysis" in vision_result and "objects" in vision_result["analysis"]:
            objects = vision_result["analysis"]["objects"]
            if objects:
                object_names = [obj["class"] for obj in objects if obj["confidence"] > 0.5]
                context_parts.append(f"Objetos detectados: {', '.join(object_names)}")
        
        # Texto extraído
        if "analysis" in vision_result and "text" in vision_result["analysis"]:
            text_info = vision_result["analysis"]["text"]
            if text_info.get("full_text"):
                context_parts.append(f"Texto en la imagen: {text_info['full_text'][:200]}...")
        
        # Descripción
        if "analysis" in vision_result and "description" in vision_result["analysis"]:
            description = vision_result["analysis"]["description"]
            context_parts.append(f"Descripción: {description}")
        
        return " | ".join(context_parts)
    
    async def handle_vision_commands(self, user_message: str, image_data: bytes = None) -> str:
        """Manejar comandos específicos de visión"""
        message_lower = user_message.lower()
        
        if "detectar" in message_lower or "objetos" in message_lower:
            if not image_data:
                return "Necesito una imagen para detectar objetos."
            
            result = await self.vision_service.analyze_image(image_data, "objects")
            if result["success"] and "analysis" in result:
                objects = result["analysis"].get("objects", [])
                if objects:
                    object_list = [f"{obj['class']} ({obj['confidence']:.2f})" for obj in objects]
                    return f"Objetos detectados: {', '.join(object_list)}"
                else:
                    return "No se detectaron objetos en la imagen."
        
        elif "leer" in message_lower or "texto" in message_lower:
            if not image_data:
                return "Necesito una imagen para extraer texto."
            
            result = await self.vision_service.analyze_image(image_data, "text")
            if result["success"] and "analysis" in result:
                text_info = result["analysis"].get("text", {})
                if text_info.get("full_text"):
                    return f"Texto extraído: {text_info['full_text']}"
                else:
                    return "No se encontró texto en la imagen."
        
        elif "describir" in message_lower:
            if not image_data:
                return "Necesito una imagen para describir."
            
            result = await self.vision_service.analyze_image(image_data, "description")
            if result["success"] and "analysis" in result:
                description = result["analysis"].get("description", "")
                return f"Descripción: {description}"
        
        else:
            # Procesar como consulta general
            return await self.process_vision_query(user_message, image_data)
```

## 📊 Métricas de Éxito

### **🎯 Objetivos Técnicos**
- **Detección de Objetos**: > 80% precisión
- **OCR**: > 90% precisión en texto claro
- **Latencia**: < 5s por imagen
- **Memoria**: < 1GB para modelos
- **Formatos**: JPG, PNG, PDF soportados

### **🎯 Objetivos de Funcionalidad**
- **Detección de Objetos**: Funcionando correctamente
- **OCR**: Extracción de texto precisa
- **Descripción**: Generación automática
- **Integración**: Con sistema de chat
- **Testing**: > 85% cobertura de código

## ✅ Criterios de Éxito

### **📋 Checklist de Validación**
- [ ] **Detección de Objetos** funcionando
- [ ] **OCR** extrayendo texto correctamente
- [ ] **Descripción automática** generando respuestas
- [ ] **Integración con chat** operativa
- [ ] **API de visión** respondiendo
- [ ] **Testing completo** del sistema
- [ ] **Documentación** actualizada

---

**🎉 ¡Con esta fase tendrás capacidades visuales avanzadas!**

*Recuerda: La visión es una característica opcional pero muy valiosa para análisis de documentos e imágenes.* 🚀

