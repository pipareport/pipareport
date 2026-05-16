import mysql.connector
from supabase import create_client
import time
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv("config.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ARCHIVO_ESTADO = "ultimo_sync.json"

def cargar_ultimo_sync():
    if os.path.exists(ARCHIVO_ESTADO):
        with open(ARCHIVO_ESTADO, 'r') as f:
            return json.load(f)
    # Primera vez: trae solo los últimos 90 días
    hace_90_dias = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    return {
        "ventas": hace_90_dias,
        "caja": hace_90_dias,
        "items": hace_90_dias,
        "cobros": hace_90_dias
    }

def guardar_ultimo_sync(estado):
    with open(ARCHIVO_ESTADO, 'w') as f:
        json.dump(estado, f)

def conectar_mysql():
    return mysql.connector.connect(
        host="localhost", user="root",
        password="root", database="pipashowroom"
    )

def transformar_fila(fila):
    for campo in list(fila.keys()):
        valor = fila[campo]
        if hasattr(valor, 'isoformat'):
            fila[campo] = valor.isoformat()
        elif valor.__class__.__name__ == 'Decimal':
            fila[campo] = float(valor)
    return fila

def sincronizar_tabla(query, params, tabla_supabase):
    try:
        db = conectar_mysql()
        cursor = db.cursor(dictionary=True)
        cursor.execute(query, params)
        filas = cursor.fetchall()
        db.close()

        if not filas:
            print(f"Sin cambios - {tabla_supabase}")
            return

        for fila in filas:
            try:
                fila = transformar_fila(fila)
                supabase.table(tabla_supabase).upsert(fila).execute()
            except Exception as e:
                print(f"  Fila fallida: {e}")
                continue
        print(f"OK - {tabla_supabase} ({len(filas)} registros)")
    except Exception as e:
        print(f"Error en {tabla_supabase}: {e}")

if __name__ == "__main__":
    while True:
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        estado = cargar_ultimo_sync()

        sincronizar_tabla(
            "SELECT * FROM vta_comprobante WHERE anulado = 'N' AND fecha >= %s",
            (estado["ventas"],),
            "ventas_reporte"
        )
        sincronizar_tabla(
            "SELECT * FROM fnd_caja_diaria WHERE apertura >= %s",
            (estado["caja"],),
            "caja_diaria"
        )
        sincronizar_tabla(
            """SELECT ci.tipo, ci.comprobante, ci.linea, ci.item, ci.descripcion,
                      ci.cantidad, ci.importe, ci.iva, ci.anulado
               FROM vta_comprobante_item ci
               JOIN vta_comprobante c ON c.comprobante = ci.comprobante
               WHERE c.fecha >= %s AND ci.anulado = 'N'""",
            (estado["items"],),
            "ventas_items"
        )
        sincronizar_tabla(
            """SELECT cm.cobro, cm.linea, cm.importe, cm.modalidad, cm.tarjeta,
                       c.fecha, c.cliente
               FROM vta_cobro_medio cm
               JOIN vta_cobro c ON c.numero = cm.cobro
               WHERE c.fecha >= %s""",
            (estado["cobros"],),
            "cobros_medio"
        )
        sincronizar_tabla(
               "SELECT id, razon_social AS nombre, visible FROM vta_cliente",
               (),
               "clientes"
        )
        
        # Guardar fecha actual como último sync
        guardar_ultimo_sync({
            "ventas": ahora,
            "caja": ahora,
            "items": ahora,
            "cobros": ahora
        })

        print(f"--- Sync completo: {ahora} ---")
        time.sleep(300)