import streamlit as st
import pandas as pd
import requests
from supabase import create_client
from streamlit_option_menu import option_menu
from datetime import datetime, date, timedelta
import io
import textwrap
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
import tempfile

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="VillaFix OS",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except:
    st.error("⚠️ Error de conexión.")
    st.stop()

# --- 3. ESTILOS CSS (CORRECCIÓN DE COLORES Y DISEÑO) ---
st.markdown("""
<style>
    /* Fondo principal limpio */
    .stApp { background-color: #f8f9fa; }
    
    /* BARRA LATERAL ESTILO VIDEO (OSCURO + CIAN) */
    section[data-testid="stSidebar"] {
        background-color: #1e293b; /* Gris azulado oscuro profesional */
    }
    
    /* Textos generales de la sidebar */
    section[data-testid="stSidebar"] .stMarkdown h1, 
    section[data-testid="stSidebar"] .stMarkdown h2, 
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #ffffff !important;
    }
    
    /* Inputs estilizados */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: white !important; 
        border: 1px solid #cbd5e1; 
        border-radius: 6px;
        color: #333 !important;
    }
    
    /* Etiquetas de los inputs (Labels) */
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label, .stTextArea label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #4b5563;
    }

    /* Botones */
    .stButton>button {
        border-radius: 6px; font-weight: 700; width: 100%;
        background-color: #2563EB; color: white; border: none;
    }
    .stButton>button:hover { background-color: #1d4ed8; }
    
    /* Estilo especial para botón rojo (Eliminar/Cancelar) */
    .btn-danger { background-color: #ef4444 !important; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES ---
def generar_ticket_pdf(t):
    """Ticket simplificado 80mm"""
    width = 80 * mm; height = 297 * mm 
    buffer = io.BytesIO(); c = canvas.Canvas(buffer, pagesize=(width, height))
    c.setFont("Helvetica-Bold", 12); c.drawCentredString(width/2, height-10*mm, "VILLAFIX OS")
    c.setFont("Helvetica", 10); c.drawCentredString(width/2, height-15*mm, f"Orden #{t['id']}")
    c.drawString(5*mm, height-25*mm, f"Cliente: {t['cliente_nombre']}")
    c.drawString(5*mm, height-30*mm, f"Equipo: {t['marca']} {t['modelo']}")
    c.drawString(5*mm, height-35*mm, f"Total: S/ {t['precio']:.2f}")
    c.showPage(); c.save(); buffer.seek(0); return buffer

def buscar_dni_reniec(dni):
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd" # Tu token
    try:
        r = requests.get(f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}", headers={'Authorization': f'Bearer {token}'}, timeout=3)
        if r.status_code == 200: 
            d = r.json(); return f"{d.get('nombres','')} {d.get('apellidoPaterno','')} {d.get('apellidoMaterno','')}".strip()
    except: pass
    return None

# --- 5. MENÚ LATERAL (DISEÑO VIDEO) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/900/900782.png", width=60) # Logo genérico
    st.markdown("<h3 style='color:white; margin-top:-10px;'>VillaFix OS</h3>", unsafe_allow_html=True)
    
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Recepción", "Inventario", "Config"],
        icons=["grid-fill", "tools", "box-seam", "gear-fill"],
        default_index=1,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#06b6d4", "font-size": "18px"}, # Cian brillante
            "nav-link": {
                "font-size": "15px",
                "text-align": "left",
                "margin": "5px",
                "color": "white", # TEXTO BLANCO (Corrección de color)
            },
            "nav-link-selected": {"background-color": "#2563EB", "font-weight": "bold"},
        }
    )

# --- 6. PÁGINAS ---

if selected == "Dashboard":
    st.title("📊 Panel de Control")
    st.info("Módulo de estadísticas")

# ==========================================
# MÓDULO RECEPCIÓN (DISEÑO IDÉNTICO A LA IMAGEN)
# ==========================================
elif selected == "Recepción":
    
    # -- SECCIÓN 1: INFORMACIÓN DEL CLIENTE --
    st.markdown("#### 📝 Información del cliente")
    
    # Fila de búsqueda/selección
    c_sel, c_btn1, c_btn2 = st.columns([4, 0.5, 0.5])
    with c_sel:
        # Lógica para cargar clientes existentes
        try:
            clients_db = supabase.table("clientes").select("dni, nombre").execute().data
            client_options = {f"{c['dni']} - {c['nombre']}": c for c in clients_db}
        except: client_options = {}
        
        selected_client_key = st.selectbox("Seleccione Cliente", ["Nuevo Cliente"] + list(client_options.keys()), label_visibility="collapsed")

    # Botones decorativos (funcionalidad visual)
    c_btn1.button("🗑️", help="Limpiar")
    c_btn2.button("➕", help="Nuevo")

    # Lógica de auto-llenado
    if selected_client_key != "Nuevo Cliente":
        cli_data = client_options[selected_client_key]
        def_dni = cli_data['dni']
        def_nom = cli_data['nombre']
    else:
        def_dni = ""; def_nom = ""

    # Formulario Cliente (Grid)
    with st.container(border=True):
        f1, f2, f3 = st.columns([2, 1, 1])
        nom = f1.text_input("Nombre completos", value=def_nom, placeholder="Nombre cliente")
        dni = f2.text_input("Documento (DNI)", value=def_dni, placeholder="DNI")
        # Botón mágico de búsqueda DNI dentro del input
        if dni and len(dni)==8 and not nom:
            api_name = buscar_dni_reniec(dni)
            if api_name: nom = api_name; st.rerun()
            
        cel = f3.text_input("Celular", placeholder="Celular")
        
        f4, f5 = st.columns(2)
        direc = f4.text_input("Direccion", placeholder="Dirección")
        email = f5.text_input("Email", placeholder="Email")

    st.write("") # Espacio

    # -- SECCIÓN 2: INFORMACIÓN DE RECEPCIÓN --
    st.markdown("#### 🔧 Informacion de la recepción")
    
    with st.container(border=True):
        # Fila 1: Equipo
        r1, r2, r3 = st.columns(3)
        marca = r1.selectbox("Marca", ["Samsung", "Apple", "Xiaomi", "Huawei", "Motorola", "Otro"])
        modelo = r2.text_input("Modelo", placeholder="Ejm: iPhone 13 Pro")
        imei = r3.text_input("N° IMEI", placeholder="Ejm: 35416305...")
        
        # Fila 2: Datos Servicio
        r4, r5, r6 = st.columns(3)
        motivo = r4.selectbox("Motivo", ["Reparación", "Mantenimiento", "Garantía", "Software"])
        f_recep = r5.date_input("Fecha Recepción", value=date.today())
        f_entr = r6.date_input("Fecha Posible Entrega", value=date.today())
        
        # Fila 3: Técnico y Costos
        r7, r8, r9 = st.columns(3)
        costo = r7.number_input("Costo Reparación", min_value=0.0, step=5.0)
        clave = r8.text_input("Contraseña / PIN", placeholder="clave telefono")
        
        # Cargar técnicos (Usuarios)
        try:
            tecnicos = [u['nombre'] for u in supabase.table("usuarios").select("nombre").execute().data]
        except: tecnicos = ["Admin"]
        tecnico = r9.selectbox("Tecnico Responsable", tecnicos)
        
        # Fila 4: Observaciones
        obs = st.text_area("Detalle / Fallas / Observaciones", placeholder="Observaciones", height=100)

    # -- BOTÓN GUARDAR (ACCIÓN FINAL) --
    st.divider()
    if st.button("💾 GUARDAR ORDEN DE SERVICIO", type="primary"):
        if not dni or not nom or not modelo:
            st.error("❌ Faltan datos obligatorios (DNI, Nombre, Modelo)")
        else:
            try:
                # 1. Guardar/Actualizar Cliente
                cli_payload = {"dni": dni, "nombre": nom, "telefono": cel, "direccion": direc, "email": email}
                supabase.table("clientes").upsert(cli_payload).execute()
                
                # 2. Guardar Ticket
                ticket_payload = {
                    "cliente_dni": dni,
                    "cliente_nombre": nom,
                    "vendedor_nombre": tecnico, # Usamos el técnico seleccionado
                    "marca": marca,
                    "modelo": modelo,
                    "imei": imei,
                    "contrasena": clave,
                    "falla_reportada": obs,
                    "motivo": motivo, # Nuevo campo
                    "precio": costo,
                    "acuenta": 0,     # Inicialmente 0 si no se cobra aquí
                    "saldo": costo,
                    "fecha_entrega": str(f_entr),
                    "estado": "Pendiente"
                }
                res = supabase.table("tickets").insert(ticket_payload).execute()
                
                st.success(f"✅ Orden Generada Correctamente")
                # Opcional: Mostrar PDF aquí
                
            except Exception as e:
                st.error(f"Error al guardar: {e}")

elif selected == "Inventario":
    st.info("Módulo Inventario")

elif selected == "Config":
    st.write("Configuración")
