from __future__ import annotations

# Standard library imports
from collections import OrderedDict
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure os is properly imported and not overridden
if not hasattr(os, 'path'):
    import importlib
    os = importlib.reload(os)

# Numpy opcional
try:
    import numpy as np  # FAISS y SentenceTransformer se importan bajo demanda
except Exception:
    np = None

# Local imports
current_file = Path(__file__)
project_root = current_file.parent.parent.parent
sys.path.append(str(project_root))

try:
    from src.backend.utils.unified_logger import get_unified_logger
except ImportError:
    # Fallback if logger import fails
    def get_unified_logger(name):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)


try:
    from src.backend.utils.memory_limiter import get_memory_limiter
except ImportError:
    get_memory_limiter = None

try:
    from src.backend.utils.tracing import PerformanceTracer
except ImportError:
    # Fallback if tracing import fails
    class PerformanceTracer:
        def __init__(self, *args, **kwargs):
            pass

        def span(self, name, metadata=None):
            from contextlib import nullcontext

            return nullcontext()


logger = get_unified_logger("Knowledge")


class EmbeddingCache:
    """
    Cache LRU optimizado para embeddings con persistencia y compresión
    """

    def __init__(
        self,
        max_size: int = 1000,
        cache_file: Optional[str] = None,
        enable_compression: bool = True,
        auto_save_interval: int = 100,
    ):
        """
        Inicializa el cache de embeddings optimizado

        Args:
            max_size: Tamaño máximo del cache
            cache_file: Archivo opcional para persistir el cache
            enable_compression: Habilitar compresión de embeddings
            auto_save_interval: Intervalo para auto-guardado
        """
        self.max_size = max_size
        self.cache_file = cache_file
        self.enable_compression = enable_compression
        self.auto_save_interval = auto_save_interval

        # Cache principal optimizado
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._hit_count = 0
        self._miss_count = 0
        self._total_requests = 0
        self._operations_since_save = 0

        # Thread safety
        import threading

        self._lock = threading.RLock()

        # Métricas de rendimiento
        self._access_times = []
        self._compression_ratio = 0.0

        self._load_cache()

    def _get_text_hash(self, text: str) -> str:
        """
        Genera un hash único para el texto

        Args:
            text: Texto a hashear

        Returns:
            Hash MD5 del texto
        """
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[np.ndarray]:
        """
        Obtiene el embedding del cache con optimizaciones

        Args:
            text: Texto del cual obtener el embedding

        Returns:
            Embedding si existe en cache, None en caso contrario
        """
        import time

        start_time = time.time()

        text_hash = self._get_text_hash(text)

        with self._lock:
            self._total_requests += 1

            if text_hash in self.cache:
                # Obtener entrada del cache
                entry = self.cache.pop(text_hash)
                self.cache[text_hash] = entry  # Mover al final (LRU)

                # Actualizar estadísticas de acceso
                entry["access_count"] = entry.get("access_count", 0) + 1
                entry["last_access"] = time.time()

                self._hit_count += 1

                # Descomprimir si es necesario
                embedding = self._decompress_embedding(entry["data"])

                # Registrar tiempo de acceso
                access_time = time.time() - start_time
                self._access_times.append(access_time)
                if len(self._access_times) > 1000:  # Mantener solo últimos 1000
                    self._access_times = self._access_times[-1000:]

                return embedding.copy() if embedding is not None else None

            self._miss_count += 1
            return None

    def put(self, text: str, embedding: np.ndarray) -> None:
        """
        Almacena un embedding en el cache con optimizaciones

        Args:
            text: Texto asociado al embedding
            embedding: Embedding a almacenar
        """
        import time

        text_hash = self._get_text_hash(text)

        with self._lock:
            # Comprimir embedding si está habilitado
            compressed_data = self._compress_embedding(embedding)

            # Crear entrada optimizada
            entry = {
                "data": compressed_data,
                "original_size": embedding.nbytes,
                "compressed_size": (
                    len(compressed_data) if isinstance(compressed_data, bytes) else embedding.nbytes
                ),
                "timestamp": time.time(),
                "access_count": 0,
                "last_access": time.time(),
                "text_length": len(text),
            }

            # Si ya existe, remover la versión anterior
            if text_hash in self.cache:
                self.cache.pop(text_hash)

            # Agregar al final (más reciente)
            self.cache[text_hash] = entry

            # Mantener tamaño máximo con LRU
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)  # Remover el más antiguo

            # Auto-guardado periódico
            self._operations_since_save += 1
            if self._operations_since_save >= self.auto_save_interval:
                self._auto_save()
                self._operations_since_save = 0

    def clear(self) -> None:
        """
        Limpia el cache completamente
        """
        self.cache.clear()
        self._hit_count = 0
        self._miss_count = 0
        self._total_requests = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas avanzadas del cache

        Returns:
            Diccionario con estadísticas del cache
        """
        total_size = sum(embedding.nbytes for embedding in self.cache.values())
        hit_rate = (
            self._hit_count / max(self._total_requests, 1) if self._total_requests > 0 else 0.0
        )
        avg_access_time = sum(self._access_times) / max(len(self._access_times), 1)

        # Calcular estadísticas de compresión
        total_original = sum(entry.get("original_size", 0) for entry in self.cache.values())
        total_compressed = sum(entry.get("compressed_size", 0) for entry in self.cache.values())
        compression_ratio = (1 - total_compressed / max(total_original, 1)) * 100

        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "memory_usage_bytes": total_size,
            "memory_usage_mb": total_size / (1024 * 1024),
            "hit_rate": hit_rate,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "total_requests": self._total_requests,
            "avg_access_time_ms": avg_access_time * 1000,
            "compression_ratio_percent": compression_ratio,
            "operations_since_save": self._operations_since_save,
            "cache_efficiency": hit_rate * (1 + compression_ratio / 100),
        }

    def _load_cache(self) -> None:
        """
        Carga el cache desde archivo si existe
        """
        if not self.cache_file or not os.path.exists(self.cache_file):
            return

        try:
            with open(self.cache_file, "rb") as f:
                import pickle

                data = pickle.load(f)
                if isinstance(data, dict) and "cache" in data:
                    # Formato nuevo con estadísticas
                    self.cache = data.get("cache", OrderedDict())
                    self._hit_count = data.get("hit_count", 0)
                    self._miss_count = data.get("miss_count", 0)
                    self._total_requests = data.get("total_requests", 0)
                else:
                    # Formato antiguo, solo cache
                    self.cache = data if isinstance(data, OrderedDict) else OrderedDict()
            logger.info(f"📥 Cache de embeddings cargado: {len(self.cache)} entradas")
        except Exception as e:
            logger.warning(f"⚠️ Error cargando cache de embeddings: {e}")
            self.cache = OrderedDict()

    def save_cache(self) -> None:
        """
        Guarda el cache a archivo
        """
        if not self.cache_file:
            return

        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, "wb") as f:
                import pickle

                data = {
                    "cache": self.cache,
                    "hit_count": self._hit_count,
                    "miss_count": self._miss_count,
                    "total_requests": self._total_requests,
                }
                pickle.dump(data, f)
            logger.info(f"💾 Cache de embeddings guardado: {len(self.cache)} entradas")
        except Exception as e:
            logger.error(f"❌ Error guardando cache de embeddings: {e}")

    def _compress_embedding(self, embedding: np.ndarray) -> Any:
        """
        Comprime un embedding si está habilitado

        Args:
            embedding: Embedding a comprimir

        Returns:
            Embedding comprimido o original
        """
        if not self.enable_compression:
            return embedding

        try:
            import zlib

            # Si no hay numpy disponible, no comprimir para evitar errores
            if np is None:
                return embedding

            # Convertir a bytes y comprimir
            embedding_bytes = embedding.astype(np.float32).tobytes()
            compressed = zlib.compress(embedding_bytes, level=6)

            # Solo usar compresión si reduce significativamente el tamaño
            if len(compressed) < len(embedding_bytes) * 0.8:
                return compressed
            else:
                return embedding

        except Exception as e:
            logger.warning(f"⚠️ Error comprimiendo embedding: {e}")
            return embedding

    def _decompress_embedding(self, data: Any) -> Optional[np.ndarray]:
        """
        Descomprime un embedding si es necesario

        Args:
            data: Datos a descomprimir

        Returns:
            Embedding descomprimido o None si hay error
        """
        try:
            if isinstance(data, bytes):
                # Datos comprimidos
                import zlib

                decompressed_bytes = zlib.decompress(data)
                if np is None:
                    logger.warning("numpy no disponible; no puedo reconstruir embedding desde bytes")
                    return None
                return np.frombuffer(decompressed_bytes, dtype=np.float32)
            elif isinstance(data, np.ndarray):
                # Datos no comprimidos
                return data
            else:
                logger.error(f"❌ Tipo de datos no reconocido en cache: {type(data)}")
                return None

        except Exception as e:
            logger.error(f"❌ Error descomprimiendo embedding: {e}")
            return None

    def _auto_save(self) -> None:
        """
        Guarda automáticamente el cache si está configurado
        """
        try:
            self.save_cache()
        except Exception as e:
            logger.warning(f"⚠️ Error en auto-guardado: {e}")

    def estimate_memory_usage(self) -> int:
        """
        Estima el uso de memoria del cache

        Returns:
            Uso estimado en bytes
        """
        try:
            import sys

            total_size = sys.getsizeof(self.cache)

            for entry in self.cache.values():
                total_size += sys.getsizeof(entry)
                if np is not None and isinstance(entry.get("data"), np.ndarray):
                    total_size += entry["data"].nbytes
                elif isinstance(entry.get("data"), bytes):
                    total_size += len(entry["data"])

            return total_size

        except Exception:
            # Estimación aproximada
            return len(self.cache) * 384 * 4  # 384 dimensiones * 4 bytes por float


class KnowledgeBase:
    """
    Base de conocimiento vectorial usando FAISS y SentenceTransformers
    Permite búsqueda semántica en documentos locales
    """

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        index_path: Optional[str] = None,
        documents_path: Optional[str] = None,
        cache_size: int = 1000,
    ):
        """
        Inicializa la base de conocimiento

        Args:
            embedding_model: Modelo de embeddings a utilizar
            index_path: Ruta opcional para guardar/cargar el índice FAISS
            documents_path: Ruta opcional para guardar/cargar los documentos
            cache_size: Tamaño máximo del cache de embeddings
        """
        self.embedding_model_name = embedding_model
        self.embedding_model = None
        self.index = None
        self.documents: List[Dict[str, Any]] = []
        self.index_path = index_path
        self.documents_path = documents_path
        self.embedding_dim = 384  # Dimensión para all-MiniLM-L6-v2

        # Inicializar cache de embeddings
        cache_file = None
        if index_path:
            cache_dir = os.path.dirname(index_path)
            cache_file = os.path.join(cache_dir, "embeddings_cache.pkl")

        # Inicializar tracer para medición de rendimiento
        try:
            from src.backend.utils.unified_config import get_config

            config = get_config()
            self.tracer = PerformanceTracer(enabled=config.system.trace_enabled)
        except (ImportError, AttributeError):
            self.tracer = PerformanceTracer(enabled=False)

        self.embedding_cache = EmbeddingCache(max_size=cache_size, cache_file=cache_file)

        # Integrar con memory limiter si está disponible
        self._register_with_memory_limiter()

        logger.info(f"🧠 Inicializando KnowledgeBase con modelo {embedding_model}")

    def _get_embedding_with_cache(self, text: str) -> Optional[np.ndarray]:
        """
        Obtiene el embedding de un texto usando cache LRU

        Args:
            text: Texto para generar embedding

        Returns:
            Embedding del texto o None si hay error
        """
        # Intentar obtener del cache primero
        cached_embedding = self.embedding_cache.get(text)
        if cached_embedding is not None:
            return cached_embedding

        # Si no está en cache, generar nuevo embedding
        try:
            if self.embedding_model is None:
                if not self.load_embedding_model():
                    return None

            embedding = self.embedding_model.encode([text])[0]

            # Guardar en cache
            self.embedding_cache.put(text, embedding)

            return embedding

        except Exception as e:
            logger.error(f"❌ Error generando embedding: {e}")
            return None

    def load_embedding_model(self) -> bool:
        """
        Carga el modelo de embeddings

        Returns:
            True si se cargó correctamente, False en caso contrario
        """
        try:
            logger.info(f"📥 Cargando modelo de embeddings {self.embedding_model_name}...")
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info("✅ Modelo de embeddings cargado correctamente")
            return True
        except Exception as e:
            logger.error(f"❌ Error cargando modelo de embeddings: {e}")
            return False

    def initialize_index(self) -> bool:
        """
        Inicializa el índice FAISS

        Returns:
            True si se inicializó correctamente, False en caso contrario
        """
        try:
            # Cargar modelo de embeddings si no está cargado
            if self.embedding_model is None:
                if not self.load_embedding_model():
                    return False

            # Intentar cargar índice existente
            if self.index_path and os.path.exists(self.index_path):
                logger.info(f"📂 Cargando índice FAISS desde {self.index_path}")
                import faiss
                self.index = faiss.read_index(self.index_path)

                # Cargar documentos si existe el archivo
                if self.documents_path and os.path.exists(self.documents_path):
                    with open(self.documents_path, "r", encoding="utf-8") as f:
                        self.documents = json.load(f)
                    logger.info(f"📄 Cargados {len(self.documents)} documentos")
                else:
                    logger.warning("⚠️ Índice cargado pero no se encontraron documentos")
                    return False
            else:
                # Crear nuevo índice
                logger.info("🆕 Creando nuevo índice FAISS")
                import faiss
                self.index = faiss.IndexFlatL2(self.embedding_dim)

            logger.info("✅ Índice FAISS inicializado correctamente")
            return True

        except Exception as e:
            logger.error(f"❌ Error inicializando índice FAISS: {e}")
            return False

    def add_document(self, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Agrega un documento a la base de conocimiento

        Args:
            content: Contenido del documento
            metadata: Metadatos opcionales (título, fuente, etc.)

        Returns:
            True si se agregó correctamente, False en caso contrario
        """
        if metadata is None:
            metadata = {}

        try:
            # Inicializar índice si no existe
            if self.index is None:
                if not self.initialize_index():
                    return False

            # Generar embedding usando cache
            embedding = self._get_embedding_with_cache(content)
            if embedding is None:
                logger.error("❌ No se pudo generar embedding para el documento")
                return False

            # Crear documento
            doc_id = len(self.documents)
            document = {
                "id": doc_id,
                "content": content,
                "metadata": metadata,
                "timestamp": time.time(),
            }

            # Agregar a la lista de documentos
            self.documents.append(document)

            # Agregar al índice FAISS
            self.index.add(np.array([embedding], dtype=np.float32))

            logger.info(f"📄 Documento agregado con ID {doc_id}")

            # Guardar índice y documentos si hay rutas configuradas
            if self.index_path and self.documents_path:
                self._save_index_and_docs()

            return True

        except Exception as e:
            logger.error(f"❌ Error agregando documento: {e}")
            return False

    def index_documents(self, file_paths: List[str]) -> int:
        """
        Indexa múltiples documentos desde archivos

        Args:
            file_paths: Lista de rutas a archivos de texto

        Returns:
            Número de documentos indexados correctamente
        """
        indexed_count = 0

        for file_path in file_paths:
            try:
                # Verificar que el archivo existe
                if not os.path.exists(file_path):
                    logger.warning(f"⚠️ Archivo no encontrado: {file_path}")
                    continue

                # Leer contenido del archivo
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extraer metadatos básicos
                file_name = os.path.basename(file_path)
                file_ext = os.path.splitext(file_name)[1]

                metadata = {
                    "file_name": file_name,
                    "file_path": file_path,
                    "file_type": file_ext,
                    "indexed_at": time.time(),
                }

                # Agregar documento
                if self.add_document(content, metadata):
                    indexed_count += 1
                    logger.info(f"✅ Indexado: {file_name}")

            except Exception as e:
                logger.error(f"❌ Error indexando {file_path}: {e}")

        logger.info(f"📊 Indexados {indexed_count}/{len(file_paths)} documentos")
        return indexed_count

    def query(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Busca documentos relevantes para una consulta

        Args:
            query_text: Texto de la consulta
            top_k: Número máximo de resultados a devolver

        Returns:
            Lista de documentos relevantes con sus metadatos
        """
        with self.tracer.span("kb_query", {"query_length": len(query_text), "top_k": top_k}):
            try:
                # Verificar que el índice está inicializado
                if self.index is None or self.embedding_model is None:
                    logger.warning("⚠️ Índice o modelo no inicializados, intentando inicializar...")
                    if not self.initialize_index():
                        return []

                # Generar embedding de la consulta usando cache
                with self.tracer.span("embed", {"text_length": len(query_text)}):
                    query_embedding = self._get_embedding_with_cache(query_text)
                    if query_embedding is None:
                        logger.error("❌ No se pudo generar embedding para la consulta")
                        return []

                # Buscar documentos similares
                with self.tracer.span(
                    "faiss_search", {"index_size": len(self.documents), "k": top_k}
                ):
                    k = min(top_k, len(self.documents))  # No buscar más documentos de los que hay
                    if k == 0:
                        logger.warning("⚠️ No hay documentos en la base de conocimiento")
                        return []

                    distances, indices = self.index.search(
                        np.array([query_embedding], dtype=np.float32), k
                    )

                # Preparar resultados
                with self.tracer.span("context_assembly", {"found_docs": len(indices[0])}):
                    results = []
                    for i, doc_idx in enumerate(indices[0]):
                        if doc_idx < 0 or doc_idx >= len(self.documents):
                            continue  # Índice inválido

                        doc = self.documents[doc_idx]
                        results.append(
                            {
                                "content": doc["content"],
                                "metadata": doc["metadata"],
                                "score": float(
                                    1.0 / (1.0 + distances[0][i])
                                ),  # Convertir distancia a score
                            }
                        )

                logger.info(f"🔍 Consulta: '{query_text[:50]}...' - {len(results)} resultados")
                return results

            except Exception as e:
                logger.error(f"❌ Error en consulta: {e}")
                return []

    def _save_index_and_docs(self) -> bool:
        """
        Guarda el índice FAISS y los documentos

        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        try:
            # Crear directorios si no existen
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            os.makedirs(os.path.dirname(self.documents_path), exist_ok=True)

            # Guardar índice FAISS
            import faiss
            faiss.write_index(self.index, self.index_path)

            # Guardar documentos
            with open(self.documents_path, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=2)

            logger.info("💾 Índice y documentos guardados correctamente")
            return True

        except Exception as e:
            logger.error(f"❌ Error guardando índice y documentos: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Devuelve el estado de la base de conocimiento

        Returns:
            Diccionario con información de estado
        """
        return {
            "embedding_model": self.embedding_model_name,
            "documents_count": len(self.documents),
            "index_initialized": self.index is not None,
            "model_loaded": self.embedding_model is not None,
        }

    def _register_with_memory_limiter(self) -> None:
        """
        Registra la knowledge base con el memory limiter para gestión automática
        """
        if not get_memory_limiter:
            return

        try:
            limiter = get_memory_limiter()

            # Registrar cache del modelo de embeddings
            limiter.register_cache(
                "embedding_model",
                {
                    "size_func": self._get_embedding_model_size,
                    "clear_func": self._unload_embedding_model,
                    "description": "Sentence transformer embedding model",
                },
            )

            # Registrar cache del índice FAISS
            limiter.register_cache(
                "faiss_index",
                {
                    "size_func": self._get_index_size,
                    "clear_func": self._clear_index,
                    "description": "FAISS vector index",
                },
            )

            # Registrar cache de documentos
            limiter.register_cache(
                "documents",
                {
                    "size_func": self._get_documents_size,
                    "clear_func": self._clear_documents,
                    "description": "Knowledge base documents",
                },
            )

            # Registrar cache del embedding cache
            limiter.register_cache(
                "embedding_cache",
                {
                    "size_func": self._get_embedding_cache_size,
                    "clear_func": self._clear_embedding_cache,
                    "description": "Embedding cache for computed vectors",
                },
            )

            # Registrar callback para limpieza cuando sea necesario
            limiter.register_cleanup_callback("knowledge_base", self._cleanup_callback)

        except Exception as e:
            logger.warning(f"⚠️ Error registrando con memory limiter: {e}")

    def _get_embedding_model_size(self) -> int:
        try:
            if self.embedding_model is None:
                return 0
            # Estimación aproximada: tamaño del modelo en memoria
            return 200 * 1024 * 1024  # 200 MB aproximado para MiniLM
        except Exception:
            return 0

    def _get_index_size(self) -> int:
        try:
            if self.index is None:
                return 0
            # Estimación aproximada basada en número de documentos y dimensión del embedding
            return len(self.documents) * self.embedding_dim * 4  # float32 = 4 bytes
        except Exception:
            return 0

    def _get_documents_size(self) -> int:
        try:
            # Estimación aproximada del tamaño de documentos en memoria
            return sum(len(doc.get("content", "")) for doc in self.documents)
        except Exception:
            return 0

    def _unload_embedding_model(self) -> None:
        try:
            self.embedding_model = None
            logger.info("🧹 Modelo de embeddings descargado de memoria")
        except Exception as e:
            logger.warning(f"⚠️ Error descargando modelo de embeddings: {e}")

    def _clear_index(self) -> None:
        try:
            self.index = None
            logger.info("🧹 Índice FAISS limpiado de memoria")
        except Exception as e:
            logger.warning(f"⚠️ Error limpiando índice FAISS: {e}")

    def _clear_documents(self) -> None:
        try:
            self.documents = []
            logger.info("🧹 Documentos limpiados de memoria")
        except Exception as e:
            logger.warning(f"⚠️ Error limpiando documentos: {e}")

    def _rebuild_index(self) -> None:
        try:
            if self.documents and self.embedding_model is not None:
                import faiss
                self.index = faiss.IndexFlatL2(self.embedding_dim)
                embeddings = []
                for doc in self.documents:
                    embedding = self._get_embedding_with_cache(doc["content"])
                    if embedding is not None:
                        embeddings.append(embedding)
                if embeddings:
                    if np is None:
                        logger.warning("numpy no disponible; no puedo reconstruir índice FAISS")
                    else:
                        self.index.add(np.array(embeddings, dtype=np.float32))
            logger.info("🔧 Índice FAISS reconstruido")
        except Exception as e:
            logger.warning(f"⚠️ Error reconstruyendo índice FAISS: {e}")

    def _cleanup_callback(self) -> None:
        """
        Callback de limpieza para el memory limiter con optimizaciones
        """
        logger.info("🧹 Ejecutando limpieza de Knowledge Base")

        # Limpiar documentos si hay demasiados
        if len(self.documents) > 200:
            self._clear_documents()

        # Limpiar cache de embeddings si está muy lleno
        if len(self.embedding_cache.cache) > self.embedding_cache.max_size * 0.8:
            self._clear_embedding_cache()

        # Guardar cache de embeddings
        self.save_embedding_cache()

        # Forzar garbage collection
        import gc

        gc.collect()

        # Limpiar memoria GPU si está disponible
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except ImportError:
            pass

        logger.info("✅ Limpieza de Knowledge Base completada")

    def _get_embedding_cache_size(self) -> int:
        try:
            return self.embedding_cache.estimate_memory_usage()
        except Exception:
            return 0

    def _clear_embedding_cache(self) -> None:
        try:
            self.embedding_cache.clear()
            logger.info("🧹 Embedding cache limpiado")
        except Exception as e:
            logger.error(f"❌ Error limpiando embedding cache: {e}")

    def save_embedding_cache(self) -> None:
        try:
            self.embedding_cache.save_cache()
        except Exception as e:
            logger.error(f"❌ Error guardando embedding cache: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        try:
            return self.embedding_cache.get_stats()
        except Exception:
            return {
                "cache_size": 0,
                "hit_rate": 0.0,
                "memory_usage_bytes": 0,
                "compression_ratio_percent": 0.0,
            }

    def get_memory_stats(self) -> Dict[str, Any]:
        try:
            return {
                "embedding_model_size": self._get_embedding_model_size(),
                "index_size": self._get_index_size(),
                "documents_size": self._get_documents_size(),
                "embedding_cache_size": self._get_embedding_cache_size(),
            }
        except Exception:
            return {
                "embedding_model_size": 0,
                "index_size": 0,
                "documents_size": 0,
                "embedding_cache_size": 0,
            }


if __name__ == "__main__":
    print("🧪 Testing KnowledgeBase...")

    # Directorios de modelos y conocimiento
    models_dir = Path(__file__).parent.parent.parent / "models"
    kb_dir = models_dir / "knowledge"
    kb_dir.mkdir(exist_ok=True, parents=True)

    # Rutas de prueba
    index_path = str(kb_dir / "faiss_index.bin")
    docs_path = str(kb_dir / "documents.json")

    # Crear instancia
    kb = KnowledgeBase(
        embedding_model="all-MiniLM-L6-v2",
        index_path=index_path,
        documents_path=docs_path,
        cache_size=500,  # Cache más pequeño para testing
    )

    print(f"✅ KnowledgeBase creada: {kb}")
    print(f"📊 Estado inicial: {kb.get_status()}")

    # Inicializar e indexar un documento de ejemplo
    if kb.initialize_index():
        print("✅ Índice inicializado correctamente")

        test_doc = """Jetson Nano es una pequeña y potente computadora que permite ejecutar 
        múltiples redes neuronales en paralelo para aplicaciones como clasificación de imágenes, 
        detección de objetos, segmentación y procesamiento de voz."""

        if kb.add_document(test_doc, {"title": "Información Jetson Nano"}):
            print("✅ Documento agregado correctamente")

            results = kb.query("¿Qué es Jetson Nano?")
            print(f"🔍 Resultados de consulta: {len(results)}")
            if results:
                print(f"📄 Primer resultado: {results[0]['content'][:100]}...")
