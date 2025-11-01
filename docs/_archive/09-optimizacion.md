# ⚡ Fase 9: Optimización y Deploy
## Estado Actual
- Optimizaciones parciales: LLMManager usando modelos GGUF cuantizados (Mistral), MemoryLimiter activo, Health Checker y logs estructurados (`Assistant/src/logs/llm_structured.json`).
- Sin Docker en host; `docker-compose.yml` listo para futuros builds.
- Próximos pasos: profiling de rendimiento, métricas (Prometheus/Grafana), y CI/CD.

## 🎯 Objetivos de esta Fase

- **Optimizar rendimiento** del sistema completo
- **Cuantización de modelos** para hardware limitado
- **Estrategias de despliegue** multiplataforma
- **Monitoreo y métricas** en producción
- **Escalabilidad** y gestión de recursos
- **Testing de rendimiento** completo

## ⏱️ Tiempo Estimado

**2 semanas** (10 días de trabajo)

## 📋 Checklist de Tareas

### **Semana 1: Optimización de Rendimiento**
- [ ] **Día 1-2: Optimización de LLM**
  - [ ] Cuantización de modelos (INT8, INT4)
  - [x] Optimización de memoria
  - [ ] Batch processing optimizado
  - [ ] Cache inteligente de respuestas

- [ ] **Día 3-4: Optimización de Sistema**
  - [ ] Optimización de base de datos
  - [ ] Cache Redis optimizado
  - [ ] Compresión de datos
  - [x] Gestión de memoria

- [ ] **Día 5: Optimización de Frontend**
  - [ ] Bundle optimization
  - [ ] Lazy loading
  - [ ] Code splitting
  - [ ] Performance monitoring

### **Semana 2: Deploy y Producción**
- [ ] **Día 8-9: Monitoreo y Métricas**
  - [ ] Sistema de monitoreo
  - [ ] Métricas de rendimiento
  - [ ] Alertas automáticas
  - [x] Logs estructurados

- [ ] **Día 10: Testing y Validación**
  - [ ] Testing de rendimiento
  - [ ] Testing de carga
  - [ ] Validación de deploy
  - [ ] Documentación final

## 🔧 Herramientas Necesarias

### **Optimización**
- **ONNX**: Optimización de modelos
- **TensorRT**: Aceleración GPU
- **Quantization**: Cuantización de modelos
- **Profiling**: Análisis de rendimiento

### **Deploy**
- **Docker**: Contenedores
- **Docker Compose**: Orquestación
- **GitHub Actions**: CI/CD
- **Electron Builder**: Builds multiplataforma

### **Monitoreo**
- **Prometheus**: Métricas
- **Grafana**: Dashboards
- **ELK Stack**: Logs
- **Sentry**: Error tracking

## 🏗️ Arquitectura de Optimización

### **📐 Componentes de Optimización**

```
┌─────────────────────────────────────────────────────────────┐
│                    SISTEMA OPTIMIZADO                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   LLM       │  │   Cache     │  │  Database  │        │
│  │ Cuantizado  │  │ Inteligente │  │ Optimizada  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│         │                 │                 │              │
│         ▼                 ▼                 ▼              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Frontend   │  │  Backend    │  │  Monitoreo  │        │
│  │ Optimizado  │  │ Optimizado  │  │   Sistema   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Implementación

### **1. Optimización de LLM**

```python
# backend/app/optimization/llm_optimizer.py
import torch
import onnx
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Dict, Any, Optional
import numpy as np

class LLMOptimizer:
    """Optimizador de modelos LLM para hardware limitado"""
    
    def __init__(self, model_name: str = "mistral:7b"):
        self.model_name = model_name
        self.optimized_model = None
        self.quantized_model = None
    
    def quantize_model(self, quantization_type: str = "int8") -> Dict[str, Any]:
        """Cuantizar modelo para ahorrar memoria"""
        try:
            if quantization_type == "int8":
                return self._quantize_int8()
            elif quantization_type == "int4":
                return self._quantize_int4()
            elif quantization_type == "dynamic":
                return self._quantize_dynamic()
            else:
                raise ValueError(f"Tipo de cuantización no soportado: {quantization_type}")
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _quantize_int8(self) -> Dict[str, Any]:
        """Cuantización INT8 para ahorrar memoria"""
        try:
            # Cargar modelo
            model = AutoModelForCausalLM.from_pretrained(self.model_name)
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Configurar cuantización INT8
            quantized_model = torch.quantization.quantize_dynamic(
                model,
                {torch.nn.Linear},
                dtype=torch.qint8
            )
            
            # Guardar modelo cuantizado
            torch.save(quantized_model.state_dict(), "models/quantized_int8.pt")
            
            return {
                "success": True,
                "quantization_type": "int8",
                "memory_saved": "~50%",
                "model_path": "models/quantized_int8.pt"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _quantize_int4(self) -> Dict[str, Any]:
        """Cuantización INT4 para máxima compresión"""
        try:
            from transformers import BitsAndBytesConfig
            
            # Configuración de cuantización 4-bit
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
            
            # Cargar modelo cuantizado
            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=quantization_config,
                device_map="auto"
            )
            
            return {
                "success": True,
                "quantization_type": "int4",
                "memory_saved": "~75%",
                "model": model
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def optimize_for_hardware(self, hardware_config: Dict[str, Any]) -> Dict[str, Any]:
        """Optimizar modelo según hardware disponible"""
        try:
            memory_gb = hardware_config.get("total_memory", 0) / (1024**3)
            has_gpu = hardware_config.get("has_gpu", False)
            gpu_memory = hardware_config.get("gpu_memory", 0)
            
            optimization_config = {}
            
            if memory_gb < 4:
                # Hardware muy limitado
                optimization_config = {
                    "quantization": "int4",
                    "batch_size": 1,
                    "max_tokens": 512,
                    "gpu_layers": 0
                }
            elif memory_gb < 8:
                # Hardware limitado
                optimization_config = {
                    "quantization": "int8",
                    "batch_size": 2,
                    "max_tokens": 1024,
                    "gpu_layers": 5 if has_gpu else 0
                }
            else:
                # Hardware suficiente
                optimization_config = {
                    "quantization": "int8",
                    "batch_size": 4,
                    "max_tokens": 2048,
                    "gpu_layers": 20 if has_gpu else 0
                }
            
            return {
                "success": True,
                "optimization_config": optimization_config,
                "hardware_config": hardware_config
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_onnx_model(self) -> Dict[str, Any]:
        """Convertir modelo a ONNX para optimización"""
        try:
            # Cargar modelo
            model = AutoModelForCausalLM.from_pretrained(self.model_name)
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Configurar modelo para exportación
            model.eval()
            
            # Crear ejemplo de entrada
            dummy_input = tokenizer("Hello", return_tensors="pt")
            
            # Exportar a ONNX
            torch.onnx.export(
                model,
                dummy_input["input_ids"],
                "models/model.onnx",
                export_params=True,
                opset_version=11,
                do_constant_folding=True,
                input_names=["input_ids"],
                output_names=["logits"],
                dynamic_axes={
                    "input_ids": {0: "batch_size", 1: "sequence"},
                    "logits": {0: "batch_size", 1: "sequence"}
                }
            )
            
            return {
                "success": True,
                "onnx_model_path": "models/model.onnx",
                "optimization": "ONNX conversion completed"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
```

### **2. Sistema de Cache Inteligente**

```python
# backend/app/optimization/cache_optimizer.py
import redis
import json
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pickle

class IntelligentCache:
    """Sistema de cache inteligente para optimizar respuestas"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.cache_ttl = 3600  # 1 hora por defecto
        self.max_cache_size = 1000  # Máximo 1000 elementos
    
    def get_cache_key(self, prompt: str, user_id: str, context: str = "") -> str:
        """Generar clave de cache única"""
        # Normalizar prompt
        normalized_prompt = prompt.lower().strip()
        
        # Crear hash único
        content = f"{user_id}:{normalized_prompt}:{context}"
        hash_key = hashlib.md5(content.encode()).hexdigest()
        
        return f"cache:{hash_key}"
    
    async def get_cached_response(self, prompt: str, user_id: str, context: str = "") -> Optional[Dict[str, Any]]:
        """Obtener respuesta desde cache"""
        try:
            cache_key = self.get_cache_key(prompt, user_id, context)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                # Deserializar datos
                response_data = pickle.loads(cached_data)
                
                # Verificar si no ha expirado
                if response_data.get("expires_at", 0) > datetime.now().timestamp():
                    # Actualizar estadísticas
                    self._update_cache_stats(cache_key, "hit")
                    return response_data.get("response")
                else:
                    # Eliminar cache expirado
                    self.redis_client.delete(cache_key)
            
            self._update_cache_stats(cache_key, "miss")
            return None
            
        except Exception as e:
            print(f"Error obteniendo cache: {e}")
            return None
    
    async def cache_response(self, prompt: str, user_id: str, response: str, 
                           context: str = "", ttl: int = None) -> bool:
        """Guardar respuesta en cache"""
        try:
            cache_key = self.get_cache_key(prompt, user_id, context)
            ttl = ttl or self.cache_ttl
            
            # Preparar datos para cache
            cache_data = {
                "response": response,
                "prompt": prompt,
                "user_id": user_id,
                "context": context,
                "cached_at": datetime.now().timestamp(),
                "expires_at": datetime.now().timestamp() + ttl,
                "access_count": 0
            }
            
            # Serializar y guardar
            serialized_data = pickle.dumps(cache_data)
            self.redis_client.setex(cache_key, ttl, serialized_data)
            
            # Limpiar cache si es necesario
            await self._cleanup_cache()
            
            return True
            
        except Exception as e:
            print(f"Error guardando cache: {e}")
            return False
    
    async def _cleanup_cache(self):
        """Limpiar cache cuando excede el tamaño máximo"""
        try:
            # Obtener todas las claves de cache
            cache_keys = self.redis_client.keys("cache:*")
            
            if len(cache_keys) > self.max_cache_size:
                # Ordenar por tiempo de acceso (LRU)
                key_access_times = []
                for key in cache_keys:
                    data = self.redis_client.get(key)
                    if data:
                        cache_data = pickle.loads(data)
                        key_access_times.append((
                            key,
                            cache_data.get("access_count", 0),
                            cache_data.get("cached_at", 0)
                        ))
                
                # Ordenar por acceso (menos accedidos primero)
                key_access_times.sort(key=lambda x: (x[1], x[2]))
                
                # Eliminar los más antiguos
                keys_to_delete = key_access_times[:len(cache_keys) - self.max_cache_size]
                for key, _, _ in keys_to_delete:
                    self.redis_client.delete(key)
                    
        except Exception as e:
            print(f"Error limpiando cache: {e}")
    
    def _update_cache_stats(self, cache_key: str, operation: str):
        """Actualizar estadísticas de cache"""
        try:
            stats_key = f"stats:{cache_key}"
            self.redis_client.hincrby(stats_key, operation, 1)
            self.redis_client.expire(stats_key, 86400)  # 24 horas
        except Exception as e:
            print(f"Error actualizando estadísticas: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache"""
        try:
            cache_keys = self.redis_client.keys("cache:*")
            stats_keys = self.redis_client.keys("stats:*")
            
            total_hits = 0
            total_misses = 0
            
            for stats_key in stats_keys:
                stats = self.redis_client.hgetall(stats_key)
                total_hits += int(stats.get("hit", 0))
                total_misses += int(stats.get("miss", 0))
            
            hit_rate = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0
            
            return {
                "total_cached_items": len(cache_keys),
                "total_hits": total_hits,
                "total_misses": total_misses,
                "hit_rate": hit_rate,
                "cache_size_mb": self._get_cache_size_mb()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_cache_size_mb(self) -> float:
        """Obtener tamaño del cache en MB"""
        try:
            info = self.redis_client.info("memory")
            return info.get("used_memory", 0) / (1024 * 1024)
        except Exception as e:
            return 0.0
```

### **3. Optimización de Base de Datos**

```python
# backend/app/optimization/database_optimizer.py
import sqlite3
import asyncio
from typing import Dict, Any, List
import json
from datetime import datetime, timedelta

class DatabaseOptimizer:
    """Optimizador de base de datos para mejor rendimiento"""
    
    def __init__(self, db_path: str = "assistant.db"):
        self.db_path = db_path
        self._optimize_database()
    
    def _optimize_database(self):
        """Optimizar configuración de base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Configuraciones de optimización
            optimizations = [
                "PRAGMA journal_mode = WAL",  # Write-Ahead Logging
                "PRAGMA synchronous = NORMAL",  # Balance entre seguridad y velocidad
                "PRAGMA cache_size = 10000",  # Cache de 10MB
                "PRAGMA temp_store = MEMORY",  # Tablas temporales en memoria
                "PRAGMA mmap_size = 268435456",  # Memory mapping de 256MB
                "PRAGMA optimize"  # Optimización automática
            ]
            
            for optimization in optimizations:
                cursor.execute(optimization)
            
            conn.commit()
            conn.close()
            print("✅ Base de datos optimizada")
            
        except Exception as e:
            print(f"⚠️ Error optimizando base de datos: {e}")
    
    def create_indexes(self) -> Dict[str, Any]:
        """Crear índices para optimizar consultas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Índices para optimizar consultas frecuentes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_memories_user_id ON user_memories(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_memories_importance ON user_memories(importance)",
                "CREATE INDEX IF NOT EXISTS idx_memories_created_at ON user_memories(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_knowledge_embeddings ON knowledge_base(embedding_id)"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "indexes_created": len(indexes),
                "message": "Índices creados exitosamente"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_database(self) -> Dict[str, Any]:
        """Analizar rendimiento de la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Obtener estadísticas
            cursor.execute("PRAGMA table_info(user_memories)")
            memories_columns = len(cursor.fetchall())
            
            cursor.execute("SELECT COUNT(*) FROM user_memories")
            memories_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM conversations")
            conversations_count = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            db_size_mb = (page_count * page_size) / (1024 * 1024)
            
            conn.close()
            
            return {
                "success": True,
                "database_size_mb": round(db_size_mb, 2),
                "memories_count": memories_count,
                "conversations_count": conversations_count,
                "total_records": memories_count + conversations_count
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def cleanup_old_data(self, days_old: int = 30) -> Dict[str, Any]:
        """Limpiar datos antiguos para optimizar espacio"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Limpiar memorias antiguas de baja importancia
            cursor.execute("""
                DELETE FROM user_memories 
                WHERE created_at < ? AND importance < 0.3
            """, (cutoff_date.isoformat(),))
            
            memories_deleted = cursor.rowcount
            
            # Limpiar conversaciones antiguas
            cursor.execute("""
                DELETE FROM conversations 
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            conversations_deleted = cursor.rowcount
            
            # Vacuum para liberar espacio
            cursor.execute("VACUUM")
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "memories_deleted": memories_deleted,
                "conversations_deleted": conversations_deleted,
                "total_deleted": memories_deleted + conversations_deleted
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
```

### **4. Sistema de Monitoreo**

```python
# backend/app/monitoring/performance_monitor.py
import psutil
import time
import asyncio
from typing import Dict, Any, List
from datetime import datetime
import json
import threading

class PerformanceMonitor:
    """Monitor de rendimiento del sistema"""
    
    def __init__(self):
        self.metrics = {}
        self.alerts = []
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self, interval: int = 30):
        """Iniciar monitoreo continuo"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        print("✅ Monitoreo de rendimiento iniciado")
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("⏹️ Monitoreo de rendimiento detenido")
    
    def _monitor_loop(self, interval: int):
        """Loop principal de monitoreo"""
        while self.monitoring:
            try:
                metrics = self._collect_metrics()
                self._process_metrics(metrics)
                time.sleep(interval)
            except Exception as e:
                print(f"Error en monitoreo: {e}")
                time.sleep(interval)
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """Recopilar métricas del sistema"""
        try:
            # Métricas de CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Métricas de memoria
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available / (1024**3)  # GB
            
            # Métricas de disco
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free = disk.free / (1024**3)  # GB
            
            # Métricas de red
            network = psutil.net_io_counters()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count
                },
                "memory": {
                    "percent": memory_percent,
                    "available_gb": round(memory_available, 2),
                    "total_gb": round(memory.total / (1024**3), 2)
                },
                "disk": {
                    "percent": disk_percent,
                    "free_gb": round(disk_free, 2)
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _process_metrics(self, metrics: Dict[str, Any]):
        """Procesar métricas y generar alertas"""
        if "error" in metrics:
            return
        
        # Guardar métricas
        timestamp = metrics["timestamp"]
        self.metrics[timestamp] = metrics
        
        # Verificar alertas
        self._check_alerts(metrics)
        
        # Limpiar métricas antiguas (mantener solo 24 horas)
        self._cleanup_old_metrics()
    
    def _check_alerts(self, metrics: Dict[str, Any]):
        """Verificar condiciones de alerta"""
        alerts = []
        
        # Alerta de CPU alto
        if metrics["cpu"]["percent"] > 80:
            alerts.append({
                "type": "cpu_high",
                "message": f"CPU usage: {metrics['cpu']['percent']}%",
                "severity": "warning"
            })
        
        # Alerta de memoria alta
        if metrics["memory"]["percent"] > 85:
            alerts.append({
                "type": "memory_high",
                "message": f"Memory usage: {metrics['memory']['percent']}%",
                "severity": "critical"
            })
        
        # Alerta de disco lleno
        if metrics["disk"]["percent"] > 90:
            alerts.append({
                "type": "disk_full",
                "message": f"Disk usage: {metrics['disk']['percent']}%",
                "severity": "critical"
            })
        
        # Guardar alertas
        for alert in alerts:
            alert["timestamp"] = metrics["timestamp"]
            self.alerts.append(alert)
    
    def _cleanup_old_metrics(self):
        """Limpiar métricas antiguas"""
        cutoff_time = datetime.now().timestamp() - 86400  # 24 horas
        
        old_keys = []
        for timestamp_str, _ in self.metrics.items():
            timestamp = datetime.fromisoformat(timestamp_str).timestamp()
            if timestamp < cutoff_time:
                old_keys.append(timestamp_str)
        
        for key in old_keys:
            del self.metrics[key]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Obtener resumen de rendimiento"""
        if not self.metrics:
            return {"message": "No hay métricas disponibles"}
        
        # Calcular promedios
        cpu_values = [m["cpu"]["percent"] for m in self.metrics.values()]
        memory_values = [m["memory"]["percent"] for m in self.metrics.values()]
        
        return {
            "monitoring_active": self.monitoring,
            "total_metrics": len(self.metrics),
            "average_cpu": round(sum(cpu_values) / len(cpu_values), 2),
            "average_memory": round(sum(memory_values) / len(memory_values), 2),
            "max_cpu": max(cpu_values),
            "max_memory": max(memory_values),
            "alerts_count": len(self.alerts),
            "recent_alerts": self.alerts[-5:] if self.alerts else []
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Obtener estado de salud del sistema"""
        try:
            current_metrics = self._collect_metrics()
            
            health_score = 100
            
            # Penalizar por CPU alto
            if current_metrics["cpu"]["percent"] > 70:
                health_score -= 20
            elif current_metrics["cpu"]["percent"] > 50:
                health_score -= 10
            
            # Penalizar por memoria alta
            if current_metrics["memory"]["percent"] > 80:
                health_score -= 30
            elif current_metrics["memory"]["percent"] > 60:
                health_score -= 15
            
            # Penalizar por disco lleno
            if current_metrics["disk"]["percent"] > 85:
                health_score -= 25
            elif current_metrics["disk"]["percent"] > 70:
                health_score -= 10
            
            # Determinar estado
            if health_score >= 80:
                status = "healthy"
            elif health_score >= 60:
                status = "warning"
            else:
                status = "critical"
            
            return {
                "status": status,
                "health_score": health_score,
                "current_metrics": current_metrics,
                "recommendations": self._get_recommendations(current_metrics)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _get_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Obtener recomendaciones de optimización"""
        recommendations = []
        
        if metrics["cpu"]["percent"] > 70:
            recommendations.append("Considerar optimizar procesos o reducir carga de trabajo")
        
        if metrics["memory"]["percent"] > 80:
            recommendations.append("Considerar aumentar memoria o optimizar uso de memoria")
        
        if metrics["disk"]["percent"] > 85:
            recommendations.append("Considerar limpiar archivos temporales o aumentar espacio en disco")
        
        if not recommendations:
            recommendations.append("Sistema funcionando correctamente")
        
        return recommendations
```

### **5. Estrategias de Deploy**

```python
# deploy/docker_optimizer.py
import docker
import os
from typing import Dict, Any, List
import json

class DockerOptimizer:
    """Optimizador de contenedores Docker"""
    
    def __init__(self):
        self.client = docker.from_env()
    
    def create_optimized_dockerfile(self, base_image: str = "python:3.11-slim") -> str:
        """Crear Dockerfile optimizado"""
        dockerfile_content = f"""
# Dockerfile optimizado para asistente de IA
FROM {base_image}

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN useradd -m -u 1000 assistant

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements primero (para cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Cambiar a usuario no-root
USER assistant

# Exponer puerto
EXPOSE 8000

# Comando de inicio
CMD ["python", "main.py"]
"""
        return dockerfile_content
    
    def create_docker_compose(self) -> str:
        """Crear docker-compose.yml optimizado"""
        compose_content = """
version: '3.8'

services:
  assistant-backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    volumes:
      - ./models:/app/models
      - ./data:/app/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - assistant-backend
    restart: unless-stopped

volumes:
  redis_data:
"""
        return compose_content
    
    def create_nginx_config(self) -> str:
        """Crear configuración de Nginx optimizada"""
        nginx_config = """
events {
    worker_connections 1024;
}

http {
    upstream assistant_backend {
        server assistant-backend:8000;
    }

    # Configuración de cache
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=assistant_cache:10m max_size=1g inactive=60m;

    server {
        listen 80;
        server_name localhost;

        # Configuración de proxy
        location / {
            proxy_pass http://assistant_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Cache de respuestas
            proxy_cache assistant_cache;
            proxy_cache_valid 200 302 10m;
            proxy_cache_valid 404 1m;
        }

        # Configuración de WebSocket
        location /ws {
            proxy_pass http://assistant_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
    }
}
"""
        return nginx_config

## 📊 Métricas de Éxito

### **🎯 Objetivos Técnicos**
- **Rendimiento**: < 2s respuesta promedio
- **Memoria**: < 2GB uso total
- **CPU**: < 70% uso promedio
- **Cache Hit Rate**: > 80%
- **Uptime**: > 99.5%

### **🎯 Objetivos de Funcionalidad**
- **Optimización**: Modelos cuantizados funcionando
- **Cache**: Sistema de cache operativo
- **Monitoreo**: Métricas en tiempo real
- **Deploy**: Contenedores optimizados
- **Testing**: > 90% cobertura de código

## ✅ Criterios de Éxito

### **📋 Checklist de Validación**
- [ ] **Modelos cuantizados** funcionando
- [ ] **Sistema de cache** operativo
- [ ] **Base de datos optimizada** con índices
- [ ] **Monitoreo** configurado y funcionando
- [ ] **Contenedores Docker** optimizados
- [ ] **Testing de rendimiento** completado
- [ ] **Documentación** de deploy actualizada

---

**🎉 ¡Con esta fase tendrás un sistema optimizado y listo para producción!**

*Recuerda: La optimización es clave para un rendimiento excelente en hardware limitado.* 🚀

