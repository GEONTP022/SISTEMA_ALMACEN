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
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stDateInput>div>div>input, .stSelectbox>div>div>div { 
        background-color: #ffffff !important; 
        color: #212529 !important; 
        border: 1px solid #ced4da;
        border-radius: 6px;
    }
    .dashboard-card {
        padding: 20px; border-radius: 12px; color: white !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-bottom: 15px;
    }
    .card-green { background-color: #28a745; }
    .card-orange { background-color: #fd7e14; }
    .card-blue { background-color: #17a2b8; }
    .card-yellow { background-color: #ffc107; color: #333 !important; }
    .stButton>button { border-radius: 6px; font-weight: 600; width: 100%; }
    
    /* Estilo para mensajes de error pequeños */
    .small-error { color: #dc3545; font-size: 0.85rem; margin-top: -10px; margin-bottom: 10px; font-weight: bold;}
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
        count_tickets = supabase.table("tickets").select("id", count="exact").eq("estado", "Pendiente").execute().count
    except: count_prod = 0; count_cli = 0; count_tickets = 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="dashboard-card card-green"><h3>👥 {count_cli}</h3><p>Clientes</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="dashboard-card card-orange"><h3>📦 {count_prod}</h3><p>Productos</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="dashboard-card card-blue"><h3>🔧 {count_tickets}</h3><p>En Reparación</p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="dashboard-card card-yellow"><h3>💰 S/ 0</h3><p>Ingresos</p></div>', unsafe_allow_html=True)

# === PÁGINA: RECEPCIÓN (VALIDACIÓN EN SU SITIO) ===
elif selected == "Recepción":
    st.markdown("### 📝 Nueva Orden de Servicio")
    
    t_ingreso, t_historial = st.tabs(["🆕 Nuevo Ticket", "📋 Historial"])
    
    with t_ingreso:
        # --- 1. DATOS DEL CLIENTE (ARRIBA) ---
        st.caption("👤 DATOS DEL CLIENTE")
        with st.container(border=True):
            if 'nombre_cliente' not in st.session_state: st.session_state.nombre_cliente = ""
            if 'dni_cliente' not in st.session_state: st.session_state.dni_cliente = ""

            c_dni, c_btn, c_cls = st.columns([3, 1, 0.5])
            dni_input = c_dni.text_input("DNI *", value=st.session_state.dni_cliente, placeholder="Ingrese DNI")
            err_dni = st.empty() # Placeholder para error de DNI

            if dni_input != st.session_state.dni_cliente:
                st.session_state.dni_cliente = dni_input
                st.session_state.nombre_cliente = ""

            if c_btn.button("🔍 Buscar"):
                if len(dni_input) == 8:
                    res_db = supabase.table("clientes").select("*").eq("dni", dni_input).execute()
                    if res_db.data:
                        st.session_state.nombre_cliente = res_db.data[0]["nombre"]
                        st.toast("Cliente Frecuente", icon="✅")
                    else:
                        with st.spinner("Buscando en RENIEC..."):
                            nom = consultar_dni_reniec(dni_input)
                            if nom: st.session_state.nombre_cliente = nom
                            else: st.warning("No encontrado")
                else: err_dni.error("⚠️ DNI debe tener 8 dígitos")
            
            if c_cls.button("🗑️"):
                st.session_state.dni_cliente = ""; st.session_state.nombre_cliente = ""; st.rerun()

            nombre = st.text_input("Nombre Completo *", value=st.session_state.nombre_cliente)
            err_nombre = st.empty() # Placeholder error nombre

            c_tel, c_dir = st.columns(2)
            telefono = c_tel.text_input("Teléfono / WhatsApp *")
            err_telefono = st.empty()
            direccion = c_dir.text_input("Dirección")

        st.write("") 
        
        # --- 2. DATOS DEL TICKET (ABAJO) ---
        st.caption("🔧 DATOS DEL EQUIPO & SERVICIO")
        
        # Usamos contenedores para organizar, NO st.form para poder validar en vivo
        with st.container(border=True):
            col_eq1, col_eq2 = st.columns(2)
            
            with col_eq1:
                marca = st.text_input("Marca *", placeholder="Ej: Samsung")
                err_marca = st.empty() # <--- Aquí saldrá el error rojo si falta marca
                
                modelo = st.text_input("Modelo *", placeholder="Ej: A54")
                err_modelo = st.empty()
                
                imei = st.text_input("IMEI / Serie (Opcional)")
                
                # NUEVO: MOTIVO
                motivo = st.selectbox("Motivo del Servicio *", ["Reparación", "Mantenimiento", "Garantía", "Instalación", "Otro"])

            with col_eq2:
                contrasena = st.text_input("Contraseña / Patrón *", placeholder="Si no tiene, poner 'SIN CLAVE'")
                err_contra = st.empty()
                
                precio = st.number_input("Costo Estimado (S/) *", min_value=0.0)
                
                # FECHAS
                c_f1, c_f2 = st.columns(2)
                fecha_recepcion = c_f1.date_input("Fecha Recepción", value=date.today())
                fecha_entrega = c_f2.date_input("Fecha Entrega Aprox. *", value=date.today(), min_value=date.today())

            descripcion = st.text_area("Descripción de la Falla / Detalles *", height=100)
            err_desc = st.empty()

        st.write("")
        btn_registrar = st.button("💾 GENERAR TICKET", type="primary", use_container_width=True)

        # --- LÓGICA DE VALIDACIÓN (AQUÍ OCURRE LA MAGIA) ---
        if btn_registrar:
            valido = True
            
            # 1. Validar DNI
            if len(dni_input) != 8:
                err_dni.error("❌ El DNI es obligatorio y debe tener 8 dígitos.")
                valido = False
            
            # 2. Validar Nombre
            if not nombre:
                err_nombre.error("❌ El Nombre es obligatorio.")
                valido = False

            # 3. Validar Teléfono
            if not telefono:
                err_telefono.error("❌ El Teléfono es obligatorio.")
                valido = False

            # 4. Validar Equipo
            if not marca:
                err_marca.error("❌ Falta la Marca.")
                valido = False
            if not modelo:
                err_modelo.error("❌ Falta el Modelo.")
                valido = False
            if not contrasena:
                err_contra.error("❌ Obligatorio. Si no tiene, escribe 'S/C'.")
                valido = False
            if not descripcion:
                err_desc.error("❌ Debes describir el problema.")
                valido = False

            # SI TODO ESTÁ BIEN, GUARDAMOS
            if valido:
                try:
                    # A. Guardar Cliente
                    try:
                        supabase.table("clientes").insert({
                            "dni": dni_input, "nombre": nombre.upper(), 
                            "telefono": telefono, "direccion": direccion
                        }).execute()
                    except: pass # Si ya existe, ignoramos

                    # B. Guardar Ticket
                    datos_ticket = {
                        "cliente_dni": dni_input,
                        "cliente_nombre": nombre.upper(),
                        "marca": marca.upper(),
                        "modelo": modelo.upper(),
                        "imei": imei,
                        "contrasena": contrasena,
                        "descripcion": descripcion,
                        "motivo": motivo,           # <--- NUEVO CAMPO
                        "precio": precio,
                        "fecha_recepcion": str(fecha_recepcion), # <--- NUEVO CAMPO
                        "fecha_entrega": str(fecha_entrega),
                        "estado": "Pendiente"
                    }
                    supabase.table("tickets").insert(datos_ticket).execute()
                    
                    st.success(f"✅ Ticket Creado Exitosamente para {nombre}")
                    st.balloons()
                    
                    # Limpieza manual
                    st.session_state.dni_cliente = ""
                    st.session_state.nombre_cliente = ""
                    # Nota: Para limpiar los campos de texto normales en Streamlit sin rerurn 
                    # a veces se requiere un truco, pero aquí el usuario verá el éxito y podrá recargar.
                    
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.toast("⚠️ Faltan datos obligatorios, revisa las casillas rojas.", icon="🚨")

    with t_historial:
        try:
            tickets = supabase.table("tickets").select("*").order("created_at", desc=True).execute().data
            if tickets:
                df = pd.DataFrame(tickets)
                st.dataframe(df[["id", "cliente_nombre", "marca", "motivo", "estado", "fecha_entrega"]], use_container_width=True, hide_index=True)
            else: st.info("No hay tickets.")
        except: pass

elif selected == "Inventario":
    st.info("📦 Módulo de Inventario (Código previo)")
    # (Pega aquí tu código de inventario si lo necesitas)

elif selected == "Ventas":
    st.info("Próximamente...")
