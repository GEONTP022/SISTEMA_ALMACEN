import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from supabase import create_client
from streamlit_option_menu import option_menu
from datetime import datetime

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="VillaFix System PRO",
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
    st.error(f"⚠️ Error crítico de conexión: {e}")
    st.stop()

# --- 3. ESTILOS CSS (MODO OFICINA) ---
st.markdown("""
<style>
    /* Fondo y Textos */
    .stApp { background-color: #f4f6f9; }
    h1, h2, h3, h4, h5, p, div, span, label, li { color: #212529 !important; }
    
    /* Inputs Blancos y Limpios */
    .stTextInput>div>div>input { 
        background-color: #ffffff !important; 
        color: #212529 !important; 
        border: 1px solid #ced4da;
        border-radius: 6px;
    }
    .stSelectbox>div>div>div {
        background-color: #ffffff !important;
        color: #212529 !important;
    }
    
    /* Tarjetas Dashboard */
    .dashboard-card {
        padding: 20px; border-radius: 12px; color: white !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-bottom: 15px;
        transition: transform 0.2s;
    }
    .dashboard-card:hover { transform: translateY(-5px); }
    
    .card-green { background-color: #28a745; background-image: linear-gradient(135deg, #28a745 0%, #20c997 100%); }
    .card-orange { background-color: #fd7e14; background-image: linear-gradient(135deg, #fd7e14 0%, #f39c12 100%); }
    .card-blue { background-color: #17a2b8; background-image: linear-gradient(135deg, #17a2b8 0%, #3498db 100%); }
    .card-yellow { background-color: #ffc107; background-image: linear-gradient(135deg, #ffc107 0%, #f1c40f 100%); }
    .card-yellow h3, .card-yellow p { color: #333 !important; } 

    /* Botones */
    .stButton>button { border-radius: 6px; font-weight: 600; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES INTELIGENTES ---

def consultar_dni_reniec(dni):
    """Búsqueda Híbrida: V2 (Token) -> V1 (Gratis)"""
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd" # Tu Token

    fuentes = [
        {"url": f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}", "headers": {'Authorization': f'Bearer {token}'}, "tipo": "v2"},
        {"url": f"https://api.apis.net.pe/v1/dni?numero={dni}", "headers": {}, "tipo": "v1"}
    ]

    for fuente in fuentes:
        try:
            response = requests.get(fuente["url"], headers=fuente["headers"], timeout=4)
            if response.status_code == 200:
                data = response.json()
                if fuente["tipo"] == "v2":
                    n = data.get("nombres", "")
                    p = data.get("apellidoPaterno", "")
                    m = data.get("apellidoMaterno", "")
                    return f"{n} {p} {m}".strip()
                elif fuente["tipo"] == "v1":
                    return data.get("nombre", "")
        except: continue
    return None

def subir_imagen(archivo):
    """Sube imagen a Supabase"""
    try:
        filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name}"
        bucket = "fotos_productos"
        file_bytes = archivo.getvalue()
        supabase.storage.from_(bucket).upload(filename, file_bytes, {"content-type": archivo.type})
        return supabase.storage.from_(bucket).get_public_url(filename)
    except: return None

# --- 5. MENÚ LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: white !important;'>VillaFix 🔧</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
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
    st.markdown("---")
    st.info("🟢 Sistema Online")

# --- 6. LÓGICA DE PÁGINAS ---

# === PÁGINA: DASHBOARD ===
if selected == "Dashboard":
    st.markdown("### 📊 Panel de Control")
    try:
        count_prod = supabase.table("productos").select("id", count="exact").execute().count
        count_cli = supabase.table("clientes").select("id", count="exact").execute().count
    except: count_prod = 0; count_cli = 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="dashboard-card card-green"><h3>👥 {count_cli}</h3><p>Clientes</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="dashboard-card card-orange"><h3>📦 {count_prod}</h3><p>Productos</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="dashboard-card card-blue"><h3>🛒 0</h3><p>Ventas Hoy</p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="dashboard-card card-yellow"><h3>💰 S/ 0</h3><p>Caja Chica</p></div>', unsafe_allow_html=True)

    st.write("")
    col_g1, col_g2 = st.columns([2, 1])
    try:
        df = pd.DataFrame(supabase.table("productos").select("categoria, stock").execute().data)
        if not df.empty:
            with col_g1:
                st.subheader("📦 Stock por Categoría")
                st.plotly_chart(px.bar(df, x='categoria', y='stock', color='categoria'), use_container_width=True)
            with col_g2:
                st.subheader("🍩 Distribución")
                st.plotly_chart(px.pie(df, names='categoria', values='stock', hole=0.5), use_container_width=True)
    except: st.info("Sin datos para gráficos.")

# === PÁGINA: CLIENTES (CORREGIDA Y MEJORADA) ===
elif selected == "Clientes":
    st.markdown("### 👥 Gestión de Clientes")
    
    t1, t2 = st.tabs(["🆕 Nuevo Cliente", "📋 Directorio"])
    
    with t1:
        st.info("💡 Ingresa el DNI. Si ya existe, carga los datos. Si no, busca en RENIEC.")
        
        # Inicializar variables de sesión
        if 'nombre_cliente' not in st.session_state: st.session_state.nombre_cliente = ""
        if 'dni_cliente' not in st.session_state: st.session_state.dni_cliente = ""

        # Layout de búsqueda
        c_dni, c_btn, c_cls = st.columns([3, 1, 0.5])
        
        # INPUT DNI SIN LIMITE DURO (Para poder editar fácil)
        dni_input = c_dni.text_input("DNI", value=st.session_state.dni_cliente, placeholder="Ingresa 8 dígitos")
        
        # Detectar cambio manual para resetear nombre
        if dni_input != st.session_state.dni_cliente:
            st.session_state.nombre_cliente = ""
            st.session_state.dni_cliente = dni_input

        # Botones
        buscar = c_btn.button("🔍 Buscar", use_container_width=True)
        limpiar = c_cls.button("🗑️", help("Limpiar"))

        if limpiar:
            st.session_state.dni_cliente = ""
            st.session_state.nombre_cliente = ""
            st.rerun()

        # LÓGICA DE BÚSQUEDA
        if (buscar or (dni_input and len(dni_input)==8)) and st.session_state.nombre_cliente == "":
            if len(dni_input) == 8:
                # 1. Buscar en BD Local
                res_db = supabase.table("clientes").select("*").eq("dni", dni_input).execute()
                if res_db.data:
                    datos = res_db.data[0]
                    st.session_state.nombre_cliente = datos["nombre"]
                    st.toast(f"✅ Cliente frecuente: {datos['nombre']}", icon="🏠")
                else:
                    # 2. Buscar en API RENIEC
                    with st.spinner("Conectando con RENIEC..."):
                        nom_api = consultar_dni_reniec(dni_input)
                        if nom_api:
                            st.session_state.nombre_cliente = nom_api
                            st.toast("✨ Datos obtenidos de RENIEC", icon="📡")
                        else:
                            st.warning("⚠️ DNI no encontrado. Ingresa el nombre manual.")
            else:
                if buscar: st.warning("El DNI debe tener 8 dígitos.")

        st.markdown("---")

        # FORMULARIO DE REGISTRO
        with st.form("form_cliente"):
            # Nombre Obligatorio marcado con *
            nombre = st.text_input("Nombre Completo *", value=st.session_state.nombre_cliente)
            
            c_tel, c_dir = st.columns(2)
            telefono = c_tel.text_input("Teléfono / Celular")
            direccion = c_dir.text_input("Dirección")
            email = st.text_input("Email (Opcional)")
            
            guardar = st.form_submit_button("💾 Guardar Cliente", use_container_width=True)
            
            if guardar:
                # VALIDACIONES ESTRICTAS
                if not dni_input or len(dni_input) != 8:
                    st.error("❌ El DNI debe tener 8 dígitos exactos.")
                elif not nombre.strip():
                    st.error("❌ El campo NOMBRE es OBLIGATORIO.")
                else:
                    try:
                        supabase.table("clientes").insert({
                            "dni": dni_input, 
                            "nombre": nombre.strip().upper(), # Guardar en MAYUSCULAS
                            "telefono": telefono, 
                            "direccion": direccion, 
                            "email": email
                        }).execute()
                        st.success(f"✅ Cliente {nombre} registrado!")
                        # Limpiar formulario
                        st.session_state.dni_cliente = ""
                        st.session_state.nombre_cliente = ""
                        st.rerun()
                    except Exception as e:
                        if "duplicate key" in str(e):
                            st.error("❌ Ese DNI ya está registrado.")
                        else:
                            st.error(f"Error: {e}")

    with t2:
        try:
            df = pd.DataFrame(supabase.table("clientes").select("*").order("created_at", desc=True).execute().data)
            if not df.empty:
                st.dataframe(df[["dni", "nombre", "telefono"]], use_container_width=True, hide_index=True)
            else: st.info("No hay clientes.")

# === PÁGINA: INVENTARIO ===
elif selected == "Inventario":
    st.markdown("### 📦 Inventario")
    t_ver, t_add = st.tabs(["👁️ Ver Catálogo", "➕ Agregar Producto"])
    
    with t_ver:
        filtro = st.text_input("🔍 Buscar producto...", placeholder="Nombre, Marca o Código")
        query = supabase.table("productos").select("*").order("created_at", desc=True)
        data = query.execute().data
        df = pd.DataFrame(data)
        
        if not df.empty:
            if filtro:
                df = df[df['nombre'].str.contains(filtro, case=False, na=False) | df['marca'].str.contains(filtro, case=False, na=False)]
            
            cols = st.columns(4)
            for i, row in df.iterrows():
                with cols[i % 4]:
                    with st.container(border=True):
                        if row['imagen_url']: st.image(row['imagen_url'], use_container_width=True)
                        else: st.markdown("🖼️ *Sin imagen*")
                        st.markdown(f"**{row['nombre']}**")
                        st.caption(f"{row.get('marca','Genérico')} | {row['categoria']}")
                        st.markdown(f"#### S/ {row['precio']}")
                        if row['stock'] <= 5: st.caption(f"⚠️ Stock bajo: {row['stock']}")
                        else: st.caption(f"✅ Stock: {row['stock']}")
        else: st.info("Inventario vacío.")

    with t_add:
        st.markdown("#### Nuevo Artículo")
        with st.form("add_prod", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nombre *")
            mar = c1.text_input("Marca")
            cat = c1.selectbox("Categoría", ["Repuestos", "Pantallas", "Baterías", "Accesorios", "Servicios"])
            pre = c2.number_input("Precio Venta (S/)", min_value=0.0)
            stk = c2.number_input("Stock Inicial", min_value=1)
            foto = st.file_uploader("Foto del Producto")
            
            if st.form_submit_button("💾 Guardar", use_container_width=True):
                if nom:
                    url = subir_imagen(foto) if foto else None
                    supabase.table("productos").insert({
                        "nombre": nom.strip().upper(), "marca": mar, "categoria": cat, 
                        "precio": pre, "stock": stk, "imagen_url": url
                    }).execute()
                    st.success(f"Producto {nom} guardado!")
                else: st.warning("Nombre obligatorio")

# === PÁGINA: VENTAS ===
elif selected == "Ventas":
    st.title("🛒 Punto de Venta")
    st.info("Próxima actualización: Carrito de compras.")
