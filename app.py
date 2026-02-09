import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from streamlit_option_menu import option_menu
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="VillaFix System", layout="wide", page_icon="🔧")

# --- CONEXIÓN ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except:
    st.error("⚠️ Error de conexión: Revisa los Secrets en Streamlit Cloud.")
    st.stop()

# --- ESTILOS CSS (TEMA BUSINESS) ---
st.markdown("""
<style>
    .stApp { background-color: #f4f6f9; }
    h1, h2, h3, p, div { color: #212529 !important; }
    
    /* Tarjetas del Dashboard */
    .dashboard-card {
        padding: 20px; border-radius: 10px; color: white !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-bottom: 10px;
    }
    .card-green { background-color: #28a745; }
    .card-orange { background-color: #fd7e14; }
    .card-blue { background-color: #17a2b8; }
    .card-yellow { background-color: #ffc107; color: #333 !important; }
    
    /* Input Forms */
    .stTextInput>div>div>input { border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- MENÚ LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: white !important;'>VillaFix 🔧</h2>", unsafe_allow_html=True)
    
    selected = option_menu(
        menu_title=None,
        # AQUI AGREGUÉ "NUEVO PRODUCTO" COMO PEDISTE
        options=["Dashboard", "Nuevo Producto", "Catálogo", "Ventas"], 
        icons=["speedometer2", "plus-circle-fill", "grid-fill", "cart4"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#262b3d"},
            "icon": {"color": "white", "font-size": "18px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "color": "white"},
            "nav-link-selected": {"background-color": "#007bff"},
        }
    )

# --- FUNCIONES AUXILIARES ---
def subir_imagen(archivo):
    """Sube imagen a Supabase Storage y devuelve URL"""
    try:
        filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name}"
        bucket = "fotos_productos" # Asegúrate de haber creado este bucket público en Supabase
        file_bytes = archivo.getvalue()
        supabase.storage.from_(bucket).upload(filename, file_bytes, {"content-type": archivo.type})
        return supabase.storage.from_(bucket).get_public_url(filename)
    except Exception as e:
        st.warning(f"No se pudo subir la imagen (Verifica el Bucket en Supabase): {e}")
        return None

# --- LÓGICA DE PÁGINAS ---

# 1. DASHBOARD (CORREGIDO EL ERROR ROJO)
if selected == "Dashboard":
    st.markdown("### 📊 Panel de Control")
    
    # Consultas seguras
    try:
        # Usamos count='exact', head=True para contar rápido sin traer datos pesados
        prod_count = supabase.table("productos").select("id", count="exact").execute().count
        # Simulamos ventas hasta tener tabla ventas
        ventas_hoy = 7
        ingresos = 350
    except Exception as e:
        prod_count = 0
        ventas_hoy = 0
        ingresos = 0
        st.error(f"Error leyendo base de datos: {e}")

    # Tarjetas
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="dashboard-card card-green"><h3>👥 12</h3><p>Clientes</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="dashboard-card card-orange"><h3>📦 {prod_count}</h3><p>Productos</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="dashboard-card card-blue"><h3>🛒 {ventas_hoy}</h3><p>Ventas Hoy</p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="dashboard-card card-yellow"><h3>💰 S/{ingresos}</h3><p>Ingresos</p></div>', unsafe_allow_html=True)

    # Gráficos
    st.write("")
    col_g1, col_g2 = st.columns([2,1])
    
    # Traer datos para gráficos
    try:
        response = supabase.table("productos").select("categoria, stock").execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            with col_g1:
                st.subheader("Inventario por Categoría")
                fig = px.bar(df, x='categoria', y='stock', color='categoria', template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            with col_g2:
                st.subheader("Distribución")
                fig2 = px.pie(df, names='categoria', values='stock', hole=0.4)
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("ℹ️ Agrega productos para ver los gráficos.")
            
    except:
        st.warning("No se pudo cargar el gráfico (Tabla vacía o error de conexión)")

# 2. NUEVO PRODUCTO (LO QUE PEDISTE)
elif selected == "Nuevo Producto":
    st.markdown("### ✨ Registrar Nuevo Artículo")
    
    with st.container(border=True):
        with st.form("form_nuevo_prod", clear_on_submit=True):
            col_a, col_b = st.columns([1, 1])
            
            with col_a:
                nombre = st.text_input("Nombre del Producto *")
                marca = st.text_input("Marca / Fabricante")
                categoria = st.selectbox("Categoría", ["Repuestos", "Pantallas", "Baterías", "Equipos", "Accesorios"])
            
            with col_b:
                precio = st.number_input("Precio Venta (S/)", min_value=0.0, step=0.5)
                stock = st.number_input("Stock Inicial", min_value=1, step=1)
                archivo_img = st.file_uploader("Foto del Producto", type=['png', 'jpg', 'jpeg'])

            st.markdown("---")
            submitted = st.form_submit_button("💾 Guardar en Inventario", use_container_width=True)
            
            if submitted:
                if nombre:
                    url_final = None
                    if archivo_img:
                        with st.spinner("Subiendo foto..."):
                            url_final = subir_imagen(archivo_img)
                    
                    datos = {
                        "nombre": nombre,
                        "marca": marca,
                        "categoria": categoria,
                        "precio": precio,
                        "stock": stock,
                        "imagen_url": url_final
                    }
                    
                    try:
                        supabase.table("productos").insert(datos).execute()
                        st.success(f"✅ ¡{nombre} agregado exitosamente!")
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                else:
                    st.warning("⚠️ El nombre es obligatorio.")

# 3. CATÁLOGO VISUAL
elif selected == "Catálogo":
    st.markdown("### 📱 Inventario Actual")
    
    response = supabase.table("productos").select("*").execute()
    df = pd.DataFrame(response.data)
    
    if not df.empty:
        # Buscador
        filtro = st.text_input("🔍 Buscar...", placeholder="Escribe nombre o marca")
        if filtro:
            df = df[df['nombre'].str.contains(filtro, case=False) | df['marca'].str.contains(filtro, case=False, na=False)]
        
        # Grid de productos
        cols = st.columns(4)
        for i, row in df.iterrows():
            with cols[i % 4]:
                with st.container(border=True):
                    if row['imagen_url']:
                        st.image(row['imagen_url'], use_container_width=True)
                    else:
                        st.markdown("📷 *Sin Foto*")
                    
                    st.markdown(f"**{row['nombre']}**")
                    st.caption(f"{row['marca']} | {row['categoria']}")
                    st.markdown(f"**S/ {row['precio']}**")
                    st.progress(min(row['stock']/20, 1.0), text=f"Stock: {row['stock']}")
    else:
        st.info("El inventario está vacío. Ve a 'Nuevo Producto' para empezar.")

elif selected == "Ventas":
    st.title("🛒 Punto de Venta (Próximamente)")
