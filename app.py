import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from supabase import create_client
from streamlit_option_menu import option_menu
from datetime import datetime, date, timedelta
import io
import textwrap
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
import tempfile

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="VillaFix OS",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except:
    st.error("⚠️ Error de conexión. Revisa tus secrets.")
    st.stop()

# --- 3. ESTILOS CSS (DISEÑO DEL VIDEO) ---
st.markdown("""
<style>
    /* Fondo general */
    .stApp { background-color: #f3f4f6; }
    
    /* Ajuste de la barra lateral para que se vea limpia */
    section[data-testid="stSidebar"] {
        background-color: #111827; /* Color oscuro profesional */
    }
    
    /* Estilo de Tarjetas del Dashboard */
    .kpi-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #00C2CB; /* Cian del video */
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 10px;
    }
    .kpi-value { font-size: 28px; font-weight: 800; color: #1f2937; }
    .kpi-label { font-size: 13px; color: #6b7280; text-transform: uppercase; font-weight: 600; }

    /* Botones estilo App */
    .stButton>button {
        border-radius: 8px;
        font-weight: 700;
        text-transform: uppercase;
        width: 100%;
        border: none;
        background-color: #2563EB;
        color: white;
        transition: all 0.2s;
    }
    .stButton>button:hover { background-color: #1d4ed8; box-shadow: 0 4px 10px rgba(37,99,235,0.3); }
    
    /* Inputs más limpios */
    .stTextInput>div>div>input { border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# --- 4. BARRA LATERAL PRO (COMO EL VIDEO) ---
with st.sidebar:
    # Logo o Título estilizado
    st.markdown("<h2 style='text-align: center; color: white; margin-bottom: 20px;'>VillaFix OS</h2>", unsafe_allow_html=True)
    
    # MENÚ CON ESTILOS PERSONALIZADOS
    selected = option_menu(
        menu_title="Módulos del Usuario",  # Título del menú
        options=["Inicio", "Productos", "Ventas", "Servicio Técnico", "Mantenimiento Caja", "Configuración"],
        icons=["speedometer2", "box-seam", "cart4", "phone", "cash-stack", "gear"],
        menu_icon="grid-fill",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#00C2CB", "font-size": "18px"}, # Iconos color Cian
            "nav-link": {
                "font-size": "15px",
                "text-align": "left",
                "margin": "5px",
                "color": "white",
                "--hover-color": "#1f2937"
            },
            "nav-link-selected": {"background-color": "#2563EB"}, # Azul seleccionado
            "menu-title": {"color": "#9ca3af", "font-size": "12px", "font-weight": "bold", "margin-bottom": "10px"}
        }
    )
    
    st.markdown("---")
    # Usuario activo mini
    if 'usuario' not in st.session_state: st.session_state.usuario = "Admin"
    st.caption(f"👤 Usuario: {st.session_state.usuario}")

# --- 5. LOGICA DE NAVEGACIÓN ---

# A) MÓDULO INICIO (DASHBOARD)
if selected == "Inicio":
    st.markdown("### 🚀 Panel de Control")
    
    # Datos falsos para visualización si la DB falla, o reales si conecta
    try:
        # Intento de cálculo real
        ventas_hoy = 0.0
        reparaciones_hoy = 0.0
        # Aquí irían las queries reales
    except:
        pass

    # TARJETAS KPI (ESTILO VIDEO)
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="kpi-card"><div class="kpi-value">S/ 545.00</div><div class="kpi-label">Ventas del Día</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-value">12</div><div class="kpi-label">Equipos en Taller</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-value">S/ 1,200</div><div class="kpi-label">Caja Total</div></div>', unsafe_allow_html=True)

    st.markdown("#### 📈 Rendimiento Mensual")
    # Gráfico de ejemplo
    data = pd.DataFrame({'Días': ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab'], 'Ventas': [150, 230, 180, 320, 400, 545]})
    st.bar_chart(data.set_index('Días'))

# B) MÓDULO PRODUCTOS (INVENTARIO)
elif selected == "Productos":
    st.markdown("### 📦 Gestión de Inventario")
    t1, t2 = st.tabs(["Catálogo", "Nuevo Producto"])
    
    with t1:
        st.markdown("#### Lista de Productos")
        search = st.text_input("🔍 Buscar producto...", placeholder="Nombre o Código")
        try:
            q = supabase.table("productos").select("*")
            if search: q = q.ilike("nombre", f"%{search}%")
            df = pd.DataFrame(q.execute().data)
            if not df.empty:
                st.dataframe(df[['nombre', 'precio', 'stock', 'costo']], use_container_width=True)
            else:
                st.info("No hay productos registrados.")
        except Exception as e:
            st.error(f"Error de base de datos: {e}")

    with t2:
        st.markdown("#### Registrar Nuevo")
        with st.form("new_prod"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nombre del Producto")
            s = c2.number_input("Stock Inicial", min_value=0, value=1)
            p = c1.number_input("Precio Venta (S/)", min_value=0.0)
            c = c2.number_input("Costo Compra (S/)", min_value=0.0)
            
            if st.form_submit_button("💾 Guardar Producto"):
                try:
                    supabase.table("productos").insert({
                        "nombre": n, "stock": s, "precio": p, "costo": c
                    }).execute()
                    st.success("✅ Producto agregado correctamente")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# C) MÓDULO VENTAS (POS)
elif selected == "Ventas":
    st.markdown("### 🛒 Punto de Venta")
    c_cat, c_ticket = st.columns([1.5, 1])
    
    with c_cat:
        st.info("Selecciona productos del inventario")
        # (Aquí va la lógica de búsqueda de productos que ya teníamos)
        
    with c_ticket:
        st.markdown("""
        <div style="background:white; padding:15px; border-radius:10px; border:1px solid #ddd;">
            <h4 style="text-align:center;">TICKET DE VENTA</h4>
            <hr>
            <p style="text-align:center; color:gray;">Carrito Vacío</p>
            <h3 style="text-align:right;">Total: S/ 0.00</h3>
            <button style="width:100%; background:#10b981; color:white; border:none; padding:10px; border-radius:5px; font-weight:bold;">COBRAR</button>
        </div>
        """, unsafe_allow_html=True)

# D) MÓDULO SERVICIO TÉCNICO
elif selected == "Servicio Técnico":
    st.markdown("### 🛠️ Taller de Reparaciones")
    t_ingreso, t_lista = st.tabs(["Nuevo Ingreso", "En Taller"])
    
    with t_ingreso:
        c1, c2 = st.columns(2)
        dni = c1.text_input("DNI Cliente")
        nom = c2.text_input("Nombre Cliente")
        eq = c1.text_input("Equipo (Modelo)")
        falla = c2.text_area("Falla Reportada")
        precio = st.number_input("Precio Estimado", 0.0)
        
        if st.button("Generar Orden de Servicio"):
            # Lógica de guardado
            st.success("Orden Generada #001")

# E) MANTENIMIENTO CAJA
elif selected == "Mantenimiento Caja":
    st.markdown("### 💵 Flujo de Caja")
    st.write("Aquí podrás ver los movimientos de entrada y salida de dinero.")

# F) CONFIGURACIÓN
elif selected == "Configuración":
    st.markdown("### ⚙️ Ajustes del Sistema")
    st.write("Versión 4.0 - Enterprise")
