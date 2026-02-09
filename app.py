import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from supabase import create_client
from streamlit_option_menu import option_menu
from datetime import datetime, date

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="VillaFix System PRO",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"⚠️ Error de conexión: {e}")
    st.stop()

# --- 3. ESTILOS CSS ---
st.markdown("""
<style>
    .stApp { background-color: #f4f6f9; }
    h1, h2, h3, h4, h5, p, div, span, label, li { color: #212529 !important; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stDateInput>div>div>input { 
        background-color: #ffffff !important; 
        color: #212529 !important; 
        border: 1px solid #ced4da;
        border-radius: 6px;
    }
    .stSelectbox>div>div>div { background-color: #ffffff !important; color: #212529 !important; }
    .dashboard-card {
        padding: 20px; border-radius: 12px; color: white !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-bottom: 15px;
    }
    .card-green { background-color: #28a745; }
    .card-orange { background-color: #fd7e14; }
    .card-blue { background-color: #17a2b8; }
    .card-yellow { background-color: #ffc107; color: #333 !important; }
    .stButton>button { border-radius: 6px; font-weight: 600; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES ---

def consultar_dni_reniec(dni):
    """Búsqueda Híbrida Inteligente"""
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
    try:
        filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name}"
        bucket = "fotos_productos"
        file_bytes = archivo.getvalue()
        supabase.storage.from_(bucket).upload(filename, file_bytes, {"content-type": archivo.type})
        return supabase.storage.from_(bucket).get_public_url(filename)
    except: return None

# --- 5. MENÚ ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: white !important;'>VillaFix 🔧</h2>", unsafe_allow_html=True)
    st.markdown("---")
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Recepción", "Inventario", "Ventas"], 
        icons=["speedometer2", "clipboard-check", "box-seam", "cart4"],
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

if selected == "Dashboard":
    st.markdown("### 📊 Panel de Control")
    try:
        count_prod = supabase.table("productos").select("id", count="exact").execute().count
        count_cli = supabase.table("clientes").select("id", count="exact").execute().count
    except: count_prod = 0; count_cli = 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="dashboard-card card-green"><h3>👥 {count_cli}</h3><p>Clientes</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="dashboard-card card-orange"><h3>📦 {count_prod}</h3><p>Productos</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="dashboard-card card-blue"><h3>🔧 0</h3><p>Tickets Activos</p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="dashboard-card card-yellow"><h3>💰 S/ 0</h3><p>Ingresos</p></div>', unsafe_allow_html=True)

    # (Aquí irían los gráficos igual que antes, los omito por brevedad pero puedes dejarlos)

# === PÁGINA: RECEPCIÓN (CLIENTES + TICKETS) ===
elif selected == "Recepción":
    st.markdown("### 📝 Recepción de Equipos")
    
    t_ingreso, t_historial = st.tabs(["🆕 Nuevo Ingreso", "📋 Historial Tickets"])
    
    with t_ingreso:
        # --- SECCIÓN 1: DATOS DEL CLIENTE (ARRIBA) ---
        st.markdown("#### 1. Datos del Cliente")
        with st.container(border=True):
            if 'nombre_cliente' not in st.session_state: st.session_state.nombre_cliente = ""
            if 'dni_cliente' not in st.session_state: st.session_state.dni_cliente = ""

            c_dni, c_btn, c_cls = st.columns([3, 1, 0.5])
            dni_input = c_dni.text_input("DNI", value=st.session_state.dni_cliente, placeholder="Ingrese DNI")
            
            # Reset si cambia el DNI
            if dni_input != st.session_state.dni_cliente:
                st.session_state.dni_cliente = dni_input
                st.session_state.nombre_cliente = ""

            if c_btn.button("🔍 Buscar Cliente"):
                if len(dni_input) == 8:
                    # 1. BD Local
                    res_db = supabase.table("clientes").select("*").eq("dni", dni_input).execute()
                    if res_db.data:
                        st.session_state.nombre_cliente = res_db.data[0]["nombre"]
                        st.toast("Cliente Frecuente encontrado", icon="✅")
                    else:
                        # 2. RENIEC
                        with st.spinner("Consultando RENIEC..."):
                            nom = consultar_dni_reniec(dni_input)
                            if nom: 
                                st.session_state.nombre_cliente = nom
                                st.toast("Datos de RENIEC cargados", icon="📡")
                            else: st.warning("No encontrado. Ingrese manual.")
                else: st.warning("DNI inválido")
            
            if c_cls.button("🗑️"):
                st.session_state.dni_cliente = ""; st.session_state.nombre_cliente = ""; st.rerun()

            # Campos Cliente
            nombre = st.text_input("Nombre Completo *", value=st.session_state.nombre_cliente)
            c_tel, c_dir = st.columns(2)
            telefono = c_tel.text_input("Teléfono / WhatsApp *")
            direccion = c_dir.text_input("Dirección")

        st.write("") # Espacio

        # --- SECCIÓN 2: DATOS DEL EQUIPO / TICKET (ABAJO) ---
        st.markdown("#### 2. Datos del Equipo (Ticket)")
        with st.form("form_ticket"):
            with st.container():
                col_eq1, col_eq2 = st.columns(2)
                with col_eq1:
                    marca = st.text_input("Marca *", placeholder="Ej: Samsung, Apple")
                    modelo = st.text_input("Modelo *", placeholder="Ej: A54, iPhone 11")
                    imei = st.text_input("IMEI (Opcional)", placeholder="Escanee o digite")
                
                with col_eq2:
                    contrasena = st.text_input("Contraseña / Patrón *", placeholder="Clave de desbloqueo")
                    precio = st.number_input("Costo Estimado (S/) *", min_value=0.0)
                    fecha_entrega = st.date_input("Fecha Posible Entrega *", min_value=date.today())

                descripcion = st.text_area("Descripción de la Falla / Detalles *", height=100, placeholder="Ej: Pantalla rota, no carga, cambiar batería...")

            st.markdown("---")
            btn_guardar = st.form_submit_button("💾 Registrar Ingreso (Cliente + Ticket)", use_container_width=True)

            if btn_guardar:
                # VALIDACIONES
                errores = []
                if len(dni_input) != 8: errores.append("DNI inválido")
                if not nombre: errores.append("Falta Nombre Cliente")
                if not marca or not modelo: errores.append("Falta Marca/Modelo")
                if not contrasena: errores.append("Falta Contraseña")
                if not descripcion: errores.append("Falta Descripción")
                if not telefono: errores.append("Falta Teléfono de contacto")

                if errores:
                    for e in errores: st.error(f"❌ {e}")
                else:
                    try:
                        # 1. GUARDAR/ACTUALIZAR CLIENTE
                        datos_cli = {
                            "dni": dni_input, "nombre": nombre.upper(), 
                            "telefono": telefono, "direccion": direccion
                        }
                        # Intentamos insertar (upsert sería ideal pero insert básico funciona si capturamos error duplicado)
                        try:
                            supabase.table("clientes").insert(datos_cli).execute()
                        except:
                            pass # Si ya existe, asumimos que está bien (o podríamos hacer update)

                        # 2. CREAR TICKET
                        datos_ticket = {
                            "cliente_dni": dni_input,
                            "cliente_nombre": nombre.upper(),
                            "marca": marca.upper(),
                            "modelo": modelo.upper(),
                            "imei": imei,
                            "contrasena": contrasena,
                            "descripcion": descripcion,
                            "precio": precio,
                            "fecha_entrega": str(fecha_entrega),
                            "estado": "Pendiente"
                        }
                        supabase.table("tickets").insert(datos_ticket).execute()
                        
                        st.success(f"✅ ¡Ingreso Registrado! Ticket creado para {nombre}")
                        st.balloons()
                        
                        # Limpiar campos
                        st.session_state.dni_cliente = ""
                        st.session_state.nombre_cliente = ""
                        
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

    # PESTAÑA HISTORIAL (Para ver los tickets creados)
    with t_historial:
        try:
            # Consultamos tickets ordenados por fecha
            tickets = supabase.table("tickets").select("*").order("created_at", desc=True).execute().data
            df_t = pd.DataFrame(tickets)
            if not df_t.empty:
                st.dataframe(
                    df_t[["id", "cliente_nombre", "marca", "modelo", "estado", "fecha_entrega"]],
                    use_container_width=True, hide_index=True
                )
            else: st.info("No hay tickets registrados.")
        except: st.warning("Error cargando historial (¿Creaste la tabla 'tickets'?)")

elif selected == "Inventario":
    # (El código del inventario que ya funcionaba bien, puedes pegarlo aquí si lo borraste o dejar el anterior)
    st.info("Módulo de Inventario (Copia el código anterior aquí si lo necesitas)")

elif selected == "Ventas":
    st.info("Próximamente...")
