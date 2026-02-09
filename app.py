import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from supabase import create_client
from streamlit_option_menu import option_menu
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="VillaFix System",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIÓN A BASE DE DATOS ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"⚠️ Error de conexión: Revisa los Secrets en Streamlit Cloud. Detalle: {e}")
    st.stop()

# --- 3. ESTILOS CSS (TEMA BUSINESS) ---
st.markdown("""
<style>
    /* Forzar fondo claro */
    .stApp { background-color: #f4f6f9; }
    h1, h2, h3, h4, h5, p, div, span, label, li { color: #212529 !important; }
    
    /* Inputs Blancos (Para que se note lo que escribes) */
    .stTextInput>div>div>input { 
        background-color: #ffffff !important; 
        color: #212529 !important; 
        border: 1px solid #ced4da;
    }
    
    /* Tarjetas del Dashboard */
    .dashboard-card {
        padding: 20px; border-radius: 10px; color: white !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-bottom: 15px;
    }
    .card-green { background-color: #28a745; }
    .card-orange { background-color: #fd7e14; }
    .card-blue { background-color: #17a2b8; }
    .card-yellow { background-color: #ffc107; }
    .card-yellow h3, .card-yellow p { color: #333 !important; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES INTELIGENTES ---

def consultar_dni_reniec(dni):
    """Prueba múltiples direcciones de API hasta que una funcione"""
    # TU TOKEN DE DECOLECTA (Limpiamos espacios por si acaso)
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd".strip()
    
    # Lista de direcciones posibles (Decolecta y ApisNet)
    urls_posibles = [
        f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}",
        f"https://api.decolecta.com/v1/reniec/dni?numero={dni}",
        f"https://api.apis.net.pe/v1/dni?numero={dni}"
    ]
    
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    
    # Probamos las direcciones una por una
    for url in urls_posibles:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                # Unir nombres según el formato que devuelva la API
                nombres = data.get("nombres", "")
                paterno = data.get("apellidoPaterno", "")
                materno = data.get("apellidoMaterno", "")
                full_name = f"{nombres} {paterno} {materno}".strip()
                
                # Si viene todo junto en "nombre" (formato antiguo)
                if not full_name and "nombre" in data:
                    full_name = data["nombre"]
                    
                return full_name
                
            elif response.status_code == 401:
                # Si dice no autorizado, probamos la siguiente URL
                continue 
                
        except:
            continue

    # Si llegamos aquí, ninguna funcionó
    st.error("❌ No se pudo conectar. Verifica si tu Token es válido o regeneralo en Decolecta.")
    return None

def subir_imagen(archivo):
    """Sube imagen a Supabase"""
    try:
        filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name}"
        bucket = "fotos_productos"
        file_bytes = archivo.getvalue()
        supabase.storage.from_(bucket).upload(filename, file_bytes, {"content-type": archivo.type})
        return supabase.storage.from_(bucket).get_public_url(filename)
    except:
        return None

# --- 5. MENÚ LATERAL ---
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
            "nav-link-selected": {"background-color": "#2563EB"},
        }
    )

# --- 6. PÁGINAS ---

# === DASHBOARD ===
if selected == "Dashboard":
    st.markdown("### 📊 Panel de Control")
    
    try:
        # Contadores Reales
        prod_count = supabase.table("productos").select("id", count="exact").execute().count
        client_count = supabase.table("clientes").select("id", count="exact").execute().count
    except:
        prod_count = 0; client_count = 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="dashboard-card card-green"><h3>👥 {client_count}</h3><p>Clientes</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="dashboard-card card-orange"><h3>📦 {prod_count}</h3><p>Productos</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="dashboard-card card-blue"><h3>🛒 0</h3><p>Ventas</p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="dashboard-card card-yellow"><h3>💰 S/ 0</h3><p>Caja</p></div>', unsafe_allow_html=True)

    # Gráficos
    st.write("")
    col_g1, col_g2 = st.columns([2, 1])
    try:
        df = pd.DataFrame(supabase.table("productos").select("categoria, stock").execute().data)
        if not df.empty:
            with col_g1:
                st.subheader("Stock por Categoría")
                st.plotly_chart(px.bar(df, x='categoria', y='stock', color='categoria'), use_container_width=True)
            with col_g2:
                st.subheader("Distribución")
                st.plotly_chart(px.pie(df, names='categoria', values='stock', hole=0.5), use_container_width=True)
    except:
        st.info("Agrega productos para ver gráficos.")

# === CLIENTES (DNI INTELIGENTE) ===
elif selected == "Clientes":
    st.markdown("### 👥 Gestión de Clientes")
    
    tab1, tab2 = st.tabs(["🆕 Nuevo Cliente", "📋 Directorio"])
    
    with tab1:
        st.info("💡 Escribe el DNI y presiona ENTER o Buscar.")
        
        if 'nombre_cliente' not in st.session_state: st.session_state.nombre_cliente = ""
        
        c_dni, c_btn = st.columns([3, 1])
        dni_input = c_dni.text_input("DNI", max_chars=8, placeholder="Ej: 72345678")
        btn_buscar = c_btn.button("🔍 Buscar RENIEC", type="primary", use_container_width=True)
        
        # Lógica de búsqueda
        if (btn_buscar or dni_input) and len(dni_input) == 8:
            # Evitar buscar si ya tenemos el nombre para no gastar API
            if st.session_state.nombre_cliente == "":
                with st.spinner("Conectando con Decolecta..."):
                    nombre = consultar_dni_reniec(dni_input)
                    if nombre:
                        st.session_state.nombre_cliente = nombre
                        st.toast("✅ ¡Datos encontrados!", icon="🎉")
                    else:
                        st.toast("⚠️ No se encontró. Ingresa manual.", icon="❌")

        with st.form("form_cliente"):
            nombre = st.text_input("Nombre Completo", value=st.session_state.nombre_cliente)
            telefono = st.text_input("Teléfono")
            direccion = st.text_input("Dirección")
            
            if st.form_submit_button("💾 Guardar Cliente", use_container_width=True):
                if nombre and dni_input:
                    try:
                        supabase.table("clientes").insert({
                            "dni": dni_input, "nombre": nombre, 
                            "telefono": telefono, "direccion": direccion
                        }).execute()
                        st.success(f"Cliente {nombre} registrado!")
                        st.session_state.nombre_cliente = "" # Limpiar
                    except Exception as e:
                        st.error(f"Error (¿DNI duplicado?): {e}")
                else:
                    st.warning("Falta DNI o Nombre")

    with tab2:
        try:
            df = pd.DataFrame(supabase.table("clientes").select("*").order("created_at", desc=True).execute().data)
            if not df.empty:
                st.dataframe(df[["dni", "nombre", "telefono", "direccion"]], use_container_width=True, hide_index=True)
        except: pass

# === INVENTARIO ===
elif selected == "Inventario":
    st.markdown("### 📦 Inventario")
    t_ver, t_add = st.tabs(["Ver Todo", "Nuevo Producto"])
    
    with t_ver:
        filtro = st.text_input("🔍 Buscar...", placeholder="Nombre o Marca")
        query = supabase.table("productos").select("*")
        if filtro: query = query.ilike("nombre", f"%{filtro}%")
        data = query.execute().data
        
        if data:
            cols = st.columns(4)
            for i, row in enumerate(data):
                with cols[i % 4]:
                    with st.container(border=True):
                        if row['imagen_url']: st.image(row['imagen_url'], use_container_width=True)
                        st.markdown(f"**{row['nombre']}**")
                        st.caption(f"{row.get('marca','')} | Stock: {row['stock']}")
                        st.markdown(f"**S/ {row['precio']}**")
        else:
            st.info("Sin productos.")

    with t_add:
        with st.form("add_prod", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nombre *")
            mar = c1.text_input("Marca")
            cat = c1.selectbox("Categoría", ["Repuestos", "Pantallas", "Accesorios"])
            pre = c2.number_input("Precio", min_value=0.0)
            stk = c2.number_input("Stock", min_value=1)
            foto = st.file_uploader("Foto")
            
            if st.form_submit_button("💾 Guardar", use_container_width=True):
                if nom:
                    url = subir_imagen(foto) if foto else None
                    supabase.table("productos").insert({
                        "nombre": nom, "marca": mar, "categoria": cat, 
                        "precio": pre, "stock": stk, "imagen_url": url
                    }).execute()
                    st.success("Guardado!")

elif selected == "Ventas":
    st.info("Módulo de ventas en construcción...")
