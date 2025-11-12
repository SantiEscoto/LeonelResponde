import csv
from tinydb import TinyDB
import os

DB_PATH = "leonel_interacciones.json" 
TABLE_NAME = 'registros_interaccion'
KNOWLEDGE_FILE = '2500_Preguntas.csv'
FUENTE_OFICIAL = "Reglamento de Becas y Financiamiento Educativo (Libro Séptimo)" 

def load_data_into_tinydb():
    if not os.path.exists(KNOWLEDGE_FILE):
        print(f"Error: Archivo de preguntas '{KNOWLEDGE_FILE}' no encontrado.")
        return

    knowledge_records = []
    
    try:
        # Usamos un lector de texto simple, no el módulo CSV, para evitar conflictos de delimitador
        with open(KNOWLEDGE_FILE, mode='r', encoding='latin-1') as f:
            lines = f.readlines()
            
            if not lines:
                print("Error: El archivo está vacío.")
                return

            # 1. Leer y limpiar los encabezados (la primera línea)
            fieldnames_raw = lines[0].strip()
            # 🛑 CRÍTICO: Forzamos la separación por punto y coma (;)
            fieldnames_clean = [name.strip() for name in fieldnames_raw.split(';')]
            
            try:
                # Obtenemos el índice (posición) de las columnas que nos interesan
                idx_pregunta = fieldnames_clean.index('Pregunta')
                idx_tema = fieldnames_clean.index('Tema')
            except ValueError as e:
                print(f"ERROR: No se encontró la columna requerida en el CSV. {e}")
                print(f"Encabezados encontrados: {fieldnames_clean}")
                return

            # 2. Procesar las filas de datos restantes (desde la segunda línea en adelante)
            for index, line in enumerate(lines[1:]):
                
                # Forzamos la separación de la línea por punto y coma (;)
                data_row = [field.strip().replace('\0', '') for field in line.split(';')]
                
                # Si la fila no tiene suficientes columnas, la ignoramos
                if len(data_row) < max(idx_pregunta, idx_tema) + 1:
                    continue

                # Extraemos y limpiamos
                pregunta = data_row[idx_pregunta]
                tema = data_row[idx_tema]
                
                # Filtro: Solo omitimos si la cadena LIMPIA está vacía
                if not pregunta or not tema:
                    continue

                record = {
                    'registro_id': f"Q{index+1:05d}", 
                    'id_usuario': None,         
                    'fecha_hora': None,         
                    'pregunta_usuario_log': pregunta,
                    'respuesta_ia': "PENDIENTE DE RESPUESTA OFICIAL", 
                    'Tema': tema,      
                    'etiquetas': [],                         
                    'fuente_oficial': FUENTE_OFICIAL         
                }
                knowledge_records.append(record)
        
        print(f"Archivos leídos con éxito. Registros encontrados: {len(knowledge_records)}")

    except Exception as e:
        print(f"ERROR al procesar el archivo CSV: {e}")
        return

    # --- 3. INSERCIÓN EN TINYDB ---
    try:
        if knowledge_records:
            with TinyDB(DB_PATH) as db:
                interacciones_table = db.table(TABLE_NAME)
                interacciones_table.insert_multiple(knowledge_records)
                print(f"🎉 Éxito: Se cargaron {len(knowledge_records)} registros de preguntas en la DB.")
        else:
            print("🛑 Advertencia: No hay registros válidos para cargar.")
            
    except Exception as e:
        print(f"ERROR al guardar datos en TinyDB: {e}")


if __name__ == "__main__":
    load_data_into_tinydb()