import pandas as pd
from tinydb import TinyDB, Query
import faiss 
import numpy as np 
import os
from sentence_transformers import SentenceTransformer 
import time

# --- CONFIGURACIÓN DE ARCHIVOS Y BASE DE DATOS ---
DB_PATH = "leonel_interacciones.json" 
# NOTA IMPORTANTE: Si tu CSV se llama diferente, ¡cambia esta línea!
CSV_FILE = './2500_Preguntas.csv' 
DELIMITER = ';' # CORRECCIÓN FINAL: Usamos punto y coma (;) como delimitador.
RAG_COLLECTION = 'base_conocimiento_rag' 
FAISS_INDEX_PATH = 'faiss_index.bin' 

# ------------------------------------------------------------------
# <<< LÓGICA RAG: CARGA DE MODELO DE EMBEDDINGS >>>
# ------------------------------------------------------------------
try:
    print("Cargando modelo de embeddings (all-MiniLM-L6-v2)...")
    # Asegúrese de tener instalado: pip install sentence-transformers faiss-cpu
    model = SentenceTransformer('all-MiniLM-L6-v2') 
except Exception as e:
    print(f"❌ ERROR: No se pudo cargar el modelo de embeddings. Verifique las librerías: {e}")
    exit()
# ------------------------------------------------------------------


def cargar_y_vectorizar_rag():
    print(f"Iniciando carga y vectorización RAG en: {DB_PATH}")
    start_time = time.time()
    
    # --- 2. Cargar y validar el archivo CSV (LÓGICA ANTERIOR) ---
    try:
        # La lectura del CSV se mantiene idéntica
        df = pd.read_csv(CSV_FILE, delimiter=DELIMITER, encoding='latin-1')
        # CORRECCIÓN FINAL: Usamos las columnas 0, 1 y 2, que son las correctas.
        df = df.iloc[:, [0, 1, 2]] 
        df.columns = ['Tema', 'Pregunta', 'Contexto_RAG']
        df = df.dropna(subset=['Contexto_RAG']) 
        registros_a_cargar = len(df)
        
        if registros_a_cargar == 0:
            print("❌ ERROR: El CSV no contiene registros válidos después de la limpieza.")
            return

        print(f"CSV cargado. Registros válidos encontrados: {registros_a_cargar}")
        
    except FileNotFoundError:
        print(f"❌ ERROR: No se encontró el CSV '{CSV_FILE}'. Verifique el nombre y la ruta.")
        return
    except Exception as e: 
        print(f"❌ ERROR: Falló la lectura del CSV. El error fue: {e}")
        # El error anterior "Error tokenizing data" desaparece con estas correcciones.
        print(f"Detalle del error: {e}")
        return

    # ------------------------------------------------------------------
    # <<< LÓGICA RAG CLAVE: VECTORIZACIÓN Y FAISS (NUEVO) >>>
    # ------------------------------------------------------------------
    
    # 1. Asignar el ID de ENLACE (puente entre FAISS y TinyDB)
    df['vector_id'] = df.index 
    
    # 2. Generar Embeddings
    preguntas_para_vectorizar = df['Pregunta'].tolist()
    print(f"Generando {registros_a_cargar} vectores (embeddings)...")
    embeddings = model.encode(preguntas_para_vectorizar, convert_to_tensor=False)
    vector_dim = embeddings.shape[1]
    
    # 3. Crear y Guardar el Índice FAISS
    index = faiss.IndexFlatL2(vector_dim) 
    index.add(embeddings.astype('float32')) 
    faiss.write_index(index, FAISS_INDEX_PATH)
    print(f"✅ Índice FAISS creado y guardado en: {FAISS_INDEX_PATH}")
    
    # ------------------------------------------------------------------
    
    
    # --- 5. Cargar la data textual en TinyDB (LÓGICA ANTERIOR + vector_id) ---
    
    # Convertir a formato TinyDB, incluyendo el campo vector_id nuevo
    data = df.to_dict('records')

    db = TinyDB(DB_PATH)