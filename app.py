import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from supabase import create_client
from streamlit_option_menu import option_menu
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="VillaFix System",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIÓN A BASE DE DATOS (SUPABASE) ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"⚠️ Error de conexión: Revisa los Secrets en Streamlit Cloud. Detalle: {e}")
    st.stop()

# --- 3. ESTILOS CSS PROFESIONALES (TEMA BUSINESS) ---
st.markdown("""
<style>
    /* Forzar fondo claro y textos oscuros (Anti-Modo Oscuro) */
    .stApp { background-color: #f4f6f9; }
    h1, h2, h3, h4, h5, p, div, span, label, li { color: #212529 !important; }
    
    /* Inputs y Botones */
    .stTextInput>div>div>input { 
        border-radius: 5px; 
        border: 1px solid #ced4da; 
        color: #212529 !important;
        background-color: #ffffff !important;
    }
    .stSelectbox>div>div>div {
        color: #212529 !important;
        background-color: #ffffff !important;
    }
    
    /* Tarjetas del Dashboard */
    .dashboard-card {
        padding: 20px; 
        border-radius: 10px; 
        color: white !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        text-align: center; 
        margin-bottom: 15px;
    }
    /* Textos dentro de las tarjetas forzados a blanco */
    .dashboard-card h3, .dashboard-card p { color: white !important; }
    
    .card-green { background-color: #28a745; }
    .card-orange { background-color: #fd7e14; }
    .card-blue { background-color: #17a2b8; }
    .card-yellow { background-color: #ffc107; }
    .card-yellow h3, .card-yellow p { color: #333 !important; } /* Excepción para amarillo */

    /* Tarjetas de Productos */
    .product-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #dee2e6;
        text-align: center;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES DEL SISTEMA ---

def consultar_dni_reniec(dni):
    """Consulta DNI usando tu Token Profesional"""
    # TU TOKEN PERSONAL (El que me pasaste)
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd"
    
    # URL de la API v2
    url = f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}"
    
    # Cabeceras de seguridad
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            # Juntar nombres y apellidos
            nombres = data.get("nombres", "")
            paterno = data.get("apellidoPaterno", "")
            materno = data.get("apellidoMaterno", "")
            
            nombre_completo = f"{nombres} {paterno} {materno}"
            return nombre_completo.strip()
        else:
            return None
    except Exception as e:
        st.error(f"Error de conexión con RENIEC: {e}")
        return None

def subir_imagen(archivo):
    """Sube imagen al Bucket 'fotos_productos' de Supabase"""
    try:
        # Nombre único con fecha y hora para no sobreescribir
        filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name}"
        bucket = "fotos_productos"
        
        file_bytes = archivo.getvalue()
        supabase.storage.from_(bucket).upload(filename, file_bytes, {"content-type": archivo.type})
        
        # Obtener URL pública
        return supabase.storage.from_(bucket).get_public_url(filename)
    except Exception as e:
        st.warning(f"Error subiendo imagen (Verifica que el Bucket sea público): {e}")
        return None

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
    st.caption("© 2026 VillaFix System")

# --- 6. LÓGICA DE PÁGINAS ---

# === PÁGINA: DASHBOARD ===
if selected == "Dashboard":
    st.markdown("### 📊 Panel de Control")
    
    try:
        # Contadores rápidos (Consultas optimizadas)
        prod_count = supabase.table("productos").select("id", count="exact").execute().count
        client_count = supabase.table("clientes").select("id", count="exact").execute().count
    except:
        prod_count = 0
        client_count = 0

    # Tarjetas de colores
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="dashboard-card card-green"><h3>👥 {client_count}</h3><p>Clientes Totales</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="dashboard-card card-orange"><h3>📦 {prod_count}</h3><p>Productos en Stock</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="dashboard-card card-blue"><h3>🛒 0</h3><p>Ventas del Mes</p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="dashboard-card card-yellow"><h3>💰 S/ 0.00</h3><p>Caja Chica</p></div>', unsafe_allow_html=True)

    # Gráficos
    st.write("")
    col_g1, col_g2 = st.columns([2, 1])
    
    try:
        response = supabase.table("productos").select("categoria, stock").execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            with col_g1:
                st.subheader("Stock por Categoría")
                fig = px.bar(df, x='categoria', y='stock', color='categoria', template="plotly_white")
                fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
            with col_g2:
                st.subheader("Distribución")
                fig2 = px.pie(df, names='categoria', values='stock', hole=0.5)
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("ℹ️ Registra productos para ver las estadísticas.")
    except:
        st.warning("No se pudieron cargar los gráficos.")


# === PÁGINA: CLIENTES ===
elif selected == "Clientes":
    st.markdown("### 👥 Gestión de Clientes")
    
    tab1, tab2 = st.tabs(["🆕 Nuevo Cliente", "📋 Directorio"])
    
    # PESTAÑA 1: REGISTRAR
    with tab1:
        st.info("💡 Escribe el DNI y presiona ENTER o Buscar para autocompletar.")
        
        # Estado para el nombre
        if 'nombre_cliente' not in st.session_state: st.session_state.nombre_cliente = ""
        
        col_dni, col_btn = st.columns([3, 1])
        with col_dni:
            dni_input = st.text_input("DNI (8 dígitos)", max_chars=8, placeholder="Ej: 72345678")
        with col_btn:
            st.write("") # Espacio para alinear
            st.write("")
            btn_buscar = st.button("🔍 Buscar RENIEC", type="primary", use_container_width=True)
            
        if btn_buscar and dni_input:
            if len(dni_input) == 8:
                with st.spinner("Conectando con RENIEC..."):
                    nombre_encontrado = consultar_dni_reniec(dni_input)
                    if nombre_encontrado:
                        st.session_state.nombre_cliente = nombre_encontrado
                        st.success("✅ ¡Datos encontrados!")
                    else:
                        st.error("❌ DNI no encontrado o error en la API.")
            else:
                st.warning("El DNI debe tener 8 dígitos.")

        st.markdown("---")
        with st.form("form_cliente"):
            nombre = st.text_input("Nombre Completo", value=st.session_state.nombre_cliente)
            
            c_tel, c_email = st.columns(2)
            telefono = c_tel.text_input("Teléfono / WhatsApp")
            email = c_email.text_input("Correo Electrónico (Opcional)")
            
            direccion = st.text_input("Dirección")
            
            if st.form_submit_button("💾 Guardar Cliente", use_container_width=True):
                if nombre and dni_input:
                    datos = {
                        "dni": dni_input, 
                        "nombre": nombre, 
                        "telefono": telefono, 
                        "email": email, 
                        "direccion": direccion
                    }
                    try:
                        supabase.table("clientes").insert(datos).execute()
                        st.success(f"Cliente {nombre} registrado correctamente.")
                        st.session_state.nombre_cliente = "" # Limpiar
                    except Exception as e:
                        st.error(f"Error al guardar (¿DNI duplicado?): {e}")
                else:
                    st.warning("El DNI y Nombre son obligatorios.")

    # PESTAÑA 2: VER CLIENTES
    with tab2:
        try:
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
        except:
            st.error("Error al cargar la tabla de clientes.")


# === PÁGINA: INVENTARIO ===
elif selected == "Inventario":
    st.markdown("### 📦 Inventario & Productos")
    
    t_ver, t_add = st.tabs(["👁️ Ver Catálogo", "➕ Agregar Producto"])
    
    # PESTAÑA 1: CATÁLOGO VISUAL
    with t_ver:
        col_search, _ = st.columns([1, 1])
        filtro = col_search.text_input("🔍 Buscar por nombre o marca...", placeholder="Ej: Pantalla iPhone")
        
        # Consulta base
        query = supabase.table("productos").select("*").order("created_at", desc=True)
        
        if filtro:
            # Filtro simple (ajustar si se necesita más complejidad)
            # Nota: ilike a veces requiere configuración en Supabase, usaremos lógica Python si falla
            pass 
        
        response = query.execute()
        df_prods = pd.DataFrame(response.data)
        
        if not df_prods.empty:
            # Filtrado en Python para asegurar que funcione rápido
            if filtro:
                df_prods = df_prods[
                    df_prods['nombre'].str.contains(filtro, case=False, na=False) | 
                    df_prods['marca'].str.contains(filtro, case=False, na=False)
                ]
            
            # Grid de 4 columnas
            cols = st.columns(4)
            for i, row in df_prods.iterrows():
                with cols[i % 4]:
                    with st.container(border=True):
                        # Imagen
                        if row['imagen_url']:
                            st.image(row['imagen_url'], use_container_width=True)
                        else:
                            st.markdown("🖼️ *Sin imagen*")
                        
                        # Datos
                        st.markdown(f"**{row['nombre']}**")
                        st.caption(f"{row.get('marca', 'Genérico')} | {row['categoria']}")
                        st.markdown(f"#### S/ {row['precio']}")
                        
                        # Stock con color
                        if row['stock'] < 3:
                            st.markdown(f":red[⚠️ Stock Bajo: {row['stock']}]")
                        else:
                            st.markdown(f":green[Stock: {row['stock']}]")
        else:
            st.info("No hay productos registrados.")

    # PESTAÑA 2: AGREGAR PRODUCTO
    with t_add:
        st.markdown("#### Nuevo Artículo")
        with st.form("add_prod", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            
            with col_a:
                nom = st.text_input("Nombre del Producto *")
                mar = st.text_input("Marca / Fabricante")
                cat = st.selectbox("Categoría", ["Repuestos", "Pantallas", "Baterías", "Accesorios", "Servicios"])
            
            with col_b:
                pre = st.number_input("Precio Venta (S/)", min_value=0.0, step=0.5)
                stk = st.number_input("Stock Inicial", min_value=1, step=1)
                foto = st.file_uploader("Foto del Producto", type=['png', 'jpg', 'jpeg'])
            
            st.markdown("---")
            if st.form_submit_button("💾 Guardar en Inventario", use_container_width=True):
                if nom:
                    with st.spinner("Procesando..."):
                        url_img = None
                        if foto:
                            url_img = subir_imagen(foto)
                        
                        datos_prod = {
                            "nombre": nom, 
                            "marca": mar, 
                            "categoria": cat, 
                            "precio": pre, 
                            "stock": stk, 
                            "imagen_url": url_img
                        }
                        try:
                            supabase.table("productos").insert(datos_prod).execute()
                            st.success(f"✅ ¡{nom} agregado correctamente!")
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
                else:
                    st.warning("El nombre es obligatorio.")


# === PÁGINA: VENTAS (Próximamente) ===
elif selected == "Ventas":
    st.title("🛒 Punto de Venta")
    st.info("🚧 Módulo de Facturación en construcción...")
    st.markdown("""
    Aquí podrás:
    1. Seleccionar un Cliente (Buscador DNI).
    2. Agregar Productos al carrito.
    3. Generar el Total y descontar Stock automáticamente.
    """)
