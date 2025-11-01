# 🎯 Fase 4: Fine-tuning y Personalización
## Estado Actual
- No iniciado: fine-tuning y personalización pendientes.
- Backend LLM local funcionando con modelos GGUF (Mistral) y versión/caché básica; se planifica LoRA/QLoRA cuando esté lista la API y datasets.
- Voz TTS/STT vía WS operativa; integración futura con pipeline de entrenamiento para personalización.
- Próximos pasos: definir datasets de identidad/conocimiento, preparar LoRA/QLoRA y API de fine-tuning.

## 🎯 Objetivos de esta Fase

- **Implementar fine-tuning** con LoRA/QLoRA para hardware limitado
- **Sistema de personalización** completo para desarrolladores
- **Interfaz de desarrollador** para configurar identidad y conocimiento
- **API de fine-tuning** para gestión de modelos personalizados
- **Testing y validación** del sistema de personalización

## ⏱️ Tiempo Estimado

**2 semanas** (10 días de trabajo)

## 📋 Checklist de Tareas

### **Semana 1: Fine-tuning Core**
- [ ] Configurar LoRA/QLoRA para hardware limitado
- [ ] Implementar sistema de datos de entrenamiento
- [ ] Crear API de fine-tuning
- [ ] Sistema de gestión de modelos personalizados
- [ ] Testing del fine-tuning

### **Semana 2: Interfaz y Optimización**
- [ ] Interfaz de desarrollador para personalización
- [ ] Sistema de validación de modelos
- [ ] Optimización para hardware limitado
- [ ] Testing completo del sistema
- [ ] Documentación de personalización

## 🔧 Herramientas Necesarias

### **Fine-tuning**
- **LoRA/QLoRA**: Fine-tuning eficiente
- **Transformers**: Modelos de Hugging Face
- **PEFT**: Parameter Efficient Fine-Tuning
- **BitsAndBytes**: Cuantización 4-bit
- **Accelerate**: Optimización de entrenamiento

### **Datos y Entrenamiento**
- **Datasets**: Gestión de datos de entrenamiento
- **Evaluate**: Métricas de evaluación
- **Wandb**: Seguimiento de experimentos
- **TensorBoard**: Visualización de entrenamiento

### **Interfaz de Desarrollador**
- **React**: Frontend para personalización
- **TypeScript**: Tipado estático
- **Framer Motion**: Animaciones
- **Tailwind CSS**: Estilos

## 🏗️ Arquitectura del Fine-tuning

### **📐 Componentes Principales**

```
┌─────────────────────────────────────────────────────────────┐
│                    FINE-TUNING SYSTEM                      │
├─────────────────────────────────────────────────────────────┤
│  LoRA/QLoRA + Transformers + PEFT + BitsAndBytes         │
│  • Fine-tuning eficiente para hardware limitado          │
│  • Cuantización 4-bit para ahorrar memoria               │
│  • Entrenamiento incremental sin reiniciar               │
│  • Múltiples personalizaciones simultáneas               │
└─────────────────────────────────────────────────────────────┘
                                ↕️
┌─────────────────────────────────────────────────────────────┐
│                    DEVELOPER INTERFACE                     │
├─────────────────────────────────────────────────────────────┤
│  React + TypeScript + Framer Motion                       │
│  • Interfaz de desarrollador intuitiva                    │
│  • Configuración de identidad y conocimiento              │
│  • Progreso de entrenamiento en tiempo real               │
│  • Gestión de modelos personalizados                     │
└─────────────────────────────────────────────────────────────┘
```

### **🔄 Flujo de Fine-tuning**

```
Datos de Entrenamiento → LoRA/QLoRA → Modelo Personalizado → Validación → Despliegue
```

## 🚀 Implementación

### **1. Dependencias para Fine-tuning**

```python
# requirements-finetuning.txt
# Fine-tuning Core
torch>=2.0.0
transformers>=4.30.0
peft>=0.4.0
bitsandbytes>=0.39.0
datasets>=2.12.0
accelerate>=0.20.0
evaluate>=0.4.0

# Training
wandb>=0.16.0
tensorboard>=2.15.0
scikit-learn>=1.3.0

# Data Processing
pandas>=2.0.0
numpy>=1.24.0
tqdm>=4.65.0
```

### **2. Sistema LoRA para Hardware Limitado**

```python
# backend/app/core/lora_finetuning.py
import torch
from peft import LoraConfig, get_peft_model, TaskType
from transformers import AutoModelForCausalLM, AutoTokenizer

class LoRAFineTuner:
    """Fine-tuning eficiente con LoRA para hardware limitado"""
    
    def __init__(self, model_name: str = "mistral:7b"):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        
        # Configuración LoRA optimizada para hardware limitado
        self.lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            inference_mode=False,
            r=16,  # Rank bajo para ahorrar memoria
            lora_alpha=32,
            lora_dropout=0.1,
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"]
        )
        
        # Aplicar LoRA al modelo
        self.model = get_peft_model(self.model, self.lora_config)
    
    def prepare_training_data(self, identity_data: list, knowledge_data: list):
        """Preparar datos de entrenamiento para personalización"""
        
        training_examples = []
        
        # Datos de identidad (personalidad, tono, estilo)
        for example in identity_data:
            training_examples.append({
                "instruction": example["instruction"],
                "input": example["input"],
                "output": example["output"]
            })
        
        # Datos de conocimiento (información específica)
        for example in knowledge_data:
            training_examples.append({
                "instruction": example["instruction"],
                "input": example["input"],
                "output": example["output"]
            })
        
        return training_examples
    
    def train_personalized_model(self, training_data: list, epochs: int = 3):
        """Entrenar modelo personalizado con LoRA"""
        
        # Configuración de entrenamiento optimizada
        training_args = {
            "output_dir": "./personalized_model",
            "per_device_train_batch_size": 1,  # Batch pequeño para hardware limitado
            "gradient_accumulation_steps": 4,
            "num_train_epochs": epochs,
            "learning_rate": 2e-4,
            "fp16": True,  # Usar precisión mixta para ahorrar memoria
            "save_steps": 100,
            "eval_steps": 100,
            "logging_steps": 10,
            "warmup_steps": 50,
            "max_steps": 1000,  # Límite de pasos para hardware limitado
        }
        
        # Entrenar modelo
        trainer = self._setup_trainer(training_data, training_args)
        trainer.train()
        
        return trainer.model
```

### **3. QLoRA para Hardware Muy Limitado**

```python
# backend/app/core/qlora_finetuning.py
from transformers import BitsAndBytesConfig
import torch

class QLoRAFineTuner:
    """Fine-tuning ultra-eficiente con QLoRA para hardware muy limitado"""
    
    def __init__(self, model_name: str = "mistral:7b"):
        self.model_name = model_name
        
        # Configuración de cuantización para hardware limitado
        self.quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,  # Cuantización 4-bit
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        
        self.model = self._load_quantized_model()
        self.lora_config = self._setup_lora_config()
    
    def _load_quantized_model(self):
        """Cargar modelo cuantizado para ahorrar memoria"""
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=self.quantization_config,
            device_map="auto",
            torch_dtype=torch.float16
        )
        return model
    
    def _setup_lora_config(self):
        """Configurar LoRA para QLoRA"""
        return LoraConfig(
            r=8,  # Rank muy bajo para QLoRA
            lora_alpha=16,
            lora_dropout=0.1,
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
            bias="none",
            task_type="CAUSAL_LM"
        )
```

### **4. Datos de Entrenamiento para Personalización**

```python
# backend/app/data/identity_data.py
IDENTITY_EXAMPLES = [
    {
        "instruction": "Eres un asistente de IA amigable y profesional. Responde de manera cálida pero informativa.",
        "input": "Hola, ¿cómo estás?",
        "output": "¡Hola! Estoy muy bien, gracias por preguntar. Soy tu asistente de IA y estoy aquí para ayudarte con cualquier cosa que necesites. ¿En qué puedo asistirte hoy?"
    },
    {
        "instruction": "Mantén un tono profesional pero accesible. Sé útil y directo.",
        "input": "¿Puedes ayudarme con un problema técnico?",
        "output": "Por supuesto, estaré encantado de ayudarte con tu problema técnico. Por favor, describe el problema que estás experimentando y te proporcionaré una solución paso a paso."
    },
    {
        "instruction": "Sé empático y comprensivo. Muestra interés genuino en ayudar.",
        "input": "Estoy frustrado con este error",
        "output": "Entiendo tu frustración, los errores técnicos pueden ser muy molestos. No te preocupes, juntos podemos resolverlo. Cuéntame exactamente qué está pasando y qué error estás viendo."
    }
]

# backend/app/data/knowledge_data.py
KNOWLEDGE_EXAMPLES = [
    {
        "instruction": "Proporciona información específica sobre tu dominio de conocimiento.",
        "input": "¿Qué es la inteligencia artificial?",
        "output": "La inteligencia artificial (IA) es una rama de la informática que se enfoca en crear sistemas capaces de realizar tareas que normalmente requieren inteligencia humana, como el reconocimiento de patrones, el aprendizaje y la toma de decisiones. En nuestro contexto, utilizamos IA para crear asistentes conversacionales que pueden ayudar a los usuarios de manera natural y eficiente."
    },
    {
        "instruction": "Explica conceptos técnicos de manera clara y accesible.",
        "input": "¿Cómo funciona el machine learning?",
        "output": "El machine learning (aprendizaje automático) es una técnica de IA que permite a las computadoras aprender y mejorar automáticamente a partir de la experiencia, sin ser programadas explícitamente para cada tarea. Funciona analizando grandes cantidades de datos para identificar patrones y hacer predicciones o decisiones."
    }
]
```

### **5. API de Fine-tuning para Desarrolladores**

```python
# backend/app/api/finetuning.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Any
from ..core.lora_finetuning import LoRAFineTuner
from ..core.qlora_finetuning import QLoRAFineTuner
from ..core.finetuning_tools import FineTuningTools
import asyncio

router = APIRouter(prefix="/api/developer", tags=["fine-tuning"])

class PersonalizationRequest(BaseModel):
    identity: Dict[str, str]
    knowledge: Dict[str, Any]
    training_config: Dict[str, Any] = {}

class FineTuningResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str

class FineTuningService:
    """Servicio de fine-tuning para desarrolladores"""
    
    def __init__(self):
        self.finetuning_tools = FineTuningTools()
        self.active_tasks = {}
    
    async def start_finetuning(
        self, 
        personalization_data: PersonalizationRequest,
        background_tasks: BackgroundTasks
    ) -> str:
        """Iniciar proceso de fine-tuning"""
        
        task_id = f"finetune_{int(time.time())}"
        
        # Configurar tarea en background
        background_tasks.add_task(
            self._execute_finetuning,
            task_id,
            personalization_data
        )
        
        self.active_tasks[task_id] = {
            "status": "started",
            "progress": 0,
            "message": "Iniciando fine-tuning..."
        }
        
        return task_id
    
    async def _execute_finetuning(
        self, 
        task_id: str, 
        personalization_data: PersonalizationRequest
    ):
        """Ejecutar fine-tuning en background"""
        
        try:
            # Actualizar estado
            self.active_tasks[task_id]["status"] = "preparing"
            self.active_tasks[task_id]["progress"] = 10
            self.active_tasks[task_id]["message"] = "Preparando datos de entrenamiento..."
            
            # Preparar datos de entrenamiento
            identity_data = self._prepare_identity_data(personalization_data.identity)
            knowledge_data = self._prepare_knowledge_data(personalization_data.knowledge)
            
            # Actualizar estado
            self.active_tasks[task_id]["status"] = "training"
            self.active_tasks[task_id]["progress"] = 30
            self.active_tasks[task_id]["message"] = "Entrenando modelo personalizado..."
            
            # Configurar fine-tuner
            finetuner = LoRAFineTuner()  # o QLoRAFineTuner para hardware muy limitado
            
            # Preparar datos
            training_data = finetuner.prepare_training_data(identity_data, knowledge_data)
            
            # Entrenar modelo
            personalized_model = finetuner.train_personalized_model(
                training_data, 
                epochs=personalization_data.training_config.get("epochs", 3)
            )
            
            # Actualizar estado
            self.active_tasks[task_id]["status"] = "saving"
            self.active_tasks[task_id]["progress"] = 80
            self.active_tasks[task_id]["message"] = "Guardando modelo personalizado..."
            
            # Guardar modelo personalizado
            model_path = f"./models/personalized_{task_id}"
            personalized_model.save_pretrained(model_path)
            
            # Actualizar estado final
            self.active_tasks[task_id]["status"] = "completed"
            self.active_tasks[task_id]["progress"] = 100
            self.active_tasks[task_id]["message"] = "Fine-tuning completado exitosamente"
            self.active_tasks[task_id]["model_path"] = model_path
            
        except Exception as e:
            # Manejar errores
            self.active_tasks[task_id]["status"] = "error"
            self.active_tasks[task_id]["message"] = f"Error en fine-tuning: {str(e)}"
    
    def _prepare_identity_data(self, identity: Dict[str, str]) -> List[Dict]:
        """Preparar datos de identidad para entrenamiento"""
        identity_examples = []
        
        # Personalidad
        if identity.get("personality"):
            identity_examples.append({
                "instruction": f"Eres un asistente con la siguiente personalidad: {identity['personality']}",
                "input": "Hola, ¿cómo estás?",
                "output": f"¡Hola! Estoy muy bien, gracias por preguntar. {identity['personality']} ¿En qué puedo ayudarte hoy?"
            })
        
        # Tono
        if identity.get("tone"):
            tone_examples = {
                "formal": "Mantén un tono formal y profesional en todas tus respuestas.",
                "amigable": "Sé amigable y cálido en tus interacciones.",
                "profesional": "Mantén un tono profesional pero accesible.",
                "casual": "Sé casual y relajado en tu comunicación."
            }
            
            if identity["tone"] in tone_examples:
                identity_examples.append({
                    "instruction": tone_examples[identity["tone"]],
                    "input": "¿Puedes ayudarme?",
                    "output": f"Por supuesto, estaré encantado de ayudarte. {tone_examples[identity['tone']].lower()}"
                })
        
        # Estilo
        if identity.get("style"):
            identity_examples.append({
                "instruction": f"Tu estilo de comunicación debe ser: {identity['style']}",
                "input": "Explícame algo",
                "output": f"Te explico de manera que sea {identity['style'].lower()}:"
            })
        
        return identity_examples
    
    def _prepare_knowledge_data(self, knowledge: Dict[str, Any]) -> List[Dict]:
        """Preparar datos de conocimiento para entrenamiento"""
        knowledge_examples = []
        
        # Dominio de conocimiento
        if knowledge.get("domain"):
            knowledge_examples.append({
                "instruction": f"Eres un experto en {knowledge['domain']}. Proporciona información precisa y detallada.",
                "input": f"¿Qué es {knowledge['domain']}?",
                "output": f"{knowledge['domain']} es un campo especializado que involucra..."
            })
        
        # Áreas de especialización
        if knowledge.get("expertise"):
            for expertise in knowledge["expertise"]:
                knowledge_examples.append({
                    "instruction": f"Tienes experiencia especializada en {expertise}.",
                    "input": f"¿Puedes explicarme sobre {expertise}?",
                    "output": f"Claro, {expertise} es un área en la que tengo experiencia especializada..."
                })
        
        # Ejemplos específicos
        if knowledge.get("examples"):
            for example in knowledge["examples"]:
                knowledge_examples.append({
                    "instruction": "Proporciona información específica y detallada.",
                    "input": "Dame un ejemplo específico",
                    "output": example
                })
        
        return knowledge_examples
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Obtener estado de tarea de fine-tuning"""
        return self.active_tasks.get(task_id, {
            "status": "not_found",
            "progress": 0,
            "message": "Tarea no encontrada"
        })

# Instancia del servicio
finetuning_service = FineTuningService()

@router.post("/finetune", response_model=FineTuningResponse)
async def start_finetuning(
    request: PersonalizationRequest,
    background_tasks: BackgroundTasks
):
    """Iniciar proceso de fine-tuning personalizado"""
    try:
        task_id = await finetuning_service.start_finetuning(request, background_tasks)
        
        return FineTuningResponse(
            task_id=task_id,
            status="started",
            progress=0,
            message="Fine-tuning iniciado"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/finetune/{task_id}", response_model=FineTuningResponse)
async def get_finetuning_status(task_id: str):
    """Obtener estado del fine-tuning"""
    status = finetuning_service.get_task_status(task_id)
    
    return FineTuningResponse(
        task_id=task_id,
        status=status["status"],
        progress=status["progress"],
        message=status["message"]
    )

@router.get("/finetune")
async def list_finetuning_tasks():
    """Listar todas las tareas de fine-tuning"""
    return {
        "tasks": list(finetuning_service.active_tasks.keys()),
        "active_count": len(finetuning_service.active_tasks)
    }
```

### **6. Interfaz de Desarrollador para Personalización**

```typescript
// frontend/src/components/DeveloperPersonalization.tsx
import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface PersonalizationData {
  identity: {
    personality: string;
    tone: string;
    style: string;
  };
  knowledge: {
    domain: string;
    expertise: string[];
    examples: string[];
  };
}

export const DeveloperPersonalization: React.FC = () => {
  const [personalizationData, setPersonalizationData] = useState<PersonalizationData>({
    identity: {
      personality: '',
      tone: '',
      style: ''
    },
    knowledge: {
      domain: '',
      expertise: [],
      examples: []
    }
  });

  const [isTraining, setIsTraining] = useState(false);
  const [trainingProgress, setTrainingProgress] = useState(0);

  const handleFineTuning = async () => {
    setIsTraining(true);
    setTrainingProgress(0);
    
    try {
      // Simular progreso de entrenamiento
      const progressInterval = setInterval(() => {
        setTrainingProgress(prev => {
          if (prev >= 100) {
            clearInterval(progressInterval);
            setIsTraining(false);
            return 100;
          }
          return prev + 10;
        });
      }, 1000);

      // Enviar datos de personalización al backend
      const response = await fetch('/api/developer/finetune', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(personalizationData)
      });
      
      if (response.ok) {
        console.log('Fine-tuning completado');
      }
    } catch (error) {
      console.error('Error en fine-tuning:', error);
      setIsTraining(false);
    }
  };

  return (
    <div className="developer-personalization bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        🎯 Personalización del Asistente
      </h2>
      
      {/* Configuración de Identidad */}
      <div className="identity-section mb-8">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          🎭 Identidad del Asistente
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Personalidad
            </label>
            <textarea
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              placeholder="Describe la personalidad del asistente..."
              value={personalizationData.identity.personality}
              onChange={(e) => setPersonalizationData({
                ...personalizationData,
                identity: { ...personalizationData.identity, personality: e.target.value }
              })}
              rows={3}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tono de Voz
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              value={personalizationData.identity.tone}
              onChange={(e) => setPersonalizationData({
                ...personalizationData,
                identity: { ...personalizationData.identity, tone: e.target.value }
              })}
            >
              <option value="">Seleccionar tono...</option>
              <option value="formal">Formal</option>
              <option value="amigable">Amigable</option>
              <option value="profesional">Profesional</option>
              <option value="casual">Casual</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Estilo de Comunicación
            </label>
            <textarea
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              placeholder="Describe el estilo de comunicación..."
              value={personalizationData.identity.style}
              onChange={(e) => setPersonalizationData({
                ...personalizationData,
                identity: { ...personalizationData.identity, style: e.target.value }
              })}
              rows={3}
            />
          </div>
        </div>
      </div>
      
      {/* Configuración de Conocimiento */}
      <div className="knowledge-section mb-8">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          🧠 Conocimiento Específico
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Dominio de Conocimiento
            </label>
            <input
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              placeholder="Ej: Inteligencia Artificial, Medicina, Derecho..."
              value={personalizationData.knowledge.domain}
              onChange={(e) => setPersonalizationData({
                ...personalizationData,
                knowledge: { ...personalizationData.knowledge, domain: e.target.value }
              })}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Áreas de Especialización
            </label>
            <input
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              placeholder="Ej: Machine Learning, Deep Learning, NLP..."
              value={personalizationData.knowledge.expertise.join(', ')}
              onChange={(e) => setPersonalizationData({
                ...personalizationData,
                knowledge: { 
                  ...personalizationData.knowledge, 
                  expertise: e.target.value.split(', ').filter(item => item.trim())
                }
              })}
            />
          </div>
        </div>
        
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Ejemplos de Conocimiento
          </label>
          <textarea
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            placeholder="Agrega ejemplos específicos de conocimiento..."
            value={personalizationData.knowledge.examples.join('\n')}
            onChange={(e) => setPersonalizationData({
              ...personalizationData,
              knowledge: { 
                ...personalizationData.knowledge, 
                examples: e.target.value.split('\n').filter(item => item.trim())
              }
            })}
            rows={4}
          />
        </div>
      </div>
      
      {/* Progreso de Entrenamiento */}
      {isTraining && (
        <div className="training-progress mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              Entrenando modelo personalizado...
            </span>
            <span className="text-sm text-gray-500">{trainingProgress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <motion.div
              className="bg-blue-600 h-2 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${trainingProgress}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>
      )}
      
      {/* Botones de Acción */}
      <div className="flex space-x-4">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleFineTuning}
          disabled={isTraining}
          className={`px-6 py-3 rounded-lg font-medium transition-colors ${
            isTraining
              ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {isTraining ? 'Entrenando...' : 'Iniciar Fine-Tuning'}
        </motion.button>
        
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="px-6 py-3 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
        >
          Guardar Configuración
        </motion.button>
      </div>
    </div>
  );
};
```

## 🧪 Testing del Fine-tuning

### **1. Tests de Fine-tuning**

```python
# backend/tests/test_finetuning.py
import pytest
from app.core.lora_finetuning import LoRAFineTuner
from app.core.qlora_finetuning import QLoRAFineTuner

def test_lora_finetuning():
    """Test que LoRA fine-tuning funcione correctamente"""
    finetuner = LoRAFineTuner()
    
    # Datos de prueba
    identity_data = [
        {
            "instruction": "Eres un asistente amigable",
            "input": "Hola",
            "output": "¡Hola! ¿En qué puedo ayudarte?"
        }
    ]
    
    knowledge_data = [
        {
            "instruction": "Eres experto en IA",
            "input": "¿Qué es IA?",
            "output": "La IA es inteligencia artificial..."
        }
    ]
    
    # Preparar datos
    training_data = finetuner.prepare_training_data(identity_data, knowledge_data)
    
    assert len(training_data) == 2
    assert training_data[0]["instruction"] == "Eres un asistente amigable"

def test_qlora_finetuning():
    """Test que QLoRA fine-tuning funcione correctamente"""
    finetuner = QLoRAFineTuner()
    
    # Verificar que el modelo se carga correctamente
    assert finetuner.model is not None
    assert finetuner.lora_config is not None
```

### **2. Tests de API**

```python
# backend/tests/test_finetuning_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_start_finetuning():
    response = client.post(
        "/api/developer/finetune",
        json={
            "identity": {
                "personality": "Amigable y profesional",
                "tone": "formal",
                "style": "Directo y útil"
            },
            "knowledge": {
                "domain": "Inteligencia Artificial",
                "expertise": ["Machine Learning", "Deep Learning"],
                "examples": ["La IA es el futuro"]
            }
        }
    )
    
    assert response.status_code == 200
    assert "task_id" in response.json()
    assert response.json()["status"] == "started"

def test_get_finetuning_status():
    # Primero iniciar fine-tuning
    start_response = client.post("/api/developer/finetune", json={...})
    task_id = start_response.json()["task_id"]
    
    # Luego verificar estado
    status_response = client.get(f"/api/developer/finetune/{task_id}")
    
    assert status_response.status_code == 200
    assert "status" in status_response.json()
    assert "progress" in status_response.json()
```

## 📊 Métricas de Éxito

### **🎯 Objetivos Técnicos**
- **Tiempo de Fine-tuning**: < 30 minutos para hardware limitado
- **Memoria Utilizada**: < 4GB durante entrenamiento
- **Calidad del Modelo**: > 90% satisfacción con personalización
- **Eficiencia**: LoRA/QLoRA funcionando correctamente
- **Interfaz**: 100% funcional para desarrolladores

### **🎯 Objetivos de Funcionalidad**
- **Personalización**: Identidad y conocimiento específico
- **Fine-tuning**: Modelos personalizados funcionando
- **API**: Todos los endpoints de fine-tuning operativos
- **Interfaz**: Desarrollador puede personalizar fácilmente
- **Testing**: > 90% cobertura de código

## ✅ Criterios de Éxito

### **📋 Checklist de Validación**
- [ ] **LoRA/QLoRA** funcionando correctamente
- [ ] **API de fine-tuning** operativa
- [ ] **Interfaz de desarrollador** funcional
- [ ] **Modelos personalizados** generándose
- [ ] **Testing completo** pasando
- [ ] **Documentación** de personalización
- [ ] **Rendimiento** dentro de métricas objetivo
- [ ] **Preparación** para siguiente fase

### **🎯 Entregables de esta Fase**
- [ ] **Sistema de fine-tuning** completamente funcional
- [ ] **API de personalización** robusta
- [ ] **Interfaz de desarrollador** intuitiva
- [ ] **Modelos personalizados** funcionando
- [ ] **Testing suite** completa
- [ ] **Documentación** de personalización
- [ ] **Optimización** para hardware limitado
- [ ] **Preparación** para frontend

## 🚀 Siguiente Fase

Una vez completada esta fase, continuar con [**Fase 5: Frontend UI**](./05-frontend-ui.md)

### **📋 Preparación para Fase 5**
- [ ] Fine-tuning funcionando
- [ ] API de personalización estable
- [ ] Modelos personalizados operativos
- [ ] Testing completo
- [ ] Documentación actualizada

---

**🎉 ¡Con esta fase tendrás un asistente completamente personalizable!**

*Recuerda: La personalización es lo que hace único a tu asistente. Invierte el tiempo necesario para hacerlo bien.* 🚀
