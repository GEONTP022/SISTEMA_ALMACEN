import streamlit as st
from supabase import create_client, Client

# --- CONFIGURACIÓN VISUAL (ESTILO FIGMA) ---
st.set_page_config(page_title="VillaFix POS", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Fondo principal */
    .stApp { background-color: #f8f9fa; }
    
    /* Estilo para las tarjetas de productos */
    .product-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        margin-bottom: 15px;
    }
    
    /* Botones estilo Figma */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN SUPABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- VISTAS (COMPONENTEIZACIÓN) ---

def view_pos():
    st.title("🛒 Punto de Venta")
    col_products, col_cart = st.columns([2, 1])
    
    with col_products:
        st.subheader("Productos")
        # Aquí simulamos el grid del diseño de Figma
        c1, c2 = st.columns(2)
        productos = supabase.table("productos").select("*").execute()
        
        for i, p in enumerate(productos.data):
            target_col = c1 if i % 2 == 0 else c2
            with target_col:
                st.markdown(f"""
                    <div class="product-card">
                        <h4 style='margin:0;'>{p['nombre']}</h4>
                        <p style='color: #666;'>Stock: {p['stock']}</p>
                        <h3 style='color: #2e7d32; margin: 10px 0;'>S/ {p['precio']}</h3>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"Agregar", key=f"btn_{p['id']}"):
                    # Lógica para añadir al carrito
                    pass

    with col_cart:
        st.markdown("<div style='background: white; padding: 20px; border-radius: 15px;'>", unsafe_allow_html=True)
        st.subheader("Resumen de Orden")
        st.write("No hay productos")
        st.divider()
        st.button("Confirmar Venta", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

def view_inventory():
    st.title("📦 Inventario de VillaFix")
    # Tabla interactiva
    productos = supabase.table("productos").select("*").execute()
    st.dataframe(productos.data, use_container_width=True)

# --- NAVEGACIÓN LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9306/9306630.png", width=80) # Logo temporal
    st.title("VillaFix Admin")
    menu = st.radio("MENÚ", ["POS / Ventas", "Inventario", "Clientes", "Reportes"])

# Renderizar la vista seleccionada
if menu == "POS / Ventas":
    view_pos()
elif menu == "Inventario":
    view_inventory()
