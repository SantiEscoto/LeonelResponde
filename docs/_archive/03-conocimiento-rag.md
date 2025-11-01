# 📚 Fase 3: Base de Conocimiento RAG
## Estado Actual
- No iniciado: RAG pendiente de implementación.
- Prerrequisitos listos: LLM local operativo con `LLMManager` (Mistral GGUF), sistema de voz TTS/STT funcionando vía WS.
- Plan: embeddings con `sentence-transformers`, base vectorial FAISS y pipeline de indexación; integración con LLM para respuestas contextualizadas.
- Docker preparado, pero sin Docker instalado en host; se continuará en `.venv` hasta nuevo aviso.

## 🎯 Objetivos de esta Fase

- **Implementar sistema RAG** completo y optimizado
- **Base de conocimiento** estructurada y eficiente
- **Búsqueda semántica** avanzada con embeddings
- **Integración con LLM** para respuestas contextualizadas
- **Testing y validación** del sistema RAG

## ⏱️ Tiempo Estimado

**1 semana** (5 días de trabajo)

## 📋 Checklist de Tareas

### **Día 1: Configuración RAG**
- [ ] Configurar embeddings con Sentence Transformers
- [ ] Implementar base de datos vectorial FAISS
- [ ] Sistema de procesamiento de documentos
- [ ] Pipeline de indexación vectorial

### **Día 2: Base de Conocimiento**
- [ ] Procesar documentos de conocimiento
- [ ] Crear chunks optimizados
- [ ] Metadatos estructurados
- [ ] Sistema de actualización incremental

### **Día 3: Búsqueda Semántica**
- [ ] Implementar búsqueda por similitud
- [ ] Sistema de ranking de relevancia
- [ ] Filtros por metadatos
- [ ] Optimización de consultas

### **Día 4: Integración con LLM**
- [ ] Contexto relevante para respuestas
- [ ] Sistema de citas y fuentes
- [ ] Validación de calidad
- [ ] Testing de integración

### **Día 5: Optimización y Testing**
- [ ] Optimizar rendimiento
- [ ] Testing completo del sistema
- [ ] Documentación de la API
- [ ] Preparación para siguiente fase

## 🔧 Herramientas Necesarias

### **RAG Core**
- **Sentence Transformers**: Embeddings
- **FAISS**: Base de datos vectorial
- **LangChain**: Framework RAG
- **ChromaDB**: Alternativa ligera

### **Procesamiento de Documentos**
- **PyPDF2**: PDFs
- **python-docx**: Word
- **BeautifulSoup**: HTML
- **markdown**: Markdown

### **Optimización**
- **numpy**: Cálculos numéricos
- **scikit-learn**: ML utilities
- **tqdm**: Progress bars
- **pandas**: Manipulación de datos

## 🏗️ Arquitectura del Sistema RAG

### **📐 Componentes Principales**

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG SYSTEM                              │
├─────────────────────────────────────────────────────────────┤
│  Sentence Transformers + FAISS + LangChain                │
│  • Embeddings de alta calidad                             │
│  • Búsqueda semántica eficiente                           │
│  • Base de conocimiento estructurada                      │
│  • Integración con LLM contextualizada                    │
└─────────────────────────────────────────────────────────────┘
                                ↕️
┌─────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE BASE                          │
├─────────────────────────────────────────────────────────────┤
│  Documentos + Chunks + Metadatos + Vectores               │
│  • Procesamiento automático de documentos                 │
│  • Chunks optimizados para contexto                       │
│  • Metadatos estructurados                               │
│  • Indexación vectorial eficiente                         │
└─────────────────────────────────────────────────────────────┘
```

### **🔄 Flujo RAG**

```
Query → Embeddings → FAISS Search → Relevant Chunks → LLM → Contextualized Response
```

## 🚀 Implementación

### **1. Dependencias RAG**

```python
# requirements-rag.txt
# RAG Core
sentence-transformers==2.2.2
faiss-cpu==1.7.4
langchain==0.0.350
chromadb==0.4.15

# Document Processing
PyPDF2==3.0.1
python-docx==0.8.11
beautifulsoup4==4.12.2
markdown==3.5.1

# Optimization
numpy==1.24.3
scikit-learn==1.3.0
pandas==2.0.3
tqdm==4.65.0

# Utilities
python-magic==0.4.27
python-magic-bin==0.4.14
```

### **2. Sistema de Embeddings**

```python
# backend/app/ai/knowledge/embeddings.py
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any
import torch

class EmbeddingService:
    """Servicio de embeddings para RAG"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """Codificar textos a embeddings"""
        embeddings = self.model.encode(
            texts,
            convert_to_tensor=True,
            show_progress_bar=True
        )
        return embeddings.cpu().numpy()
    
    def encode_query(self, query: str) -> np.ndarray:
        """Codificar consulta para búsqueda"""
        embedding = self.model.encode(
            query,
            convert_to_tensor=True
        )
        return embedding.cpu().numpy()
    
    def get_similarity(self, query_embedding: np.ndarray, doc_embeddings: np.ndarray) -> np.ndarray:
        """Calcular similitud entre consulta y documentos"""
        # Normalizar embeddings
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        doc_norms = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
        
        # Calcular similitud coseno
        similarities = np.dot(doc_norms, query_norm)
        return similarities
```

### **3. Base de Datos Vectorial FAISS**

```python
# backend/app/ai/knowledge/vector_db.py
import faiss
import numpy as np
import pickle
from typing import List, Dict, Any, Tuple
import os

class FAISSVectorDB:
    """Base de datos vectorial con FAISS"""
    
    def __init__(self, dimension: int = 384, index_path: str = "vector_index"):
        self.dimension = dimension
        self.index_path = index_path
        self.index = None
        self.metadata = []
        self.documents = []
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Cargar índice existente o crear uno nuevo"""
        index_file = f"{self.index_path}.faiss"
        metadata_file = f"{self.index_path}.pkl"
        
        if os.path.exists(index_file) and os.path.exists(metadata_file):
            # Cargar índice existente
            self.index = faiss.read_index(index_file)
            with open(metadata_file, 'rb') as f:
                data = pickle.load(f)
                self.metadata = data['metadata']
                self.documents = data['documents']
        else:
            # Crear nuevo índice
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner Product para similitud coseno
            self.metadata = []
            self.documents = []
    
    def add_documents(self, documents: List[str], embeddings: np.ndarray, metadata: List[Dict]):
        """Agregar documentos al índice"""
        # Normalizar embeddings para similitud coseno
        embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        # Agregar al índice
        self.index.add(embeddings_norm.astype('float32'))
        
        # Guardar metadatos
        self.documents.extend(documents)
        self.metadata.extend(metadata)
        
        # Guardar índice
        self._save_index()
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> Tuple[List[str], List[Dict], List[float]]:
        """Buscar documentos similares"""
        # Normalizar consulta
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        query_norm = query_norm.astype('float32').reshape(1, -1)
        
        # Buscar en índice
        scores, indices = self.index.search(query_norm, k)
        
        # Obtener documentos y metadatos
        results_docs = [self.documents[i] for i in indices[0]]
        results_metadata = [self.metadata[i] for i in indices[0]]
        results_scores = scores[0].tolist()
        
        return results_docs, results_metadata, results_scores
    
    def _save_index(self):
        """Guardar índice y metadatos"""
        index_file = f"{self.index_path}.faiss"
        metadata_file = f"{self.index_path}.pkl"
        
        # Guardar índice FAISS
        faiss.write_index(self.index, index_file)
        
        # Guardar metadatos
        with open(metadata_file, 'wb') as f:
            pickle.dump({
                'metadata': self.metadata,
                'documents': self.documents
            }, f)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del índice"""
        return {
            "total_documents": len(self.documents),
            "dimension": self.dimension,
            "index_type": "FAISS IndexFlatIP",
            "memory_usage": self.index.ntotal * self.dimension * 4  # bytes
        }
```

### **4. Procesador de Documentos**

```python
# backend/app/ai/knowledge/document_processor.py
import os
import PyPDF2
from docx import Document
from bs4 import BeautifulSoup
import markdown
from typing import List, Dict, Any
import re

class DocumentProcessor:
    """Procesador de documentos para RAG"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_document(self, file_path: str) -> List[Dict[str, Any]]:
        """Procesar documento y extraer chunks"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return self._process_pdf(file_path)
        elif file_extension == '.docx':
            return self._process_docx(file_path)
        elif file_extension == '.html':
            return self._process_html(file_path)
        elif file_extension == '.md':
            return self._process_markdown(file_path)
        elif file_extension == '.txt':
            return self._process_txt(file_path)
        else:
            raise ValueError(f"Formato de archivo no soportado: {file_extension}")
    
    def _process_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Procesar archivo PDF"""
        chunks = []
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text.strip():
                    page_chunks = self._create_chunks(text, {
                        'source': file_path,
                        'page': page_num + 1,
                        'type': 'pdf'
                    })
                    chunks.extend(page_chunks)
        
        return chunks
    
    def _process_docx(self, file_path: str) -> List[Dict[str, Any]]:
        """Procesar archivo DOCX"""
        chunks = []
        
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        
        if text.strip():
            chunks = self._create_chunks(text, {
                'source': file_path,
                'type': 'docx'
            })
        
        return chunks
    
    def _process_html(self, file_path: str) -> List[Dict[str, Any]]:
        """Procesar archivo HTML"""
        chunks = []
        
        with open(file_path, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file.read(), 'html.parser')
            text = soup.get_text()
            
            if text.strip():
                chunks = self._create_chunks(text, {
                    'source': file_path,
                    'type': 'html'
                })
        
        return chunks
    
    def _process_markdown(self, file_path: str) -> List[Dict[str, Any]]:
        """Procesar archivo Markdown"""
        chunks = []
        
        with open(file_path, 'r', encoding='utf-8') as file:
            md_content = file.read()
            html = markdown.markdown(md_content)
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text()
            
            if text.strip():
                chunks = self._create_chunks(text, {
                    'source': file_path,
                    'type': 'markdown'
                })
        
        return chunks
    
    def _process_txt(self, file_path: str) -> List[Dict[str, Any]]:
        """Procesar archivo de texto"""
        chunks = []
        
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
            
            if text.strip():
                chunks = self._create_chunks(text, {
                    'source': file_path,
                    'type': 'txt'
                })
        
        return chunks
    
    def _create_chunks(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Crear chunks del texto"""
        chunks = []
        
        # Limpiar texto
        text = self._clean_text(text)
        
        # Dividir en chunks
        words = text.split()
        current_chunk = []
        current_size = 0
        
        for word in words:
            if current_size + len(word) + 1 > self.chunk_size and current_chunk:
                # Crear chunk
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'metadata': metadata.copy(),
                    'chunk_id': len(chunks)
                })
                
                # Iniciar nuevo chunk con overlap
                overlap_words = current_chunk[-self.chunk_overlap:] if self.chunk_overlap > 0 else []
                current_chunk = overlap_words + [word]
                current_size = len(" ".join(current_chunk))
            else:
                current_chunk.append(word)
                current_size += len(word) + 1
        
        # Agregar último chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'metadata': metadata.copy(),
                'chunk_id': len(chunks)
            })
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Limpiar texto"""
        # Remover caracteres especiales
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        text = text.strip()
        
        return text
```

### **5. Servicio RAG Completo**

```python
# backend/app/ai/knowledge/rag_service.py
from typing import List, Dict, Any, Tuple
import os
from .embeddings import EmbeddingService
from .vector_db import FAISSVectorDB
from .document_processor import DocumentProcessor

class RAGService:
    """Servicio RAG completo"""
    
    def __init__(self, knowledge_base_path: str = "knowledge/"):
        self.knowledge_base_path = knowledge_base_path
        self.embedding_service = EmbeddingService()
        self.vector_db = FAISSVectorDB(
            dimension=self.embedding_service.embedding_dim
        )
        self.document_processor = DocumentProcessor()
        self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        """Inicializar base de conocimiento"""
        if not os.path.exists(self.knowledge_base_path):
            os.makedirs(self.knowledge_base_path)
        
        # Procesar documentos existentes
        self._process_existing_documents()
    
    def _process_existing_documents(self):
        """Procesar documentos existentes en la base de conocimiento"""
        for root, dirs, files in os.walk(self.knowledge_base_path):
            for file in files:
                if file.endswith(('.pdf', '.docx', '.html', '.md', '.txt')):
                    file_path = os.path.join(root, file)
                    try:
                        chunks = self.document_processor.process_document(file_path)
                        self._add_chunks_to_index(chunks)
                    except Exception as e:
                        print(f"Error procesando {file_path}: {e}")
    
    def _add_chunks_to_index(self, chunks: List[Dict[str, Any]]):
        """Agregar chunks al índice vectorial"""
        if not chunks:
            return
        
        # Extraer textos y metadatos
        texts = [chunk['text'] for chunk in chunks]
        metadata = [chunk['metadata'] for chunk in chunks]
        
        # Generar embeddings
        embeddings = self.embedding_service.encode_texts(texts)
        
        # Agregar al índice
        self.vector_db.add_documents(texts, embeddings, metadata)
    
    def add_document(self, file_path: str) -> bool:
        """Agregar nuevo documento a la base de conocimiento"""
        try:
            chunks = self.document_processor.process_document(file_path)
            self._add_chunks_to_index(chunks)
            return True
        except Exception as e:
            print(f"Error agregando documento {file_path}: {e}")
            return False
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Buscar documentos relevantes"""
        # Generar embedding de la consulta
        query_embedding = self.embedding_service.encode_query(query)
        
        # Buscar en base de datos vectorial
        documents, metadata, scores = self.vector_db.search(query_embedding, k)
        
        # Formatear resultados
        results = []
        for doc, meta, score in zip(documents, metadata, scores):
            results.append({
                'text': doc,
                'metadata': meta,
                'score': float(score),
                'relevance': self._calculate_relevance(score)
            })
        
        return results
    
    def _calculate_relevance(self, score: float) -> str:
        """Calcular nivel de relevancia"""
        if score >= 0.8:
            return "Muy relevante"
        elif score >= 0.6:
            return "Relevante"
        elif score >= 0.4:
            return "Moderadamente relevante"
        else:
            return "Poco relevante"
    
    def get_context_for_llm(self, query: str, max_chunks: int = 3) -> str:
        """Obtener contexto para LLM"""
        results = self.search(query, k=max_chunks)
        
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"Fuente {i} ({result['relevance']}):")
            context_parts.append(result['text'])
            context_parts.append(f"Metadatos: {result['metadata']}")
            context_parts.append("---")
        
        return "\n".join(context_parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de la base de conocimiento"""
        return {
            "total_documents": self.vector_db.get_stats()["total_documents"],
            "embedding_dimension": self.embedding_service.embedding_dim,
            "model_name": self.embedding_service.model_name,
            "chunk_size": self.document_processor.chunk_size,
            "chunk_overlap": self.document_processor.chunk_overlap
        }
```

### **6. API REST para RAG**

```python
# backend/app/api/rag.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from ..ai.knowledge.rag_service import RAGService

router = APIRouter(prefix="/api/rag", tags=["rag"])

class SearchRequest(BaseModel):
    query: str
    k: int = 5

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_results: int
    query: str

class AddDocumentRequest(BaseModel):
    file_path: str

class AddDocumentResponse(BaseModel):
    success: bool
    message: str
    chunks_added: int

# Instancia del servicio RAG
rag_service = RAGService()

@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """Buscar documentos en la base de conocimiento"""
    try:
        results = rag_service.search(request.query, request.k)
        
        return SearchResponse(
            results=results,
            total_results=len(results),
            query=request.query
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add-document", response_model=AddDocumentResponse)
async def add_document(request: AddDocumentRequest):
    """Agregar documento a la base de conocimiento"""
    try:
        success = rag_service.add_document(request.file_path)
        
        if success:
            return AddDocumentResponse(
                success=True,
                message="Documento agregado exitosamente",
                chunks_added=1  # Simplificado
            )
        else:
            return AddDocumentResponse(
                success=False,
                message="Error agregando documento",
                chunks_added=0
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_rag_stats():
    """Obtener estadísticas de la base de conocimiento"""
    try:
        stats = rag_service.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/context/{query}")
async def get_context(query: str, max_chunks: int = 3):
    """Obtener contexto para LLM"""
    try:
        context = rag_service.get_context_for_llm(query, max_chunks)
        return {"context": context, "query": query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 🧪 Testing del Sistema RAG

### **1. Tests de RAG**

```python
# backend/tests/test_rag.py
import pytest
from app.ai.knowledge.rag_service import RAGService
from app.ai.knowledge.embeddings import EmbeddingService
from app.ai.knowledge.vector_db import FAISSVectorDB

def test_embedding_service():
    """Test que el servicio de embeddings funcione"""
    embedding_service = EmbeddingService()
    
    # Test encoding
    texts = ["Hello world", "This is a test"]
    embeddings = embedding_service.encode_texts(texts)
    
    assert embeddings.shape[0] == 2
    assert embeddings.shape[1] == embedding_service.embedding_dim

def test_vector_db():
    """Test que la base de datos vectorial funcione"""
    vector_db = FAISSVectorDB(dimension=384)
    
    # Test agregar documentos
    documents = ["Document 1", "Document 2"]
    embeddings = [[0.1] * 384, [0.2] * 384]
    metadata = [{"id": 1}, {"id": 2}]
    
    vector_db.add_documents(documents, embeddings, metadata)
    
    # Test búsqueda
    query_embedding = [0.15] * 384
    results_docs, results_metadata, results_scores = vector_db.search(query_embedding, k=2)
    
    assert len(results_docs) == 2
    assert len(results_metadata) == 2
    assert len(results_scores) == 2

def test_rag_service():
    """Test que el servicio RAG funcione"""
    rag_service = RAGService()
    
    # Test búsqueda
    results = rag_service.search("test query", k=3)
    
    assert isinstance(results, list)
    for result in results:
        assert "text" in result
        assert "metadata" in result
        assert "score" in result
        assert "relevance" in result
```

### **2. Tests de Integración**

```python
# backend/tests/test_rag_integration.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_search_endpoint():
    """Test endpoint de búsqueda"""
    response = client.post(
        "/api/rag/search",
        json={"query": "test query", "k": 5}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total_results" in data
    assert "query" in data

def test_add_document_endpoint():
    """Test endpoint de agregar documento"""
    response = client.post(
        "/api/rag/add-document",
        json={"file_path": "test_document.txt"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "message" in data

def test_stats_endpoint():
    """Test endpoint de estadísticas"""
    response = client.get("/api/rag/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "embedding_dimension" in data
```

## 📊 Métricas de Éxito

### **🎯 Objetivos Técnicos**
- **Tiempo de Búsqueda**: < 100ms
- **Precisión**: > 90% resultados relevantes
- **Cobertura**: > 95% documentos indexados
- **Memoria**: < 256MB para base de conocimiento
- **Escalabilidad**: > 1000 documentos

### **🎯 Objetivos de Funcionalidad**
- **Búsqueda Semántica**: Funcionando correctamente
- **Integración con LLM**: Contexto relevante
- **API REST**: Todos los endpoints operativos
- **Procesamiento**: Múltiples formatos soportados
- **Testing**: > 90% cobertura de código

## ✅ Criterios de Éxito

### **📋 Checklist de Validación**
- [ ] **Sistema RAG** completamente funcional
- [ ] **Base de conocimiento** indexada
- [ ] **Búsqueda semántica** operativa
- [ ] **Integración con LLM** funcionando
- [ ] **API REST** documentada
- [ ] **Testing completo** pasando
- [ ] **Rendimiento** dentro de métricas objetivo
- [ ] **Preparación** para siguiente fase

### **🎯 Entregables de esta Fase**
- [ ] **Sistema RAG** completamente implementado
- [ ] **Base de conocimiento** estructurada
- [ ] **API de búsqueda** robusta
- [ ] **Integración con LLM** funcional
- [ ] **Testing suite** completa
- [ ] **Documentación** técnica
- [ ] **Optimización** para hardware limitado
- [ ] **Preparación** para fine-tuning

## 🚀 Siguiente Fase

Una vez completada esta fase, continuar con [**Fase 4: Fine-tuning**](./04-finetuning.md)

### **📋 Preparación para Fase 4**
- [ ] Sistema RAG funcionando
- [ ] Base de conocimiento indexada
- [ ] API de búsqueda estable
- [ ] Testing completo
- [ ] Documentación actualizada

---

**🎉 ¡Con esta fase tendrás una base de conocimiento inteligente y contextual!**

*Recuerda: RAG es la base de la inteligencia contextual. Invierte el tiempo necesario para hacerlo robusto.* 🚀
