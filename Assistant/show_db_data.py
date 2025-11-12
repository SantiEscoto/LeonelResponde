from tinydb import TinyDB
from tabulate import tabulate
import os

# --- CONFIGURACIÓN ---
DB_PATH = "leonel_interacciones.json"
TABLE_NAME = 'registros_interaccion'

def show_only_table():
    # 1. Definición explícita de la estructura (Tus columnas)
    headers = ['registro_id', 'id_usuario', 'fecha_hora', 'pregunta_usuario_log',
               'respuesta_ia', 'Tema', 'etiquetas', 'fuente_oficial']

    rows = []

    try:
        if os.path.exists(DB_PATH):
            with TinyDB(DB_PATH) as db:
                data = db.table(TABLE_NAME).all()
            # Si hay datos, construir filas; si no, dejar `rows` vacío (sólo encabezados)
            for doc in data:
                rows.append([doc.get(h, "N/A") for h in headers])
        # Si no existe el archivo, `rows` queda vacío: se mostrará solo la cabecera
    except Exception:
        # En caso de error de lectura, mostrar únicamente la tabla vacía (solo encabezados)
        rows = []

    # Mostrar únicamente la tabla (sin mensajes extra). No mostrar índice.
    print(tabulate(rows, headers=headers, tablefmt="simple", showindex=False))


if __name__ == "__main__":
    show_only_table()