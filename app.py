import streamlit as st
import pandas as pd
from supabase import create_client
import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="VillaFix Pro", layout="wide")

# Conexión a Supabase usando secrets.toml (Local) o Secrets de Streamlit (Nube)
@st.cache_resource
def init_db():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_db()

# --- FUNCIONES AUXILIARES ---
def subir_imagen(archivo):
    """Sube una imagen al Storage de Supabase y devuelve la URL pública"""
    try:
        # Crear un nombre único para el archivo (usando la hora actual)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"img_{timestamp}_{archivo.name}"
        
        # Leer el archivo
        archivo_bytes = archivo.getvalue()
        
        # Subir al bucket 'fotos_productos'
        ruta = f"items/{nombre_archivo}" # carpeta/archivo
        supabase.storage.from_("fotos_productos").upload(
            path=ruta,
            file=archivo_bytes,
            file_options={"content-type": archivo.type}
        )
        
        # Obtener la URL pública para guardarla en la BD
        public_url = supabase.storage.from_("fotos_productos").get_public_url(ruta)
        return public_url
    except Exception as e:
        st.error(f"Error al subir imagen: {e}")
        return None

# --- INTERFAZ ---
st.title("📱 Sistema de Gestión VillaFix")

tabs = st.tabs(["📦 Inventario", "➕ Nuevo Producto", "🛒 Ventas"])

# --- PESTAÑA 1: INVENTARIO VISUAL ---
with tabs[0]:
    st.header("Catálogo de Productos")
    
    # Traer datos
    response = supabase.table("productos").select("*").execute()
    df = pd.DataFrame(response.data)
    
    if not df.empty:
        # Buscador
        busqueda = st.text_input("🔍 Buscar producto...", "")
        if busqueda:
            df = df[df['nombre'].str.contains(busqueda, case=False, na=False)]
        
        # Mostrar como cuadrícula (Más profesional que una tabla simple)
        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        
        for index, row in df.iterrows():
            with cols[index % 3]:
                with st.container(border=True):
                    # Mostrar imagen si existe
                    if row['imagen_url']:
                        st.image(row['imagen_url'], use_container_width=True)
                    else:
                        st.write("📷 Sin imagen")
                        
                    st.subheader(row['nombre'])
                    st.write(f"**Categoría:** {row['categoria']}")
                    st.write(f"**Stock:** {row['stock']} unid.")
                    st.metric("Precio", f"S/ {row['precio']}")
    else:
        st.info("No hay productos registrados.")

# --- PESTAÑA 2: AGREGAR PRODUCTO ---
with tabs[1]:
    st.header("Registrar Nuevo Ítem")
    
    with st.form("form_producto", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        nombre = col_a.text_input("Nombre del Producto")
        categoria = col_b.selectbox("Categoría", ["Celulares", "Baterías", "Pantallas", "Cargadores", "Audífonos"])
        
        col_c, col_d = st.columns(2)
        precio = col_c.number_input("Precio Venta (S/)", min_value=0.0, step=0.5)
        stock = col_d.number_input("Stock Inicial", min_value=1, step=1)
        
        st.markdown("---")
        st.write("🖼️ **Imagen del Producto**")
        
        tipo_img = st.radio("¿Cómo quieres agregar la foto?", ["Subir archivo descargado", "Pegar URL de internet"])
        
        url_final = None
        
        if tipo_img == "Subir archivo descargado":
            archivo = st.file_uploader("Arrastra tu imagen aquí", type=['png', 'jpg', 'jpeg', 'webp'])
        else:
            url_texto = st.text_input("Pega el link de la imagen aquí")
        
        submitted = st.form_submit_button("💾 Guardar Producto")
        
        if submitted:
            # Procesar la imagen
            if tipo_img == "Subir archivo descargado" and archivo:
                with st.spinner("Subiendo imagen a la nube..."):
                    url_final = subir_imagen(archivo)
            elif tipo_img == "Pegar URL de internet":
                url_final = url_texto
                
            # Guardar en Base de Datos
            datos = {
                "nombre": nombre,
                "categoria": categoria,
                "precio": precio,
                "stock": stock,
                "imagen_url": url_final
            }
            
            try:
                supabase.table("productos").insert(datos).execute()
                st.success("✅ Producto agregado correctamente!")
                st.rerun() # Recargar para ver cambios
            except Exception as e:
                st.error(f"Error al guardar en BD: {e}")

# --- PESTAÑA 3: VENTAS (Próximamente) ---
with tabs[2]:
    st.info("Módulo de ventas en construcción...")
