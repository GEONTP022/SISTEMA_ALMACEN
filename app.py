import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Sistema VillaFix",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIÓN A BASE DE DATOS ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except:
    st.warning("⚠️ Configura tus secretos en Streamlit Cloud para conectar la BD.")
    st.stop()

# --- 3. CSS "TEMA BUSINESS" (Arregla el problema de las letras) ---
# Esto fuerza el estilo limpio tipo Zoho/AdminLTE de tus fotos
st.markdown("""
<style>
    /* Forzar modo claro en textos */
    .stApp {
        background-color: #f4f6f9; /* Fondo gris muy suave (AdminLTE) */
    }
    h1, h2, h3, h4, h5, p, div, span {
        color: #212529 !important; /* Texto casi negro para contraste */
    }
    
    /* Estilo para las Tarjetas del Dashboard (Tus colores: Verde, Naranja, Azul, Amarillo) */
    .dashboard-card {
        padding: 20px;
        border-radius: 10px;
        color: white !important; /* Texto blanco dentro de las tarjetas */
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        text-align: center;
    }
    .card-green { background-color: #28a745; }
    .card-orange { background-color: #fd7e14; }
    .card-blue { background-color: #17a2b8; }
    .card-yellow { background-color: #ffc107; color: #333 !important; } /* Amarillo con texto oscuro */

    /* Estilo de Tarjeta de Producto (Tu imagen 3) */
    .product-card {
        background-color: white;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
        text-align: center;
    }
    .price-tag {
        background-color: #e6f4ea;
        color: #1e7e34 !important;
        padding: 5px 10px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 14px;
    }
    
    /* Eliminar espacios extra arriba */
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- 4. BARRA LATERAL (Menú Profesional) ---
with st.sidebar:
    # Simulación de logo
    st.markdown("<h2 style='text-align: center;'>VillaFix 🔧</h2>", unsafe_allow_html=True)
    
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Catálogo", "Ventas", "Configuración"],
        icons=["speedometer2", "grid-fill", "cart4", "gear"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#343a40"},
            "icon": {"color": "white", "font-size": "18px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#495057", "color": "white"},
            "nav-link-selected": {"background-color": "#007bff"},
        }
    )

# --- 5. LÓGICA DE PÁGINAS ---

if selected == "Dashboard":
    st.markdown("### 📊 Panel de Control")
    
    # 5.1 Tarjetas de Colores (Como tu imagen 1)
    col1, col2, col3, col4 = st.columns(4)
    
    # Datos reales (Consultas rápidas)
    try:
        count_prod = supabase.table("productos").select("id", count="exact").execute().count
        # Simulamos ventas por ahora (luego conectamos tabla ventas)
        ventas_hoy = 350 
        clientes = 12
    except:
        count_prod = 0
        ventas_hoy = 0
        clientes = 0

    # Función para dibujar tarjeta HTML
    def metric_card(color_class, icon, number, label):
        return f"""
        <div class="dashboard-card {color_class}">
            <h3 style="color: inherit !important; margin:0;">{icon} {number}</h3>
            <p style="color: inherit !important; font-size: 14px; margin:0;">{label}</p>
        </div>
        """

    with col1:
        st.markdown(metric_card("card-green", "👤", str(clientes), "Clientes"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("card-orange", "📦", str(count_prod), "Productos"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card("card-blue", "🛒", "7", "Ventas Hoy"), unsafe_allow_html=True)
    with col4:
        st.markdown(metric_card("card-yellow", "💰", f"S/{ventas_hoy}", "Ingresos"), unsafe_allow_html=True)

    # 5.2 Gráficos (Como tu imagen 4)
    st.write("") # Espacio
    c_chart1, c_chart2 = st.columns([2, 1])
    
    with c_chart1:
        st.subheader("Ventas por Categoría")
        # Traer datos reales para el gráfico
        response = supabase.table("productos").select("categoria, stock").execute()
        df_chart = pd.DataFrame(response.data)
        
        if not df_chart.empty:
            fig = px.bar(df_chart, x='categoria', y='stock', color='categoria', template="plotly_white")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos para graficar")

    with c_chart2:
        st.subheader("Estado de Stock")
        if not df_chart.empty:
            fig2 = px.pie(df_chart, names='categoria', values='stock', hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)


elif selected == "Catálogo":
    # 6. VISTA TIPO TARJETAS (Como tu imagen 3)
    st.markdown("### 📱 Catálogo de Productos")
    
    col_search, col_add = st.columns([4, 1])
    with col_search:
        search_term = st.text_input("🔍 Buscar por nombre o código", placeholder="Ej: Pantalla iPhone...")
    with col_add:
        st.write("") # Espacio para alinear
        if st.button("➕ Nuevo Item"):
            st.toast("Abre el formulario de registro")

    # Obtener productos
    query = supabase.table("productos").select("*")
    if search_term:
        query = query.ilike("nombre", f"%{search_term}%")
    
    response = query.execute()
    df = pd.DataFrame(response.data)

    if not df.empty:
        # Layout de Grid (3 columnas)
        cols = st.columns(4)
        
        for index, row in df.iterrows():
            col_idx = index % 4
            with cols[col_idx]:
                # CONTENEDOR TIPO TARJETA
                with st.container(border=True):
                    # Imagen
                    if row['imagen_url']:
                        st.image(row['imagen_url'], use_container_width=True)
                    else:
                        # Imagen por defecto si no hay
                        st.image("https://via.placeholder.com/200x200.png?text=Sin+Foto", use_container_width=True)
                    
                    st.markdown(f"**{row['nombre']}**")
                    st.caption(f"ID: {row.get('id', '---')}")
                    
                    # Precio y Stock
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"<span class='price-tag'>S/ {row['precio']}</span>", unsafe_allow_html=True)
                    with c2:
                        st.write(f"📦 {row['stock']}")
                    
                    # Botón Toggle (Simulado)
                    st.checkbox("Catálogo", value=True, key=f"check_{index}")

    else:
        st.warning("No se encontraron productos. ¡Agrega el primero!")

elif selected == "Ventas":
    st.title("🛒 Punto de Venta")
    st.info("Aquí irá el módulo de facturación (Próximo paso).")

elif selected == "Configuración":
    st.title("⚙️ Ajustes")
    st.write("Configuración de usuarios y empresa.")
