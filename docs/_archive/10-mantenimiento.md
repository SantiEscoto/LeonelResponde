# 🔧 Fase 10: Mantenimiento y Evolución
## Estado Actual
- Mantenimiento básico en marcha: verificación manual de logs y health checks, con `llm_structured.json` y HealthChecker.
- Sin sistema de métricas/alertas (Prometheus/Grafana/Sentry) aún; backups y actualizaciones pendientes.
- Próximos pasos: tareas programadas (cron), alertas, y documentación de procedimientos.

## 🎯 Objetivos de esta Fase

- **Estrategias de mantenimiento** a largo plazo
- **Sistema de actualizaciones** automáticas
- **Monitoreo continuo** y alertas
- **Backup y recuperación** de datos
- **Evolución del sistema** y nuevas funcionalidades
- **Documentación** y transferencia de conocimiento

## ⏱️ Tiempo Estimado

**Ongoing** (Mantenimiento continuo)

## 📋 Checklist de Tareas

### **Mantenimiento Diario**
- [ ] **Monitoreo del sistema** (CPU, memoria, disco)
- [x] **Verificación de logs** de errores
- [ ] **Backup automático** de datos
- [ ] **Actualizaciones de seguridad**

### **Mantenimiento Semanal**
- [ ] **Análisis de rendimiento** del sistema
- [ ] **Limpieza de datos** antiguos
- [ ] **Verificación de dependencias**
- [ ] **Testing de funcionalidades**

### **Mantenimiento Mensual**
- [ ] **Actualización de modelos** de IA
- [ ] **Optimización de base de datos**
- [ ] **Revisión de seguridad**
- [ ] **Análisis de uso y métricas**

### **Evolución Trimestral**
- [ ] **Evaluación de nuevas tecnologías**
- [ ] **Planificación de mejoras**
- [ ] **Actualización de documentación**
- [ ] **Capacitación del equipo**

## 🔧 Herramientas Necesarias

### **Monitoreo y Alertas**
- **Prometheus**: Métricas y monitoreo
- **Grafana**: Dashboards y visualización
- **ELK Stack**: Logs centralizados
- **Sentry**: Error tracking
- **Uptime Robot**: Monitoreo externo

### **Backup y Recuperación**
- **rsync**: Sincronización de archivos
- **pg_dump**: Backup de PostgreSQL
- **Redis RDB**: Backup de Redis
- **S3/MinIO**: Almacenamiento en la nube

### **Automatización**
- **GitHub Actions**: CI/CD
- **Cron**: Tareas programadas
- **Ansible**: Automatización de infraestructura
- **Docker**: Contenedores

## 🏗️ Arquitectura de Mantenimiento

### **📐 Componentes de Mantenimiento**

```
┌─────────────────────────────────────────────────────────────┐
│                    SISTEMA DE MANTENIMIENTO               │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Monitoreo   │  │   Backup    │  │ Actualiz.   │        │
│  │ Continuo    │  │ Automático  │  │ Automáticas │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│         │                 │                 │              │
│         ▼                 ▼                 ▼              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Alertas   │  │ Recuperación │  │   Testing   │        │
│  │ Automáticas │  │   de Datos   │  │ Continuo    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Implementación

### **1. Sistema de Monitoreo Avanzado**

```python
# backend/app/monitoring/advanced_monitor.py
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import psutil
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class AdvancedMonitor:
    """Monitor avanzado con alertas y métricas detalladas"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics_history = []
        self.alerts_sent = []
        self.health_checks = []
    
    async def start_comprehensive_monitoring(self):
        """Iniciar monitoreo comprensivo del sistema"""
        tasks = [
            self._monitor_system_resources(),
            self._monitor_application_health(),
            self._monitor_database_performance(),
            self._monitor_ai_models(),
            self._monitor_user_activity(),
            self._check_security_alerts()
        ]
        
        await asyncio.gather(*tasks)
    
    async def _monitor_system_resources(self):
        """Monitorear recursos del sistema"""
        while True:
            try:
                # CPU
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_freq = psutil.cpu_freq()
                
                # Memoria
                memory = psutil.virtual_memory()
                swap = psutil.swap_memory()
                
                # Disco
                disk = psutil.disk_usage('/')
                disk_io = psutil.disk_io_counters()
                
                # Red
                network = psutil.net_io_counters()
                
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu": {
                        "percent": cpu_percent,
                        "frequency": cpu_freq.current if cpu_freq else None,
                        "count": psutil.cpu_count()
                    },
                    "memory": {
                        "total": memory.total,
                        "available": memory.available,
                        "percent": memory.percent,
                        "swap_total": swap.total,
                        "swap_used": swap.used
                    },
                    "disk": {
                        "total": disk.total,
                        "used": disk.used,
                        "free": disk.free,
                        "percent": disk.percent
                    },
                    "network": {
                        "bytes_sent": network.bytes_sent,
                        "bytes_recv": network.bytes_recv,
                        "packets_sent": network.packets_sent,
                        "packets_recv": network.packets_recv
                    }
                }
                
                # Verificar alertas
                await self._check_resource_alerts(metrics)
                
                # Guardar métricas
                self.metrics_history.append(metrics)
                
                # Limpiar historial antiguo
                self._cleanup_old_metrics()
                
                await asyncio.sleep(30)  # Verificar cada 30 segundos
                
            except Exception as e:
                print(f"Error en monitoreo de recursos: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_application_health(self):
        """Monitorear salud de la aplicación"""
        while True:
            try:
                # Verificar endpoints
                health_checks = await self._perform_health_checks()
                
                # Verificar servicios
                services_status = await self._check_services_status()
                
                # Verificar dependencias
                dependencies_status = await self._check_dependencies()
                
                health_metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "health_checks": health_checks,
                    "services": services_status,
                    "dependencies": dependencies_status,
                    "overall_health": self._calculate_overall_health(health_checks, services_status, dependencies_status)
                }
                
                # Verificar alertas de salud
                await self._check_health_alerts(health_metrics)
                
                await asyncio.sleep(60)  # Verificar cada minuto
                
            except Exception as e:
                print(f"Error en monitoreo de salud: {e}")
                await asyncio.sleep(120)
    
    async def _perform_health_checks(self) -> Dict[str, Any]:
        """Realizar verificaciones de salud"""
        checks = {}
        
        try:
            # Verificar API principal
            response = requests.get("http://localhost:8000/health", timeout=5)
            checks["api"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            checks["api"] = {"status": "unhealthy", "error": str(e)}
        
        try:
            # Verificar base de datos
            # (Implementar verificación de DB)
            checks["database"] = {"status": "healthy"}
        except Exception as e:
            checks["database"] = {"status": "unhealthy", "error": str(e)}
        
        try:
            # Verificar Redis
            # (Implementar verificación de Redis)
            checks["redis"] = {"status": "healthy"}
        except Exception as e:
            checks["redis"] = {"status": "unhealthy", "error": str(e)}
        
        return checks
    
    async def _check_services_status(self) -> Dict[str, Any]:
        """Verificar estado de servicios"""
        services = {}
        
        # Verificar procesos Python
        python_processes = [p for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']) 
                           if 'python' in p.info['name'].lower()]
        
        services["python_processes"] = {
            "count": len(python_processes),
            "total_cpu": sum(p.info['cpu_percent'] for p in python_processes),
            "total_memory": sum(p.info['memory_percent'] for p in python_processes)
        }
        
        return services
    
    async def _check_dependencies(self) -> Dict[str, Any]:
        """Verificar dependencias externas"""
        dependencies = {}
        
        # Verificar conectividad a internet
        try:
            response = requests.get("https://www.google.com", timeout=5)
            dependencies["internet"] = {"status": "connected"}
        except Exception as e:
            dependencies["internet"] = {"status": "disconnected", "error": str(e)}
        
        return dependencies
    
    def _calculate_overall_health(self, health_checks: Dict, services: Dict, dependencies: Dict) -> str:
        """Calcular salud general del sistema"""
        unhealthy_count = 0
        total_checks = 0
        
        for check in health_checks.values():
            total_checks += 1
            if check.get("status") == "unhealthy":
                unhealthy_count += 1
        
        if unhealthy_count == 0:
            return "healthy"
        elif unhealthy_count / total_checks < 0.5:
            return "warning"
        else:
            return "critical"
    
    async def _check_resource_alerts(self, metrics: Dict[str, Any]):
        """Verificar alertas de recursos"""
        alerts = []
        
        # Alerta de CPU
        if metrics["cpu"]["percent"] > 90:
            alerts.append({
                "type": "cpu_critical",
                "message": f"CPU usage critical: {metrics['cpu']['percent']}%",
                "severity": "critical"
            })
        elif metrics["cpu"]["percent"] > 80:
            alerts.append({
                "type": "cpu_high",
                "message": f"CPU usage high: {metrics['cpu']['percent']}%",
                "severity": "warning"
            })
        
        # Alerta de memoria
        if metrics["memory"]["percent"] > 95:
            alerts.append({
                "type": "memory_critical",
                "message": f"Memory usage critical: {metrics['memory']['percent']}%",
                "severity": "critical"
            })
        elif metrics["memory"]["percent"] > 85:
            alerts.append({
                "type": "memory_high",
                "message": f"Memory usage high: {metrics['memory']['percent']}%",
                "severity": "warning"
            })
        
        # Alerta de disco
        if metrics["disk"]["percent"] > 95:
            alerts.append({
                "type": "disk_critical",
                "message": f"Disk usage critical: {metrics['disk']['percent']}%",
                "severity": "critical"
            })
        elif metrics["disk"]["percent"] > 90:
            alerts.append({
                "type": "disk_high",
                "message": f"Disk usage high: {metrics['disk']['percent']}%",
                "severity": "warning"
            })
        
        # Enviar alertas
        for alert in alerts:
            await self._send_alert(alert)
    
    async def _check_health_alerts(self, health_metrics: Dict[str, Any]):
        """Verificar alertas de salud"""
        if health_metrics["overall_health"] == "critical":
            alert = {
                "type": "system_critical",
                "message": "System health is critical",
                "severity": "critical",
                "details": health_metrics
            }
            await self._send_alert(alert)
        elif health_metrics["overall_health"] == "warning":
            alert = {
                "type": "system_warning",
                "message": "System health is degraded",
                "severity": "warning",
                "details": health_metrics
            }
            await self._send_alert(alert)
    
    async def _send_alert(self, alert: Dict[str, Any]):
        """Enviar alerta por email/SMS"""
        try:
            # Verificar si ya se envió esta alerta recientemente
            alert_key = f"{alert['type']}_{alert['severity']}"
            if alert_key in self.alerts_sent:
                last_sent = self.alerts_sent[alert_key]
                if datetime.now() - last_sent < timedelta(hours=1):
                    return  # No enviar la misma alerta por 1 hora
            
            # Enviar email
            await self._send_email_alert(alert)
            
            # Registrar alerta enviada
            self.alerts_sent[alert_key] = datetime.now()
            
        except Exception as e:
            print(f"Error enviando alerta: {e}")
    
    async def _send_email_alert(self, alert: Dict[str, Any]):
        """Enviar alerta por email"""
        try:
            # Configurar email
            smtp_server = self.config.get("smtp_server", "smtp.gmail.com")
            smtp_port = self.config.get("smtp_port", 587)
            email_user = self.config.get("email_user")
            email_password = self.config.get("email_password")
            email_to = self.config.get("email_to")
            
            if not all([email_user, email_password, email_to]):
                print("Configuración de email incompleta")
                return
            
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = email_user
            msg['To'] = email_to
            msg['Subject'] = f"ALERTA: {alert['type'].upper()}"
            
            body = f"""
            Alerta del Sistema de Asistente de IA
            
            Tipo: {alert['type']}
            Severidad: {alert['severity']}
            Mensaje: {alert['message']}
            Timestamp: {datetime.now().isoformat()}
            
            Detalles: {json.dumps(alert.get('details', {}), indent=2)}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Enviar email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_user, email_password)
            text = msg.as_string()
            server.sendmail(email_user, email_to, text)
            server.quit()
            
            print(f"Alerta enviada: {alert['type']}")
            
        except Exception as e:
            print(f"Error enviando email: {e}")
    
    def _cleanup_old_metrics(self):
        """Limpiar métricas antiguas"""
        cutoff_time = datetime.now() - timedelta(days=7)  # Mantener 7 días
        
        self.metrics_history = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"]) > cutoff_time
        ]
    
    async def _monitor_database_performance(self):
        """Monitorear rendimiento de base de datos"""
        while True:
            try:
                # Implementar monitoreo de DB
                # - Tamaño de tablas
                # - Consultas lentas
                # - Conexiones activas
                # - Índices fragmentados
                
                await asyncio.sleep(300)  # Verificar cada 5 minutos
                
            except Exception as e:
                print(f"Error monitoreando DB: {e}")
                await asyncio.sleep(600)
    
    async def _monitor_ai_models(self):
        """Monitorear modelos de IA"""
        while True:
            try:
                # Implementar monitoreo de modelos
                # - Tiempo de respuesta
                # - Uso de memoria
                # - Precisión de respuestas
                # - Errores de inferencia
                
                await asyncio.sleep(600)  # Verificar cada 10 minutos
                
            except Exception as e:
                print(f"Error monitoreando modelos: {e}")
                await asyncio.sleep(1200)
    
    async def _monitor_user_activity(self):
        """Monitorear actividad de usuarios"""
        while True:
            try:
                # Implementar monitoreo de usuarios
                # - Usuarios activos
                # - Consultas por minuto
                # - Errores de usuario
                # - Satisfacción
                
                await asyncio.sleep(60)  # Verificar cada minuto
                
            except Exception as e:
                print(f"Error monitoreando usuarios: {e}")
                await asyncio.sleep(300)
    
    async def _check_security_alerts(self):
        """Verificar alertas de seguridad"""
        while True:
            try:
                # Implementar verificaciones de seguridad
                # - Intentos de acceso
                # - Patrones sospechosos
                # - Vulnerabilidades
                # - Logs de seguridad
                
                await asyncio.sleep(3600)  # Verificar cada hora
                
            except Exception as e:
                print(f"Error verificando seguridad: {e}")
                await asyncio.sleep(7200)
```

### **2. Sistema de Backup Automático**

```python
# backend/app/backup/backup_manager.py
import os
import shutil
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
import subprocess
import tarfile
import gzip

class BackupManager:
    """Gestor de backup automático"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backup_dir = config.get("backup_dir", "./backups")
        self.retention_days = config.get("retention_days", 30)
        self.s3_bucket = config.get("s3_bucket")
        self.s3_region = config.get("s3_region", "us-east-1")
    
    async def create_full_backup(self) -> Dict[str, Any]:
        """Crear backup completo del sistema"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"full_backup_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Crear directorio de backup
            os.makedirs(backup_path, exist_ok=True)
            
            # Backup de base de datos
            await self._backup_database(backup_path)
            
            # Backup de archivos de configuración
            await self._backup_config_files(backup_path)
            
            # Backup de modelos
            await self._backup_models(backup_path)
            
            # Backup de logs
            await self._backup_logs(backup_path)
            
            # Backup de datos de usuario
            await self._backup_user_data(backup_path)
            
            # Comprimir backup
            compressed_path = await self._compress_backup(backup_path)
            
            # Subir a S3 si está configurado
            if self.s3_bucket:
                await self._upload_to_s3(compressed_path)
            
            # Limpiar backups antiguos
            await self._cleanup_old_backups()
            
            return {
                "success": True,
                "backup_path": compressed_path,
                "size_mb": os.path.getsize(compressed_path) / (1024 * 1024),
                "timestamp": timestamp
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _backup_database(self, backup_path: str):
        """Backup de base de datos"""
        try:
            db_path = self.config.get("database_path", "assistant.db")
            backup_db_path = os.path.join(backup_path, "database.db")
            
            # Copiar archivo de base de datos
            shutil.copy2(db_path, backup_db_path)
            
            # Exportar datos en formato SQL
            sql_path = os.path.join(backup_path, "database.sql")
            subprocess.run([
                "sqlite3", db_path, ".dump"
            ], stdout=open(sql_path, 'w'))
            
            print("✅ Base de datos respaldada")
            
        except Exception as e:
            print(f"⚠️ Error respaldando base de datos: {e}")
    
    async def _backup_config_files(self, backup_path: str):
        """Backup de archivos de configuración"""
        try:
            config_dir = os.path.join(backup_path, "config")
            os.makedirs(config_dir, exist_ok=True)
            
            # Archivos de configuración importantes
            config_files = [
                "config.json",
                ".env",
                "requirements.txt",
                "docker-compose.yml",
                "Dockerfile"
            ]
            
            for file in config_files:
                if os.path.exists(file):
                    shutil.copy2(file, os.path.join(config_dir, file))
            
            print("✅ Archivos de configuración respaldados")
            
        except Exception as e:
            print(f"⚠️ Error respaldando configuración: {e}")
    
    async def _backup_models(self, backup_path: str):
        """Backup de modelos de IA"""
        try:
            models_dir = os.path.join(backup_path, "models")
            source_models_dir = self.config.get("models_dir", "./models")
            
            if os.path.exists(source_models_dir):
                shutil.copytree(source_models_dir, models_dir)
                print("✅ Modelos respaldados")
            else:
                print("⚠️ Directorio de modelos no encontrado")
                
        except Exception as e:
            print(f"⚠️ Error respaldando modelos: {e}")
    
    async def _backup_logs(self, backup_path: str):
        """Backup de logs"""
        try:
            logs_dir = os.path.join(backup_path, "logs")
            source_logs_dir = self.config.get("logs_dir", "./logs")
            
            if os.path.exists(source_logs_dir):
                shutil.copytree(source_logs_dir, logs_dir)
                print("✅ Logs respaldados")
            else:
                print("⚠️ Directorio de logs no encontrado")
                
        except Exception as e:
            print(f"⚠️ Error respaldando logs: {e}")
    
    async def _backup_user_data(self, backup_path: str):
        """Backup de datos de usuario"""
        try:
            user_data_dir = os.path.join(backup_path, "user_data")
            source_user_data_dir = self.config.get("user_data_dir", "./data")
            
            if os.path.exists(source_user_data_dir):
                shutil.copytree(source_user_data_dir, user_data_dir)
                print("✅ Datos de usuario respaldados")
            else:
                print("⚠️ Directorio de datos de usuario no encontrado")
                
        except Exception as e:
            print(f"⚠️ Error respaldando datos de usuario: {e}")
    
    async def _compress_backup(self, backup_path: str) -> str:
        """Comprimir backup"""
        try:
            compressed_path = f"{backup_path}.tar.gz"
            
            with tarfile.open(compressed_path, "w:gz") as tar:
                tar.add(backup_path, arcname=os.path.basename(backup_path))
            
            # Eliminar directorio sin comprimir
            shutil.rmtree(backup_path)
            
            print(f"✅ Backup comprimido: {compressed_path}")
            return compressed_path
            
        except Exception as e:
            print(f"⚠️ Error comprimiendo backup: {e}")
            return backup_path
    
    async def _upload_to_s3(self, file_path: str):
        """Subir backup a S3"""
        try:
            import boto3
            
            s3_client = boto3.client(
                's3',
                region_name=self.s3_region,
                aws_access_key_id=self.config.get("aws_access_key_id"),
                aws_secret_access_key=self.config.get("aws_secret_access_key")
            )
            
            file_name = os.path.basename(file_path)
            s3_key = f"backups/{file_name}"
            
            s3_client.upload_file(file_path, self.s3_bucket, s3_key)
            
            print(f"✅ Backup subido a S3: s3://{self.s3_bucket}/{s3_key}")
            
        except Exception as e:
            print(f"⚠️ Error subiendo a S3: {e}")
    
    async def _cleanup_old_backups(self):
        """Limpiar backups antiguos"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            for file in os.listdir(self.backup_dir):
                file_path = os.path.join(self.backup_dir, file)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_date:
                        os.remove(file_path)
                        print(f"🗑️ Backup antiguo eliminado: {file}")
            
        except Exception as e:
            print(f"⚠️ Error limpiando backups antiguos: {e}")
    
    async def restore_backup(self, backup_path: str) -> Dict[str, Any]:
        """Restaurar backup"""
        try:
            # Descomprimir backup
            extract_path = backup_path.replace('.tar.gz', '_extracted')
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(os.path.dirname(extract_path))
            
            # Restaurar base de datos
            await self._restore_database(extract_path)
            
            # Restaurar archivos de configuración
            await self._restore_config_files(extract_path)
            
            # Restaurar modelos
            await self._restore_models(extract_path)
            
            # Restaurar datos de usuario
            await self._restore_user_data(extract_path)
            
            # Limpiar archivos temporales
            shutil.rmtree(extract_path)
            
            return {
                "success": True,
                "message": "Backup restaurado exitosamente"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _restore_database(self, extract_path: str):
        """Restaurar base de datos"""
        try:
            db_path = self.config.get("database_path", "assistant.db")
            backup_db_path = os.path.join(extract_path, "database.db")
            
            if os.path.exists(backup_db_path):
                shutil.copy2(backup_db_path, db_path)
                print("✅ Base de datos restaurada")
            else:
                print("⚠️ Archivo de base de datos no encontrado en backup")
                
        except Exception as e:
            print(f"⚠️ Error restaurando base de datos: {e}")
    
    async def _restore_config_files(self, extract_path: str):
        """Restaurar archivos de configuración"""
        try:
            config_dir = os.path.join(extract_path, "config")
            
            if os.path.exists(config_dir):
                for file in os.listdir(config_dir):
                    source_file = os.path.join(config_dir, file)
                    shutil.copy2(source_file, file)
                print("✅ Archivos de configuración restaurados")
            else:
                print("⚠️ Directorio de configuración no encontrado en backup")
                
        except Exception as e:
            print(f"⚠️ Error restaurando configuración: {e}")
    
    async def _restore_models(self, extract_path: str):
        """Restaurar modelos"""
        try:
            models_dir = os.path.join(extract_path, "models")
            target_models_dir = self.config.get("models_dir", "./models")
            
            if os.path.exists(models_dir):
                if os.path.exists(target_models_dir):
                    shutil.rmtree(target_models_dir)
                shutil.copytree(models_dir, target_models_dir)
                print("✅ Modelos restaurados")
            else:
                print("⚠️ Directorio de modelos no encontrado en backup")
                
        except Exception as e:
            print(f"⚠️ Error restaurando modelos: {e}")
    
    async def _restore_user_data(self, extract_path: str):
        """Restaurar datos de usuario"""
        try:
            user_data_dir = os.path.join(extract_path, "user_data")
            target_user_data_dir = self.config.get("user_data_dir", "./data")
            
            if os.path.exists(user_data_dir):
                if os.path.exists(target_user_data_dir):
                    shutil.rmtree(target_user_data_dir)
                shutil.copytree(user_data_dir, target_user_data_dir)
                print("✅ Datos de usuario restaurados")
            else:
                print("⚠️ Directorio de datos de usuario no encontrado en backup")
                
        except Exception as e:
            print(f"⚠️ Error restaurando datos de usuario: {e}")
```

### **3. Sistema de Actualizaciones Automáticas**

```python
# backend/app/updates/update_manager.py
import asyncio
import json
import subprocess
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
import git
import os

class UpdateManager:
    """Gestor de actualizaciones automáticas"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.repo_path = config.get("repo_path", ".")
        self.auto_update = config.get("auto_update", False)
        self.update_channel = config.get("update_channel", "stable")
        self.github_repo = config.get("github_repo")
        self.current_version = self._get_current_version()
    
    def _get_current_version(self) -> str:
        """Obtener versión actual"""
        try:
            with open("version.json", "r") as f:
                version_data = json.load(f)
                return version_data.get("version", "1.0.0")
        except:
            return "1.0.0"
    
    async def check_for_updates(self) -> Dict[str, Any]:
        """Verificar actualizaciones disponibles"""
        try:
            if not self.github_repo:
                return {"error": "GitHub repository not configured"}
            
            # Obtener información de releases
            releases_url = f"https://api.github.com/repos/{self.github_repo}/releases"
            response = requests.get(releases_url)
            
            if response.status_code != 200:
                return {"error": "Failed to fetch releases"}
            
            releases = response.json()
            latest_release = releases[0] if releases else None
            
            if not latest_release:
                return {"error": "No releases found"}
            
            latest_version = latest_release["tag_name"]
            current_version = self.current_version
            
            # Comparar versiones
            is_update_available = self._compare_versions(current_version, latest_version)
            
            return {
                "current_version": current_version,
                "latest_version": latest_version,
                "update_available": is_update_available,
                "release_notes": latest_release.get("body", ""),
                "published_at": latest_release.get("published_at", ""),
                "download_url": latest_release.get("zipball_url", "")
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _compare_versions(self, current: str, latest: str) -> bool:
        """Comparar versiones"""
        try:
            current_parts = [int(x) for x in current.split('.')]
            latest_parts = [int(x) for x in latest.split('.')]
            
            return latest_parts > current_parts
        except:
            return False
    
    async def update_system(self, version: str = None) -> Dict[str, Any]:
        """Actualizar sistema"""
        try:
            if not self.auto_update:
                return {"error": "Auto-update is disabled"}
            
            # Crear backup antes de actualizar
            backup_manager = BackupManager(self.config)
            backup_result = await backup_manager.create_full_backup()
            
            if not backup_result["success"]:
                return {"error": "Failed to create backup before update"}
            
            # Actualizar código
            update_result = await self._update_code(version)
            
            if not update_result["success"]:
                # Restaurar backup si falla la actualización
                await backup_manager.restore_backup(backup_result["backup_path"])
                return {"error": "Update failed, system restored from backup"}
            
            # Actualizar dependencias
            deps_result = await self._update_dependencies()
            
            if not deps_result["success"]:
                return {"error": "Failed to update dependencies"}
            
            # Reiniciar servicios
            restart_result = await self._restart_services()
            
            if not restart_result["success"]:
                return {"error": "Failed to restart services"}
            
            return {
                "success": True,
                "message": "System updated successfully",
                "new_version": version or "latest",
                "backup_path": backup_result["backup_path"]
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _update_code(self, version: str = None) -> Dict[str, Any]:
        """Actualizar código del sistema"""
        try:
            repo = git.Repo(self.repo_path)
            
            # Obtener cambios remotos
            origin = repo.remotes.origin
            origin.fetch()
            
            # Cambiar a la versión especificada
            if version:
                repo.git.checkout(version)
            else:
                # Cambiar a la rama principal
                repo.git.checkout("main")
                repo.git.pull()
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _update_dependencies(self) -> Dict[str, Any]:
        """Actualizar dependencias"""
        try:
            # Actualizar requirements.txt
            subprocess.run([
                "pip", "install", "-r", "requirements.txt", "--upgrade"
            ], check=True)
            
            return {"success": True}
            
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": str(e)}
    
    async def _restart_services(self) -> Dict[str, Any]:
        """Reiniciar servicios"""
        try:
            # Reiniciar servicios usando systemd o docker-compose
            if os.path.exists("docker-compose.yml"):
                subprocess.run(["docker-compose", "restart"], check=True)
            else:
                # Reiniciar servicios del sistema
                subprocess.run(["sudo", "systemctl", "restart", "assistant"], check=True)
            
            return {"success": True}
            
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": str(e)}
    
    async def schedule_auto_update(self):
        """Programar actualización automática"""
        try:
            while True:
                # Verificar actualizaciones cada 24 horas
                await asyncio.sleep(86400)
                
                update_info = await self.check_for_updates()
                
                if update_info.get("update_available"):
                    print(f"Update available: {update_info['latest_version']}")
                    
                    if self.auto_update:
                        update_result = await self.update_system()
                        if update_result["success"]:
                            print("System updated successfully")
                        else:
                            print(f"Update failed: {update_result['error']}")
                    else:
                        print("Auto-update is disabled")
                
        except Exception as e:
            print(f"Error in auto-update scheduler: {e}")
```

## 📊 Métricas de Éxito

### **🎯 Objetivos Técnicos**
- **Uptime**: > 99.5%
- **Tiempo de respuesta**: < 2s promedio
- **Disponibilidad**: 24/7
- **Recovery Time**: < 5 minutos
- **Backup frequency**: Diario

### **🎯 Objetivos de Funcionalidad**
- **Monitoreo**: Sistema operativo 24/7
- **Backup**: Automático y confiable
- **Actualizaciones**: Sin interrupciones
- **Alertas**: Respuesta rápida
- **Documentación**: Actualizada y completa

## ✅ Criterios de Éxito

### **📋 Checklist de Validación**
- [ ] **Sistema de monitoreo** operativo
- [ ] **Backup automático** funcionando
- [ ] **Actualizaciones** sin interrupciones
- [ ] **Alertas** configuradas y funcionando
- [ ] **Documentación** actualizada
- [ ] **Procedimientos** de emergencia
- [ ] **Equipo capacitado** en mantenimiento

---

**🎉 ¡Con esta fase tendrás un sistema robusto y mantenible a largo plazo!**

*Recuerda: El mantenimiento es clave para la longevidad y confiabilidad del sistema.* 🚀

