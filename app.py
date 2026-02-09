import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from supabase import create_client
from streamlit_option_menu import option_menu
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="VillaFix System", layout="wide", page_icon="🔧")

# --- CONEXIÓN A SUPABASE ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except:
    st.error("⚠️ Error de conexión: Revisa los Secrets en Streamlit Cloud.")
    st.stop()

# --- TOKEN API DNI (USARÉ UNA DE PRUEBA, PERO RECOMIENDO SACAR LA TUYA EN APIS.NET.PE) ---
# Puedes cambiar este token por uno tuyo gratuito de: https://apis.net.pe/ o similar
API_DNI_TOKEN = "apis-token-1.aT87s56.23i" # Este es un ejemplo, idealmente usa el tuyo
API_DNI_URL = "https://api.apis.net.pe/v2/reniec/dni"

# --- ESTILOS CSS (TEMA BUSINESS) ---
st.markdown("""
<style>
    /* Forzar tema claro profesional */
    .stApp { background-color: #f4f6f9; }
    h1, h2, h3, p, div, span, label { color: #212529 !important; }
    
    /* Inputs y Botones */
    .stTextInput>div>div>input { border-radius: 5px; border: 1px solid #ced4da; }
    .stButton>button { border-radius: 5px; font-weight: 600; }
    
    /* Tarjetas Dashboard */
    .dashboard-card {
        padding: 20px; border-radius: 10px; color: white !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-bottom: 10px;
    }
    .card-green { background-color: #28a745; }
    .card-orange { background-color: #fd7e14; }
    .card-blue { background-color: #17a2b8; }
    .card-yellow { background-color: #ffc107; color: #333 !important; }
</style>
""", unsafe_allow_html=True)

# --- MENÚ LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: white !important;'>VillaFix 🔧</h2>", unsafe_allow_html=True)
    
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Clientes", "Inventario", "Ventas"], 
        icons=["speedometer2", "people-fill", "box-seam", "cart4"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#262b3d"},
            "icon": {"color": "white", "font-size": "18px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "color": "white"},
            "nav-link-selected": {"background-color": "#007bff"},
        }
    )

# --- FUNCIONES ---
def consultar_dni_reniec(dni):
    """Consulta DNI en API externa"""
    try:
        # Intento 1: API pública simple (A veces falla si tiene mucha carga)
        response = requests.get(f"https://api.apis.net.pe/v1/dni?numero={dni}")
        if response.status_code == 200:
            data = response.json()
            return data.get("nombre", "") # Devuelve nombre completo
    except:
        pass
    return None

def subir_imagen(archivo):
    try:
        filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name}"
        bucket = "fotos_productos"
        file_bytes = archivo.getvalue()
        supabase.storage.from_(bucket).upload(filename, file_bytes, {"content-type": archivo.type})
        return supabase.storage.from_(bucket).get_public_url(filename)
    except:
        return None

# --- LÓGICA DE PÁGINAS ---

if selected == "Dashboard":
    st.markdown("### 📊 Resumen General")
    
    try:
        # Contadores rápidos
        prod_count = supabase.table("productos").select("id", count="exact").execute().count
        client_count = supabase.table("clientes").select("id", count="exact").execute().count
    except:
        prod_count = 0
        client_count = 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="dashboard-card card-green"><h3>👥 {client_count}</h3><p>Clientes Registrados</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="dashboard-card card-orange"><h3>📦 {prod_count}</h3><p>Productos en Stock</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="dashboard-card card-blue"><h3>🛒 0</h3><p>Ventas del Mes</p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="dashboard-card card-yellow"><h3>💰 S/ 0</h3><p>Caja Chica</p></div>', unsafe_allow_html=True)

# --- MÓDULO DE CLIENTES (NUEVO) ---
elif selected == "Clientes":
    st.markdown("### 👥 Gestión de Clientes")
    
    tab1, tab2 = st.tabs(["🆕 Nuevo Cliente", "📋 Directorio"])
    
    # PESTAÑA 1: REGISTRAR
    with tab1:
        st.write("Ingresa el DNI y presiona **ENTER** o el botón buscar para autocompletar.")
        
        # Variables de estado para guardar el nombre si se encuentra
        if 'nombre_cliente' not in st.session_state: st.session_state.nombre_cliente = ""
        
        col_dni, col_btn = st.columns([3, 1])
        with col_dni:
            dni_input = st.text_input("DNI (8 dígitos)", max_chars=8)
        with col_btn:
            st.write("") # Espacio
            st.write("") 
            btn_buscar = st.button("🔍 Buscar RENIEC", type="primary")
            
        if btn_buscar and dni_input:
            with st.spinner("Consultando RENIEC..."):
                nombre_encontrado = consultar_dni_reniec(dni_input)
                if nombre_encontrado:
                    st.session_state.nombre_cliente = nombre_encontrado
                    st.success("✅ ¡Datos encontrados!")
                else:
                    st.warning("No se encontró el DNI o la API está saturada. Ingrese manual.")

        with st.form("form_cliente"):
            nombre = st.text_input("Nombre Completo", value=st.session_state.nombre_cliente)
            c_tel, c_email = st.columns(2)
            telefono = c_tel.text_input("Teléfono / WhatsApp")
            email = c_email.text_input("Correo Electrónico (Opcional)")
            direccion = st.text_input("Dirección")
            
            if st.form_submit_button("💾 Guardar Cliente"):
                datos = {"dni": dni_input, "nombre": nombre, "telefono": telefono, "email": email, "direccion": direccion}
                try:
                    supabase.table("clientes").insert(datos).execute()
                    st.success(f"Cliente {nombre} registrado correctamente.")
                    st.session_state.nombre_cliente = "" # Limpiar
                except Exception as e:
                    st.error(f"Error (Posible DNI duplicado): {e}")

    # PESTAÑA 2: VER CLIENTES
    with tab2:
        response = supabase.table("clientes").select("*").order("created_at", desc=True).execute()
        df_clientes = pd.DataFrame(response.data)
        if not df_clientes.empty:
            st.dataframe(
                df_clientes[["dni", "nombre", "telefono", "direccion"]], 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hay clientes registrados aún.")

# --- MÓDULO DE INVENTARIO (YA LO TENÍAS) ---
elif selected == "Inventario":
    st.markdown("### 📦 Inventario & Productos")
    
    t_ver, t_add = st.tabs(["Ver Stock", "Agregar Producto"])
    
    with t_ver:
        filtro = st.text_input("🔍 Buscar Producto...")
        query = supabase.table("productos").select("*")
        if filtro:
            query = query.ilike("nombre", f"%{filtro}%")
        data = query.execute().data
        
        if data:
            cols = st.columns(4)
            for i, row in enumerate(data):
                with cols[i % 4]:
                    with st.container(border=True):
                        st.markdown(f"**{row['nombre']}**")
                        st.caption(f"{row.get('marca','Genérico')}")
                        if row['imagen_url']:
                            st.image(row['imagen_url'], use_container_width=True)
                        st.markdown(f"💰 **S/ {row['precio']}**")
                        st.caption(f"Stock: {row['stock']}")
        else:
            st.info("Sin resultados.")

    with t_add:
        with st.form("add_prod", clear_on_submit=True):
            nom = st.text_input("Nombre")
            mar = st.text_input("Marca")
            cat = st.selectbox("Categoría", ["Repuestos", "Pantallas", "Accesorios"])
            pre = st.number_input("Precio", min_value=0.0)
            stk = st.number_input("Stock", min_value=1)
            foto = st.file_uploader("Foto")
            
            if st.form_submit_button("Guardar"):
                url_img = subir_imagen(foto) if foto else None
                supabase.table("productos").insert({
                    "nombre": nom, "marca": mar, "categoria": cat, 
                    "precio": pre, "stock": stk, "imagen_url": url_img
                }).execute()
                st.success("Guardado!")

elif selected == "Ventas":
    st.title("🛒 Punto de Venta")
    st.info("Selecciona un cliente y productos para generar venta (Próximamente).")
