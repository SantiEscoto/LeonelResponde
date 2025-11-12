import faiss
import numpy as np
from tinydb import TinyDB, Query
from sentence_transformers import SentenceTransformer

# --- CONFIGURACIÓN RAG ---
DB_PATH = "leonel_interacciones.json" 
RAG_COLLECTION = 'base_conocimiento_rag' 
FAISS_INDEX_PATH = 'faiss_index.bin' 
K_RESULTS = 3 # Número de resultados (preguntas) más similares a devolver

# 1. Inicializar Modelo y FAISS
try:
    print("Cargando modelo y FAISS...")
    # El mismo modelo usado para vectorizar la base de conocimiento
    model = SentenceTransformer('all-MiniLM-L6-v2') 
    # Cargar el índice FAISS que creamos en el paso anterior
    index = faiss.read_index(FAISS_INDEX_PATH)
    # Inicializar TinyDB
    db = TinyDB(DB_PATH)
    rag_table = db.table(RAG_COLLECTION)
    
except Exception as e:
    print(f"❌ ERROR al inicializar FAISS/TinyDB. Asegúrese de haber ejecutado load_knowledge_RAG.py. Error: {e}")
    exit()


def buscar_contexto_rag(pregunta_usuario: str):
    """
    Toma la pregunta del usuario, busca los vectores más similares en FAISS,
    y recupera las Preguntas y Temas de TinyDB.
    """
    print(f"\n--- Buscando contexto para: '{pregunta_usuario}' ---")
    
    # 2. Vectorizar la pregunta del usuario
    query_vector = model.encode([pregunta_usuario], convert_to_tensor=False)
    query_vector = query_vector.astype('float32')
    
    # 3. Buscar en el índice FAISS
    # D: Distancias (distancia L2), I: Índices (vector_id)
    D, I = index.search(query_vector, K_RESULTS) 
    
    # Obtener los IDs de los vectores más cercanos
    vector_ids = I[0].tolist() 
    
    # 4. Recuperar la información textual de TinyDB
    Query_db = Query()
    # TinyDB busca los registros cuyos 'vector_id' coinciden con los que nos dio FAISS
    resultados_db = rag_table.search(Query_db.vector_id.one_of(vector_ids))
    
    contexto_encontrado = []
    
    if resultados_db:
        print(f"✅ Se encontraron {len(resultados_db)} coincidencias.")
        for i, doc in enumerate(resultados_db):
            # Devolvemos la pregunta original y el tema como contexto
            contexto_encontrado.append({
                'Pregunta_similar': doc['Pregunta'],
                'Tema': doc['Tema'],
                'ID_vector': doc['vector_id'],
                'Distancia_FAISS': D[0][i] 
            })
    else:
        print("🛑 No se encontró contexto RAG relevante.")
        
    db.close()
    return contexto_encontrado


if __name__ == '__main__':
    # --- PRUEBA DEL MÓDULO RAG ---
    
    pregunta_de_prueba = "¿Qué es lo que tengo que hacer para conseguir mi beca?"
    
    contextos = buscar_contexto_rag(pregunta_de_prueba)
    
    print("\n--- RESULTADO DE CONTEXTO RAG PARA EL CHATBOT ---")
    if contextos:
        for c in contextos:
            print("---------------------------------------")
            print(f"Pregunta Original (Contexto): {c['Pregunta_similar']}")
            print(f"Tema Relacionado: {c['Tema']}")
            print(f"Distancia (menor es mejor): {c['Distancia_FAISS']:.4f}")
    else:
        print("El sistema RAG no pudo recuperar información. El chatbot procederá a buscar en documentos.")