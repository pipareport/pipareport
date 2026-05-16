import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import date

st.set_page_config(page_title="Pipa Showroom - Reportes", layout="wide")
st.title("📊 Panel de Ventas - Pipa Showroom")

from dotenv import load_dotenv
import os

load_dotenv("config.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Cargar datos
ventas = pd.DataFrame(supabase.table("ventas_reporte").select("*").execute().data)
caja = pd.DataFrame(supabase.table("caja_diaria").select("*").execute().data)
items = pd.DataFrame(supabase.table("ventas_items").select("*").execute().data)
clientes = pd.DataFrame(supabase.table("clientes").select("*").execute().data)
cobros = pd.DataFrame(supabase.table("cobros_medio").select("*").execute().data)

# Convertir fechas
if not ventas.empty:
    ventas['fecha'] = pd.to_datetime(ventas['fecha'])
if not cobros.empty:
    cobros['fecha'] = pd.to_datetime(cobros['fecha'])
if not caja.empty:
    caja['apertura'] = pd.to_datetime(caja['apertura'])

tab1, tab2, tab3 = st.tabs(["💰 Caja Diaria", "🧾 Facturas", "📦 Productos"])

# ── TAB 1: CAJA DIARIA ──────────────────────────────────────────────
with tab1:
    st.subheader("Caja Diaria")

    col_fecha1, col_fecha2, col_boton = st.columns([2, 2, 1])
    fecha_desde = col_fecha1.date_input("Desde", value=date.today(), key="caja_desde")
    fecha_hasta = col_fecha2.date_input("Hasta", value=date.today(), key="caja_hasta")
    cierre_hoy = col_boton.button("📅 Ver solo hoy")

    if cierre_hoy:
        fecha_desde = date.today()
        fecha_hasta = date.today()

    # Filtro por medio de pago
    medios_disponibles = ["TODOS", "CAJA", "TARJETA", "CUENTA", "CHEQUE"]
    medio_seleccionado = st.selectbox("Filtrar por medio de pago", medios_disponibles, key="medio_caja")

    if not cobros.empty:
        filtro_cobros = cobros[
            (cobros['fecha'].dt.date >= fecha_desde) &
            (cobros['fecha'].dt.date <= fecha_hasta)
        ]

        if medio_seleccionado != "TODOS":
            filtro_cobros = filtro_cobros[filtro_cobros['modalidad'] == medio_seleccionado]

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Cobrado", f"${filtro_cobros['importe'].sum():,.2f}")
        col2.metric("Cantidad de Cobros", len(filtro_cobros))
        efectivo = filtro_cobros[filtro_cobros['modalidad'] == 'CAJA']['importe'].sum()
        col3.metric("Efectivo", f"${efectivo:,.2f}")

        st.subheader("Resumen por Medio de Pago")
        resumen_medios = filtro_cobros.groupby('modalidad').agg(
            Total=('importe', 'sum'),
            Cantidad=('importe', 'count')
        ).reset_index().rename(columns={'modalidad': 'Medio de Pago'})
        st.dataframe(resumen_medios, use_container_width=True)

        st.subheader("Detalle de Cobros")
        st.dataframe(filtro_cobros[['fecha', 'cobro', 'modalidad', 'importe']].rename(columns={
            'fecha': 'Fecha', 'cobro': 'Comprobante',
            'modalidad': 'Medio', 'importe': 'Importe'
        }), use_container_width=True)
    else:
        st.warning("Sin datos de cobros.")

# ── TAB 2: FACTURAS ─────────────────────────────────────────────────
with tab2:
    st.subheader("Facturas Emitidas")
    if not ventas.empty:
        col_fecha1, col_fecha2, col_boton = st.columns([2, 2, 1])
        fecha_desde_f = col_fecha1.date_input("Desde", value=date.today(), key="fact_desde")
        fecha_hasta_f = col_fecha2.date_input("Hasta", value=date.today(), key="fact_hasta")
        hoy_fact = col_boton.button("📅 Ver solo hoy", key="hoy_fact")

        if hoy_fact:
            fecha_desde_f = date.today()
            fecha_hasta_f = date.today()

        filtro = ventas[
            (ventas['fecha'].dt.date >= fecha_desde_f) &
            (ventas['fecha'].dt.date <= fecha_hasta_f)
        ]

        col1, col2 = st.columns(2)
        col1.metric("Total Facturado", f"${filtro['total'].sum():,.2f}")
        col2.metric("Cantidad de Facturas", len(filtro))

        if not clientes.empty:
            filtro = filtro.merge(clientes, left_on='cliente', right_on='id', how='left')

        columnas = ['fecha', 'comprobante', 'total']
        nombres = {'fecha': 'Fecha', 'comprobante': 'Comprobante', 'total': 'Total'}
        if 'nombre' in filtro.columns:
            columnas.insert(2, 'nombre')
            nombres['nombre'] = 'Cliente'

        st.dataframe(filtro[columnas].rename(columns=nombres), use_container_width=True)
    else:
        st.warning("Sin datos de facturas.")

# ── TAB 3: PRODUCTOS ────────────────────────────────────────────────
with tab3:
    st.subheader("Productos Vendidos")
    if not items.empty and not ventas.empty:
        col_fecha1, col_fecha2, col_boton = st.columns([2, 2, 1])
        fecha_desde_p = col_fecha1.date_input("Desde", value=date.today(), key="prod_desde")
        fecha_hasta_p = col_fecha2.date_input("Hasta", value=date.today(), key="prod_hasta")
        hoy_prod = col_boton.button("📅 Ver solo hoy", key="hoy_prod")

        if hoy_prod:
            fecha_desde_p = date.today()
            fecha_hasta_p = date.today()

        # Filtrar ventas por fecha y cruzar con items
        ventas_filtradas = ventas[
            (ventas['fecha'].dt.date >= fecha_desde_p) &
            (ventas['fecha'].dt.date <= fecha_hasta_p)
        ][['comprobante']]

        items_filtrados = items.merge(ventas_filtradas, on='comprobante', how='inner')

        resumen = items_filtrados.groupby('descripcion').agg(
            Cantidad=('cantidad', 'sum'),
            Importe=('importe', 'sum')
        ).reset_index().sort_values('Importe', ascending=False)

        col1, col2 = st.columns(2)
        col1.metric("Total Items Vendidos", f"{resumen['Cantidad'].sum():,.0f}")
        col2.metric("Importe Total", f"${resumen['Importe'].sum():,.2f}")

        st.dataframe(resumen.rename(columns={'descripcion': 'Producto'}), use_container_width=True)
    else:
        st.warning("Sin datos de productos.")