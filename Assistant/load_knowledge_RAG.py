import pandas as pd
from tinydb import TinyDB
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# --- CONFIGURACIÓN DE ARCHIVOS ---
DB_PATH = "leonel_interacciones.json" 
RAG_COLLECTION = 'base_conocimiento_rag' # Nueva colección para la data RAG
KNOWLEDGE_FILE = '2500_Preguntas.csv'
FAISS_INDEX_PATH = 'faiss_index.bin' # Archivo donde se guarda el índice de búsqueda
FUENTE_OFICIAL = "Reglamento de Becas y Financiamiento Educativo (Libro Séptimo)" 


def load_data_and_vectorize():
    """
    Carga el CSV, vectoriza SOLO la columna 'Pregunta' para la búsqueda
    y guarda la data textual de Pregunta y Tema en TinyDB.
    """
    
    # 1. Inicializar Modelo de Embeddings
    try:
        print("Cargando modelo de embeddings (SentenceTransformer)...")
        model = SentenceTransformer('all-MiniLM-L6-v2') 
    except Exception as e:
        print(f"❌ ERROR: Falló la carga del modelo. Verifique la instalación. Error: {e}")
        return

    # 2. Cargar y validar el archivo CSV con Pandas (Solo necesitamos Tema y Pregunta)
    print(f"\n--- INICIANDO CARGA RAG desde {KNOWLEDGE_FILE} ---")
    try:
        # Usamos el delimitador punto y coma, que es el más probable
        df = pd.read_csv(
            KNOWLEDGE_FILE, 
            delimiter=';', # <--- DELIMITADOR PUNTO Y COMA
            encoding='latin-1',
            header=None, 
            on_bad_lines='skip' # Ignora líneas con errores
        )
        
        # Asumimos que Tema y Pregunta están en las columnas 1 y 2.
        if df.shape[1] < 3:
             print("❌ ERROR: El CSV debe tener al menos 3 columnas (asumiendo ID, Tema, Pregunta) separadas por ';'.")
             return

        # Seleccionamos las columnas 1 y 2 (Tema y Pregunta)
        df = df.iloc[:, [1, 2]] 
        
        # Asignamos nombres para mayor claridad
        df.columns = ['Tema', 'Pregunta']
        
        # Eliminamos filas con preguntas vacías
        df = df.dropna(subset=['Pregunta']) 
        
        registros_a_cargar = len(df)
        print(f"CSV cargado. {registros_a_cargar} registros válidos encontrados.")
        
    except FileNotFoundError:
        print(f"❌ ERROR: No se encontró el CSV '{KNOWLEDGE_FILE}'. Verifique el nombre y la ruta.")
        return
    except Exception as e:
        print(f"❌ ERROR: Falló la lectura del CSV. Error: {e}")
        return

    # 3. Generar Embeddings (Vectores)
    
    df['vector_id'] = df.index 
    
    preguntas_para_vectorizar = df['Pregunta'].tolist()
    print(f"Generando {registros_a_cargar} vectores (embeddings) de las preguntas...")
    
    # Esta es la línea RAG clave: convierte la Pregunta en vectores
    embeddings = model.encode(preguntas_para_vectorizar, convert_to_tensor=False)
    vector_dim = embeddings.shape[1] 
    
    # 4. Crear y Guardar el Índice FAISS
    
    index = faiss.IndexFlatL2(vector_dim) 
    index.add(embeddings.astype('float32')) 
    
    faiss.write_index(index, FAISS_INDEX_PATH)
    print(f"✅ Índice FAISS creado y guardado en: {FAISS_INDEX_PATH}")
    
    # 5. Cargar la data textual en TinyDB (Colección RAG)
    
    data = df.to_dict('records') 

    db = TinyDB(DB_PATH)
    rag_table = db.table(RAG_COLLECTION)
    
    rag_table.truncate() 
    rag_table.insert_multiple(data) 
    
    db.close()
    
    print("\n--- CARGA Y VECTORIZACIÓN RAG COMPLETADA ---")
    print(f"✅ TinyDB Collection '{RAG_COLLECTION}' y FAISS listos con {registros_a_cargar} registros.")


if __name__ == '__main__':
    load_data_and_vectorize()