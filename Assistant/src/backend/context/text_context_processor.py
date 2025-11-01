"""
Procesador de contexto para archivos de texto
Optimizado para rendimiento y relevancia
"""
import os
import glob
from typing import Dict, List
import time

class TextContextProcessor:
    def __init__(self, knowledge_dir: str = "data/knowledge"):
        self.knowledge_dir = knowledge_dir
        self.context_docs = {}
        self.load_context_files()
    
    def load_context_files(self):
        """Carga todos los archivos .txt de la carpeta knowledge"""
        start_time = time.time()
        
        if not os.path.exists(self.knowledge_dir):
            print(f"⚠️ Carpeta de conocimiento no encontrada: {self.knowledge_dir}")
            return
        
        # Buscar archivos .txt
        txt_files = glob.glob(os.path.join(self.knowledge_dir, "*.txt"))
        
        if not txt_files:
            print(f"📚 No se encontraron archivos .txt en {self.knowledge_dir}")
            return
        
        loaded_count = 0
        for file_path in txt_files:
            filename = os.path.basename(file_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read().strip()
                    if content:
                        self.context_docs[filename] = content
                        loaded_count += 1
                        print(f"📚 Cargado contexto: {filename} ({len(content)} caracteres)")
                    else:
                        print(f"⚠️ Archivo vacío: {filename}")
            except Exception as e:
                print(f"❌ Error cargando {filename}: {e}")
        
        load_time = time.time() - start_time
        print(f"✅ Contexto cargado: {loaded_count} archivos en {load_time:.2f}s")
    
    def get_context_for_query(self, query: str, max_chars: int = 1000) -> str:
        """
        Retorna contexto relevante para una consulta
        Optimizado para rendimiento y relevancia
        """
        if not self.context_docs:
            return ""
        
        start_time = time.time()
        
        # Buscar archivos relevantes basados en palabras clave
        query_words = [word.lower() for word in query.split() if len(word) > 2]  # Filtrar palabras muy cortas
        relevant_content = []
        
        for filename, content in self.context_docs.items():
            content_lower = content.lower()
            # Contar coincidencias de palabras clave
            matches = sum(1 for word in query_words if word in content_lower)
            
            if matches > 0:
                # Solo tomar los primeros 500 caracteres de cada archivo relevante
                preview = content[:500]
                relevant_content.append(f"--- {filename} ---\n{preview}\n")
        
        # Si no hay coincidencias, usar el primer documento
        if not relevant_content and self.context_docs:
            first_doc = list(self.context_docs.items())[0]
            filename, content = first_doc
            preview = content[:500]
            relevant_content.append(f"--- {filename} ---\n{preview}\n")
        
        # Limitar a max_chars caracteres total
        context = "\n".join(relevant_content)
        final_context = context[:max_chars]
        
        search_time = time.time() - start_time
        print(f"🔍 Contexto encontrado en {search_time:.3f}s ({len(final_context)} chars)")
        
        return final_context
    
    def get_all_context(self, max_chars: int = 2000) -> str:
        """Retorna todo el contexto disponible (para casos especiales)"""
        if not self.context_docs:
            return ""
        
        all_context = []
        for filename, content in self.context_docs.items():
            preview = content[:max_chars // len(self.context_docs)]  # Dividir espacio entre archivos
            all_context.append(f"--- {filename} ---\n{preview}\n")
        
        return "\n".join(all_context)
    
    def get_context_stats(self) -> Dict:
        """Retorna estadísticas del contexto cargado"""
        return {
            "total_files": len(self.context_docs),
            "total_chars": sum(len(content) for content in self.context_docs.values()),
            "files": list(self.context_docs.keys())
        }


