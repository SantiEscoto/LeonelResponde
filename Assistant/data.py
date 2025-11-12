from tinydb import TinyDB
import os

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
DB_PATH = "leonel_interacciones.json" 

# 1. Registro de INICIALIZACIÓN (Define Estructura y Guarda Categorías/Etiquetas)
registro_estructura_referencia = {
    'registro_id': 'ESTRUCTURA_BASE', 
    'id_usuario': None,
    'fecha_hora': None,
    'pregunta_usuario_log': 'DEFINICION_ESTRUCTURA_DE_DATOS', 
    'respuesta_ia': 'Este registro define la estructura de las Categorías (Nivel 1) y Etiquetas (Nivel 2).', 
    
    # Nivel 1: Categorías Principales
    'Tema': [
        'Mantenimiento y Promedio', 
        'Servicio Becario y AFIS', 
        'Proceso y Modificaciones', 
        'Convocatorias y Tipos de Apoyo', 
        'Reglamentos y Contacto'
    ],
    
    # Nivel 2: Subcategorías o Etiquetas
    'etiquetas': {
        'Mantenimiento y Promedio': ['Promedio Ponderado', 'Promedio Mínimo', 'Materia Reprobada', 'Calificación Mínima', 'Recuperación de Beca'],
        'Servicio Becario y AFIS': ['Horas Becario', 'Centro Gestor', 'Advertencia', 'Amonestación', 'Curso Ser Becario', 'AFIS Obligatorias'],
        'Proceso y Modificaciones': ['Renovación Automática', 'Baja de Materia', 'Baja Temporal', 'Cambio de Carrera', 'Intercambio', 'Internado Medicina'],
        'Convocatorias y Tipos de Apoyo': ['Aumento de Beca', 'Porcentaje Máximo Aumento', 'Beca SEP', 'Convocatoria SEP'],
        'Reglamentos y Contacto': ['Reglamento de Becas', 'Buzón de Becas', 'Aviso Amonestación']
    },
    
    'fuente_oficial': 'Definición de Esquema de la Base de Conocimiento'
}

# Inicializar la base de datos
db = TinyDB(DB_PATH)
print(f"Base de datos inicializada en: {DB_PATH}")

# Definir la colección principal (Logs)
interacciones_table = db.table('registros_interaccion')
print("Colección 'registros_interaccion' definida y lista para ser usada.")

# 2. Limpiar la tabla de registros anteriores
interacciones_table.truncate() 
print("Tabla vaciada de registros anteriores!")

# 3. Insertar el registro de estructura y categorías
interacciones_table.insert(registro_estructura_referencia)
print("Estructura base y taxonomía (categorías/etiquetas) insertada.")


# Cierre de la base de datos
db.close()
print("Ejecución de creación de base de datos finalizada con éxito.")