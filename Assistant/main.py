#!/usr/bin/env python3
"""
🤖 Asistente Multimodal Offline - Fase 1
Implementación del motor LLM local con memoria y base de conocimiento
"""

# Standard library imports
import argparse
import json
import os
import sys
import time
from pathlib import Path

# Configure environment variables for Mac
os.environ['TMPDIR'] = '/tmp'
os.environ['TEMP'] = '/tmp'
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'  # For Mac M1/M2

# Add project paths
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Local imports
from backend.llm.model_manager import LLMManager
from backend.llm.memory_manager import MemoryManager
from backend.llm.knowledge_base import KnowledgeBase
from backend.utils.logger import get_logger, setup_logger
import config

# Configurar logger
setup_logger("Main")
logger = get_logger("Main")

logger.info("🔧 Configurando entorno...")
logger.info(f"📁 Directorio actual: {current_dir}")
logger.info(f"🗂️ TMPDIR: {os.environ.get('TMPDIR', 'No definido')}")
logger.info(f"🧠 Modelo configurado: {config.LLM_CONFIG['model_name']}")
logger.info(f"💻 Device: {config.LLM_CONFIG['device']}")

def test_imports():
    """Test de imports básicos"""
    logger.info("\n📦 Verificando imports...")
    
    try:
        import torch
        logger.info(f"✅ PyTorch {torch.__version__}")
        logger.info(f"   🔧 CUDA disponible: {torch.cuda.is_available()}")
        if hasattr(torch.backends, 'mps'):
            logger.info(f"   🍎 MPS disponible: {torch.backends.mps.is_available()}")
    except Exception as e:
        logger.error(f"❌ Error con PyTorch: {e}")
        return False
    
    try:
        import llama_cpp
        logger.info(f"✅ llama-cpp-python {llama_cpp.__version__}")
    except Exception as e:
        logger.error(f"❌ Error con llama-cpp-python: {e}")
        return False
    
    try:
        import sentence_transformers
        logger.info(f"✅ sentence-transformers {sentence_transformers.__version__}")
    except Exception as e:
        logger.error(f"❌ Error con sentence-transformers: {e}")
        return False
    
    try:
        import faiss
        logger.info(f"✅ FAISS disponible")
    except Exception as e:
        logger.error(f"❌ Error con FAISS: {e}")
        return False
    
    return True

def initialize_components():
    """Inicializa los componentes del sistema"""
    logger.info("\n🧩 Inicializando componentes...")
    
    components = {}
    
    # Inicializar LLM Manager
    try:
        # Configurar rutas para modelos
        models_dir = Path(config.MODELS_DIR)
        model_path = str(models_dir / config.LLM_CONFIG["model_name"])
        
        # Verificar si existe el modelo
        if not os.path.exists(model_path):
            logger.warning(f"⚠️ Modelo no encontrado en {model_path}")
            logger.warning("⚠️ Usando configuración de prueba")
            # Usar configuración de prueba si no existe el modelo
            components["llm"] = LLMManager()
        else:
            # Inicializar con el modelo configurado
            components["llm"] = LLMManager(
                model_path=model_path)
        
        logger.info("✅ LLM Manager inicializado")
    except Exception as e:
        logger.error(f"❌ Error inicializando LLM Manager: {e}")
        components["llm"] = None
    
    # Inicializar Memory Manager
    try:
        memory_dir = models_dir / "memory"
        memory_dir.mkdir(exist_ok=True, parents=True)
        
        components["memory"] = MemoryManager(
            memory_file=str(memory_dir / "conversation_history.json")
        )
        
        logger.info("✅ Memory Manager inicializado")
    except Exception as e:
        logger.error(f"❌ Error inicializando Memory Manager: {e}")
        components["memory"] = None
    
    # Inicializar Knowledge Base
    try:
        kb_dir = models_dir / "knowledge"
        kb_dir.mkdir(exist_ok=True, parents=True)
        
        components["kb"] = KnowledgeBase(
            embedding_model="all-MiniLM-L6-v2",
            index_path=str(kb_dir / "faiss_index.bin"),
            documents_path=str(kb_dir / "documents.json")
        )
        
        # Inicializar índice
        components["kb"].initialize_index()
        
        logger.info("✅ Knowledge Base inicializada")
    except Exception as e:
        logger.error(f"❌ Error inicializando Knowledge Base: {e}")
        components["kb"] = None
    
    return components

def interactive_mode(components):
    """Modo interactivo con LLM, memoria y base de conocimiento"""
    logger.info("\n💬 Modo Interactivo Avanzado")
    print("\n🤖 Asistente Personal Leonel - Modo Interactivo")
    print("═" * 50)
    print("📋 Comandos disponibles:")
    print("  /help        - Mostrar todos los comandos")
    print("  /salir       - Salir del programa")
    print("  /status      - Ver estado del sistema")
    print("  /clear       - Limpiar toda la memoria")
    print("  /memory      - Ver estado de la memoria")
    print("  /list_short  - Ver interacciones de memoria a corto plazo")
    print("  /list_long   - Ver interacciones de memoria a largo plazo")
    print("  /delete_short [índice] - Borrar interacción específica (corto plazo)")
    print("  /delete_long [índice]  - Borrar interacción específica (largo plazo)")
    print("  /rag on|off  - Activar/desactivar búsqueda RAG")
    print("  /add <texto> - Agregar texto a la base de conocimiento")
    print("═" * 50)
    print("💬 Escribe tu mensaje o usa un comando:")
    
    # Verificar componentes
    llm = components.get("llm")
    memory = components.get("memory")
    kb = components.get("kb")
    
    if not llm:
        logger.error("❌ LLM no inicializado, no se puede iniciar modo interactivo")
        return
    
    print("✅ ¡Listo para chatear!\n")
    
    # Configuración de la sesión
    use_rag = False
    
    while True:
        try:
            user_input = input("👤 Tú: ").strip()
            
            # Procesar comandos especiales
            if user_input.lower() in ["/salir", "/exit", "/quit"]:
                print("\n👋 ¡Hasta luego! Sesión terminada.")
                break
                
            elif user_input.lower() == "/help":
                print("\n📋 Comandos Disponibles")
                print("═" * 50)
                print("🔧 SISTEMA:")
                print("  /help        - Mostrar esta ayuda")
                print("  /salir       - Salir del programa")
                print("  /status      - Ver estado del sistema")
                print("\n💾 MEMORIA:")
                print("  /clear       - Limpiar toda la memoria")
                print("  /memory      - Ver estado de la memoria")
                print("  /list_short  - Ver interacciones de memoria a corto plazo")
                print("  /list_long   - Ver interacciones de memoria a largo plazo")
                print("  /delete_short [índice] - Borrar interacción específica (corto plazo)")
                print("  /delete_long [índice]  - Borrar interacción específica (largo plazo)")
                print("\n📚 CONOCIMIENTO:")
                print("  /rag on|off  - Activar/desactivar búsqueda RAG")
                print("  /add <texto> - Agregar texto a la base de conocimiento")
                print("═" * 50)
                continue
                
            elif user_input.lower() == "/status":
                print("\n📊 Estado del Sistema")
                print("─" * 30)
                
                # Mostrar estado del LLM con formato mejorado
                if llm:
                    try:
                        llm_status = llm.get_status()
                        print("🧠 LLM:")
                        print(f"  - Modelo: {os.path.basename(llm_status['model_path'])}")
                        print(f"  - Cargado: {'✅' if llm_status['is_loaded'] else '❌'}")
                        print(f"  - Optimizado: {'✅' if llm_status.get('optimized', False) else '❌'}")
                        print(f"  - Timeout: {llm_status.get('timeout', 30)}s")
                        print(f"  - Tokens máximos: {llm_status.get('max_tokens', 256)}")
                        print(f"  - Tamaño de contexto: {llm_status.get('context_size', 2048)}")
                        print(f"  - Temperatura: {llm_status['params'].get('temperature', 0.7)}")
                        print(f"  - Historial: {llm_status['conversation_length']} mensajes")
                    except Exception as e:
                        logger.error(f"Error obteniendo estado del LLM: {e}")
                        print("🧠 LLM: Error obteniendo estado")
                
                # Mostrar estado de la memoria
                if memory:
                    try:
                        memory_status = memory.get_status()
                        print("💾 Memoria:")
                        print(f"  - Interacciones: {memory_status.get('interactions', 0)}")
                        print(f"  - Memorias a largo plazo: {memory_status.get('long_term_count', 0)}")
                        print(f"  - Tamaño máximo (corto plazo): {memory_status.get('max_short_term', 20)}")
                        print(f"  - Archivo: {os.path.basename(memory_status.get('file', 'No disponible'))}")
                    except Exception as e:
                        logger.error(f"Error obteniendo estado de la memoria: {e}")
                        print("💾 Memoria: Error obteniendo estado")
                
                # Mostrar estado de la base de conocimiento
                if kb:
                    try:
                        kb_status = kb.get_status()
                        print("📚 Base de Conocimiento:")
                        print(f"  - Documentos: {kb_status.get('document_count', 0)}")
                        print(f"  - Modelo: {kb_status.get('embedding_model', 'No disponible')}")
                        print(f"  - Índice: {os.path.basename(kb_status.get('index_path', 'No disponible'))}")
                    except Exception as e:
                        logger.error(f"Error obteniendo estado de la KB: {e}")
                        print("📚 Base de Conocimiento: Error obteniendo estado")
                
                print(f"🔍 RAG activado: {'✅' if use_rag else '❌'}")
                print()
                continue
                
            elif user_input.lower() == "/clear":
                if memory:
                    memory.clear_memory()
                    print("\n🧹 Memoria limpiada completamente")
                    print("   ✅ Memoria a corto plazo: Limpiada")
                    print("   ✅ Memoria a largo plazo: Limpiada")
                else:
                    print("\n❌ Error: Memoria no disponible")
                continue
                
            elif user_input.lower() == "/memory":
                if memory:
                    short_count = len(memory.short_term_memory)
                    long_count = len(memory.long_term_memory)
                    print("\n💾 Estado de la Memoria")
                    print("─" * 35)
                    print(f"📝 Memoria a corto plazo:  {short_count} interacciones")
                    print(f"🗄️ Memoria a largo plazo:   {long_count} elementos")
                    print(f"🔄 Límite de transición:    {memory.auto_transition_threshold}")
                    
                    # Mostrar últimas interacciones si existen
                    if short_count > 0:
                        print("\n📋 Últimas 3 interacciones:")
                        recent = memory.short_term_memory[-3:]  # Últimas 3
                        for i, interaction in enumerate(recent, 1):
                            # Verificar que la interacción tenga la estructura correcta
                            if isinstance(interaction, dict) and 'user_message' in interaction:
                                user_preview = interaction['user_message'][:80] + "..." if len(interaction['user_message']) > 80 else interaction['user_message']
                                print(f"   {i}. {user_preview}")
                            else:
                                print(f"   {i}. [Interacción con formato incorrecto]")
                    print("─" * 35)
                else:
                    print("\n❌ Error: Memoria no disponible")
                continue
                
            # Comandos de memoria complejos eliminados para simplificar la interfaz
                
            elif user_input.lower().startswith("/rag"):
                parts = user_input.split()
                if len(parts) > 1:
                    if parts[1].lower() == "on":
                        use_rag = True
                        print("\n🔍 RAG (Búsqueda en Base de Conocimiento)")
                        print("   ✅ Estado: Activado")
                    elif parts[1].lower() == "off":
                        use_rag = False
                        print("\n🔍 RAG (Búsqueda en Base de Conocimiento)")
                        print("   ❌ Estado: Desactivado")
                    else:
                        print("\n❌ Error: Comando inválido")
                        print("   💡 Uso correcto: /rag on|off")
                else:
                    print(f"\n🔍 RAG (Búsqueda en Base de Conocimiento)")
                    print(f"   {'✅ Estado: Activado' if use_rag else '❌ Estado: Desactivado'}")
                continue
                
            elif user_input.lower().startswith("/add "):
                text_to_add = user_input[5:].strip()
                if text_to_add:
                    try:
                        from datetime import datetime
                        success_kb = False
                        success_memory = False
                        
                        # Agregar a la base de conocimiento si está disponible
                        if kb:
                            success_kb = kb.add_document(text_to_add, {"source": "user_input", "timestamp": str(datetime.now())})
                        
                        # Agregar a memoria a largo plazo si está disponible
                        if memory:
                            memory.add_to_long_term(
                                content=text_to_add,
                                metadata={
                                    "group": "user_added",
                                    "category": "important_info",
                                    "importance": "high",
                                    "source": "manual_add",
                                    "timestamp": str(datetime.now())
                                }
                            )
                            success_memory = True
                        
                        # Mostrar resultado
                        print("\n📝 Información Agregada")
                        print("─" * 30)
                        if success_kb:
                            print("   ✅ Base de Conocimiento: Agregado")
                        elif kb:
                            print("   ❌ Base de Conocimiento: Error")
                        else:
                            print("   ⚠️ Base de Conocimiento: No disponible")
                            
                        if success_memory:
                            print("   ✅ Memoria a Largo Plazo: Agregado")
                        elif memory:
                            print("   ❌ Memoria a Largo Plazo: Error")
                        else:
                            print("   ⚠️ Memoria a Largo Plazo: No disponible")
                            
                        print(f"   📝 Contenido: {text_to_add[:60]}{'...' if len(text_to_add) > 60 else ''}")
                        
                        if not success_kb and not success_memory:
                            print("   ⚠️ Advertencia: No se pudo guardar en ningún sistema")
                            
                    except Exception as e:
                        print("\n❌ Error al agregar información")
                        print(f"   🔍 Detalles: {e}")
                else:
                    print("\n❌ Error: Texto requerido")
                    print("   💡 Uso correcto: /add <texto>")
                continue
                
            elif user_input.lower() == "/list_short":
                if memory:
                    interactions = memory.short_term_memory
                    if interactions:
                        print("\n📝 Memoria a Corto Plazo")
                        print("─" * 40)
                        for i, interaction in enumerate(interactions, 1):
                            user_msg = interaction.get('user_message', 'N/A')[:60]
                            assistant_msg = interaction.get('assistant_response', 'N/A')[:60]
                            print(f"  {i}. Usuario: {user_msg}{'...' if len(interaction.get('user_message', '')) > 60 else ''}")
                            print(f"     Asistente: {assistant_msg}{'...' if len(interaction.get('assistant_response', '')) > 60 else ''}")
                            print()
                    else:
                        print("\n📝 Memoria a Corto Plazo: Vacía")
                else:
                    print("\n❌ Error: Memoria no disponible")
                continue
                
            elif user_input.lower() == "/list_long":
                if memory:
                    long_memories = memory.long_term_memory
                    if long_memories:
                        print("\n🧠 Memoria a Largo Plazo")
                        print("─" * 40)
                        for i, mem in enumerate(long_memories, 1):
                            content = mem.get('content', 'N/A')[:80]
                            category = mem.get('metadata', {}).get('category', 'general')
                            importance = mem.get('metadata', {}).get('importance', 'normal')
                            print(f"  {i}. [{category}] [{importance}] {content}{'...' if len(mem.get('content', '')) > 80 else ''}")
                    else:
                        print("\n🧠 Memoria a Largo Plazo: Vacía")
                else:
                    print("\n❌ Error: Memoria no disponible")
                continue
                
            elif user_input.lower().startswith("/delete_short "):
                if memory:
                    try:
                        parts = user_input.split()
                        if len(parts) < 2:
                            print("\n❌ Error: Índice requerido")
                            print("   💡 Uso correcto: /delete_short [número]")
                            continue
                        index = int(parts[1]) - 1
                        if 0 <= index < len(memory.short_term_memory):
                            deleted = memory.short_term_memory.pop(index)
                            memory._save_memory()
                            print(f"\n✅ Interacción {index + 1} eliminada de memoria a corto plazo")
                            user_preview = deleted.get('user_message', '')[:50]
                            print(f"   📝 Contenido: {user_preview}{'...' if len(deleted.get('user_message', '')) > 50 else ''}")
                        else:
                            print(f"\n❌ Error: Índice {index + 1} fuera de rango (1-{len(memory.short_term_memory)})")
                    except (ValueError, IndexError):
                        print("\n❌ Error: Índice inválido")
                        print("   💡 Uso correcto: /delete_short [número]")
                else:
                    print("\n❌ Error: Memoria no disponible")
                continue
                
            elif user_input.lower().startswith("/delete_long "):
                if memory:
                    try:
                        parts = user_input.split()
                        if len(parts) < 2:
                            print("\n❌ Error: Índice requerido")
                            print("   💡 Uso correcto: /delete_long [número]")
                            continue
                        index = int(parts[1]) - 1
                        if 0 <= index < len(memory.long_term_memory):
                            deleted = memory.long_term_memory.pop(index)
                            memory._save_memory()
                            print(f"\n✅ Memoria {index + 1} eliminada de memoria a largo plazo")
                            content_preview = deleted.get('content', '')[:50]
                            print(f"   📝 Contenido: {content_preview}{'...' if len(deleted.get('content', '')) > 50 else ''}")
                        else:
                            print(f"\n❌ Error: Índice {index + 1} fuera de rango (1-{len(memory.long_term_memory)})")
                    except (ValueError, IndexError):
                        print("\n❌ Error: Índice inválido")
                        print("   💡 Uso correcto: /delete_long [número]")
                else:
                    print("\n❌ Error: Memoria no disponible")
                continue
            
            # Ignorar entradas vacías
            if not user_input:
                continue
            
            # Procesar consulta normal
            start_time = time.time()
            
            # Obtener contexto de la base de conocimiento si RAG está activado
            context = ""
            
            # Obtener contexto de memoria si hay gestor de memoria
            memory_context = ""
            if memory and user_input:
                try:
                    # Obtener memoria a corto plazo (conversación reciente)
                    recent_context = memory.get_recent_context(max_items=3)
                    
                    # Obtener memoria a largo plazo relevante
                    relevant_memories = memory.get_relevant_memory_contents(user_input, max_items=2)
                    
                    # Combinar ambos tipos de memoria
                    all_memory = []
                    if recent_context:
                        all_memory.extend([f"Conversación reciente:\n{ctx}" for ctx in recent_context])
                    if relevant_memories:
                        all_memory.extend([f"Memoria relevante:\n{mem}" for mem in relevant_memories])
                    
                    if all_memory:
                        memory_context = "\n\n" + "\n---\n".join(all_memory)
                        logger.info(f"🧠 Contexto de memoria recuperado: {len(memory_context)} caracteres (reciente: {len(recent_context)}, relevante: {len(relevant_memories)})")
                except Exception as e:
                    logger.error(f"❌ Error al recuperar memoria: {e}")
            
            # Obtener contexto de la base de conocimiento si RAG está activado
            kb_context = ""
            if use_rag and kb and user_input:
                try:
                    kb_results = kb.query(user_input, top_k=2)
                    if kb_results:
                        kb_context = "\n\nInformación de la base de conocimiento:\n" + "\n---\n".join([r["content"] for r in kb_results])
                        logger.info(f"📚 Contexto de KB recuperado: {len(kb_context)} caracteres")
                except Exception as e:
                    logger.error(f"❌ Error al recuperar contexto de KB: {e}")
                    print("⚠️ No se pudo recuperar contexto de la base de conocimiento. RAG desactivado para esta consulta.")
                    use_rag = False
            
            # Combinar todos los contextos
            context = ""
            if memory_context:
                context += memory_context
            if kb_context:
                context += kb_context
                
            if context:
                logger.info(f"📚 Contexto total recuperado: {len(context)} caracteres")
            
            # Obtener timeout de la configuración de forma segura
            timeout = 30  # Valor por defecto
            try:
                timeout = config.LLM_CONFIG.get("response_timeout", 30)
            except (AttributeError, KeyError):
                logger.warning("No se pudo obtener timeout de configuración, usando valor por defecto")
            
            # Generar respuesta con timeout
            if context:
                # Limitar el tamaño del contexto para evitar tokens excesivos
                max_context_length = 2000
                if len(context) > max_context_length:
                    logger.warning(f"⚠️ Contexto truncado de {len(context)} a {max_context_length} caracteres")
                    context = context[:max_context_length] + "...\n(contexto truncado)"
                
                response = llm.query_with_context(user_input, context, timeout=timeout)
            else:
                response = llm.query(user_input, timeout=timeout)
            
            # Guardar en memoria
            if memory:
                memory.add_interaction(user_input, response)
            
            # Mostrar respuesta y tiempo
            processing_time = time.time() - start_time
            print(f"🤖 Asistente: {response}")
            print(f"⏱️  Tiempo: {processing_time:.2f}s (límite: {timeout}s)\n")
            
            # Advertencia si el tiempo fue cercano al límite
            if processing_time > (timeout * 0.8) and processing_time < timeout:
                print(f"⚠️  Advertencia: La respuesta tardó más del 80% del tiempo límite.")
                print(f"   Considera usar consultas más cortas o ajustar el timeout en config.py\n")
            
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            logger.error(f"❌ Error en conversación: {e}")
            print(f"❌ Error: {e}")

def start_api_server(components):
    """Inicia el servidor API"""
    try:
        from backend.api import start_api
        
        logger.info("🚀 Iniciando servidor API...")
        start_api(host=config.API_HOST, port=config.API_PORT)
        
    except Exception as e:
        logger.error(f"❌ Error iniciando servidor API: {e}")
        print(f"❌ No se pudo iniciar el servidor API: {e}")

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Asistente Multimodal Offline - Fase 1")
    parser.add_argument("--api", action="store_true", help="Iniciar servidor API")
    parser.add_argument("--interactive", action="store_true", help="Iniciar modo interactivo")
    parser.add_argument("--test", action="store_true", help="Ejecutar tests básicos")
    args = parser.parse_args()
    
    print("🤖 ASISTENTE MULTIMODAL OFFLINE - FASE 1")
    print("="*50)
    
    # Si no se especifica ningún modo, usar interactivo por defecto
    if not (args.api or args.interactive or args.test):
        args.interactive = True
    
    # Test de imports
    if args.test or args.interactive:
        if not test_imports():
            logger.error("❌ Error en imports básicos")
            print("\n🔧 Posibles soluciones:")
            print("1. Reinstalar dependencias: pip install -r requirements.txt")
            print("2. Verificar que los modelos están descargados")
            return
    
    # Inicializar componentes
    components = initialize_components()
    
    # Iniciar modo según argumentos
    if args.api:
        start_api_server(components)
    elif args.interactive:
        interactive_mode(components)
    elif args.test:
        logger.info("✅ Tests básicos completados correctamente")
        print("✅ Tests básicos completados correctamente")

if __name__ == "__main__":
    main()