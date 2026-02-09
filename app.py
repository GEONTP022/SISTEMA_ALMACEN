import streamlit as st
import pandas as pd
from supabase import create_client
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN DE PÁGINA (Debe ser lo primero) ---
st.set_page_config(
    page_title="VillaFix OS",
    layout="wide",
    initial_sidebar_state="collapsed" # Ocultamos la barra por defecto para hacer la nuestra
)

# --- 2. CONEXIÓN (Blindada) ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("⚠️ Error de conexión. Revisa los Secrets.")
    st.stop()

# --- 3. INYECCIÓN DE CSS (AQUÍ VA LA MAGIA DEL FIGMA) ---
# Esto permite que quitemos los bordes feos de Streamlit y usemos tus colores
def local_css():
    st.markdown("""
    <style>
        /* Color de fondo general */
        .stApp {
            background-color: #F5F7FA; /* Gris muy suave profesional */
        }
        
        /* Ocultar menú de hamburguesa y footer de Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Estilo para TUS tarjetas (Cards) */
        .card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        /* Títulos personalizados */
        h1, h2, h3 {
            color: #1E293B; /* Azul oscuro corporativo */
            font-family: 'Helvetica Neue', sans-serif;
        }
        
        /* Botones personalizados */
        .stButton>button {
            background-color: #2563EB; /* Azul VillaFix */
            color: white;
            border-radius: 8px;
            border: none;
            padding: 10px 24px;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #1D4ED8;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 4. INTERFAZ TIPO DASHBOARD ---

# Encabezado (Header)
with st.container():
    col_logo, col_titulo, col_user = st.columns([1, 4, 1])
    with col_titulo:
        st.markdown("## 📱 Centro de Control VillaFix")
    with col_user:
        st.caption("🟢 Online | Admin")

st.markdown("---")

# Métricas (KPIs) - Diseñadas con HTML para que se vean como Figma
col1, col2, col3, col4 = st.columns(4)

def card_metrica(titulo, valor, delta, color):
    return f"""
    <div class="card">
        <p style="color: #64748B; font-size: 14px; margin:0;">{titulo}</p>
        <h2 style="color: {color}; margin:0;">{valor}</h2>
        <p style="color: {color}; font-size: 12px; margin:0;">{delta}</p>
    </div>
    """

with col1:
    st.markdown(card_metrica("Ventas Hoy", "S/ 350.00", "▲ 12%", "#10B981"), unsafe_allow_html=True)
with col2:
    st.markdown(card_metrica("Stock Crítico", "4 Items", "▼ Reponer", "#EF4444"), unsafe_allow_html=True)
with col3:
    st.markdown(card_metrica("Clientes Nuevos", "12", "+2 ayer", "#3B82F6"), unsafe_allow_html=True)
with col4:
    st.markdown(card_metrica("Ganancia Neta", "S/ 120.00", "34% Margen", "#6366F1"), unsafe_allow_html=True)

# --- 5. CUERPO PRINCIPAL ---
st.write("") # Espacio
st.subheader("📦 Inventario en Tiempo Real")

# Aquí va la tabla, pero la haremos bonita luego
# (Copia aquí la lógica de conexión a la tabla productos que hicimos antes)
# Por ahora pongo un placeholder:
st.info("👆 Aquí cargaremos tu diseño de tabla cuando me pases el Figma.")
