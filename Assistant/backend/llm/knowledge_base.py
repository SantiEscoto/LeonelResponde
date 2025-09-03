# Standard library imports
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Third-party imports
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from backend.utils.logger import get_logger
except ImportError:
    # Fallback if logger import fails
    def get_logger(name):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)

logger = get_logger("Knowledge")

class KnowledgeBase:
    """
    Base de conocimiento vectorial usando FAISS y SentenceTransformers
    Permite búsqueda semántica en documentos locales
    """
    
    def __init__(self, 
                 embedding_model: str = "all-MiniLM-L6-v2",
                 index_path: Optional[str] = None,
                 documents_path: Optional[str] = None):
        """
        Inicializa la base de conocimiento
        
        Args:
            embedding_model: Modelo de embeddings a utilizar
            index_path: Ruta opcional para guardar/cargar el índice FAISS
            documents_path: Ruta opcional para guardar/cargar los documentos
        """
        self.embedding_model_name = embedding_model
        self.embedding_model = None
        self.index = None
        self.documents: List[Dict[str, Any]] = []
        self.index_path = index_path
        self.documents_path = documents_path
        self.embedding_dim = 384  # Dimensión para all-MiniLM-L6-v2
        
        logger.info(f"🧠 Inicializando KnowledgeBase con modelo {embedding_model}")
    
    def load_embedding_model(self) -> bool:
        """
        Carga el modelo de embeddings
        
        Returns:
            True si se cargó correctamente, False en caso contrario
        """
        try:
            logger.info(f"📥 Cargando modelo de embeddings {self.embedding_model_name}...")
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
                self.index = faiss.read_index(self.index_path)
                
                # Cargar documentos si existe el archivo
                if self.documents_path and os.path.exists(self.documents_path):
                    with open(self.documents_path, 'r', encoding='utf-8') as f:
                        self.documents = json.load(f)
                    logger.info(f"📄 Cargados {len(self.documents)} documentos")
                else:
                    logger.warning("⚠️ Índice cargado pero no se encontraron documentos")
                    return False
            else:
                # Crear nuevo índice
                logger.info("🆕 Creando nuevo índice FAISS")
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
            
            # Generar embedding
            embedding = self.embedding_model.encode([content])[0]
            
            # Crear documento
            doc_id = len(self.documents)
            document = {
                "id": doc_id,
                "content": content,
                "metadata": metadata,
                "timestamp": time.time()
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
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extraer metadatos básicos
                file_name = os.path.basename(file_path)
                file_ext = os.path.splitext(file_name)[1]
                
                metadata = {
                    "file_name": file_name,
                    "file_path": file_path,
                    "file_type": file_ext,
                    "indexed_at": time.time()
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
        try:
            # Verificar que el índice está inicializado
            if self.index is None or self.embedding_model is None:
                logger.warning("⚠️ Índice o modelo no inicializados, intentando inicializar...")
                if not self.initialize_index():
                    return []
            
            # Generar embedding de la consulta
            query_embedding = self.embedding_model.encode([query_text])[0]
            
            # Buscar documentos similares
            k = min(top_k, len(self.documents))  # No buscar más documentos de los que hay
            if k == 0:
                logger.warning("⚠️ No hay documentos en la base de conocimiento")
                return []
            
            distances, indices = self.index.search(np.array([query_embedding], dtype=np.float32), k)
            
            # Preparar resultados
            results = []
            for i, doc_idx in enumerate(indices[0]):
                if doc_idx < 0 or doc_idx >= len(self.documents):
                    continue  # Índice inválido
                
                doc = self.documents[doc_idx]
                results.append({
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "score": float(1.0 / (1.0 + distances[0][i]))  # Convertir distancia a score
                })
            
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
            faiss.write_index(self.index, self.index_path)
            
            # Guardar documentos
            with open(self.documents_path, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Índice y documentos guardados correctamente")
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
            "model_loaded": self.embedding_model is not None
        }

# Test de importación
if __name__ == "__main__":
    print("🧪 Testing KnowledgeBase...")
    
    # Crear directorio para modelos si no existe
    models_dir = Path(__file__).parent.parent.parent / "models"
    kb_dir = models_dir / "knowledge"
    kb_dir.mkdir(exist_ok=True, parents=True)
    
    # Rutas para índice y documentos
    index_path = str(kb_dir / "faiss_index.bin")
    docs_path = str(kb_dir / "documents.json")
    
    kb = KnowledgeBase(
        embedding_model="all-MiniLM-L6-v2",
        index_path=index_path,
        documents_path=docs_path
    )
    
    print(f"✅ KnowledgeBase creada: {kb}")
    print(f"📊 Estado inicial: {kb.get_status()}")
    
    # Test básico
    if kb.initialize_index():
        print("✅ Índice inicializado correctamente")
        
        # Agregar documento de prueba
        test_doc = """Jetson Nano es una pequeña y potente computadora que permite ejecutar 
        múltiples redes neuronales en paralelo para aplicaciones como clasificación de imágenes, 
        detección de objetos, segmentación y procesamiento de voz."""
        
        if kb.add_document(test_doc, {"title": "Información Jetson Nano"}):
            print("✅ Documento agregado correctamente")
            
            # Probar consulta
            results = kb.query("¿Qué es Jetson Nano?")
            print(f"🔍 Resultados de consulta: {len(results)}")
            if results:
                print(f"📄 Primer resultado: {results[0]['content'][:100]}...")