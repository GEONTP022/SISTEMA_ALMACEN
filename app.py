import streamlit as st
from supabase import create_client, Client

# 1. Configuración de la interfaz
st.set_page_config(page_title="VillaFix POS", layout="wide")

# 2. Conexión (Usa tus credenciales de Supabase)
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 3. Inicializar el carrito en la sesión
if "carrito" not in st.session_state:
    st.session_state.carrito = []

# --- Lógica de Interfaz ---

st.title("📱 Sistema de Ventas VillaFix")

col_menu, col_carrito = st.columns([2, 1])

with col_menu:
    st.subheader("Catálogo de Repuestos/Servicios")
    
    # Consultar productos de Supabase
    productos = supabase.table("productos").select("*").execute()
    
    # Crear un grid de productos
    for p in productos.data:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.write(f"**{p['nombre']}**")
            c2.write(f"${p['precio']}")
            if c3.button("Añadir", key=p['id']):
                st.session_state.carrito.append(p)
                st.toast(f"{p['nombre']} añadido")

with col_carrito:
    st.subheader("🛒 Ticket de Venta")
    
    total = 0
    for idx, item in enumerate(st.session_state.carrito):
        st.write(f"{item['nombre']} - ${item['precio']}")
        total += float(item['precio'])
    
    st.divider()
    st.markdown(f"### Total: **${total:.2f}**")
    
    if st.button("Finalizar Venta", type="primary", use_container_width=True):
        # Aquí insertaremos la venta en Supabase después
        if total > 0:
            st.success("¡Venta procesada!")
            st.session_state.carrito = [] # Limpiar carrito
        else:
            st.error("El carrito está vacío")
