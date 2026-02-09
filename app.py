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

# --- 3. ESTILOS CSS PRO ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    
    /* SIDEBAR ESTILO VIDEO */
    section[data-testid="stSidebar"] { background-color: #1e293b; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: white !important; }
    
    /* INPUTS */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: white !important; border: 1px solid #cbd5e1; border-radius: 6px; color: #333 !important;
    }
    
    /* BOTONES */
    .stButton>button { border-radius: 6px; font-weight: 700; width: 100%; background-color: #2563EB; color: white; border: none; }
    .stButton>button:hover { background-color: #1d4ed8; }
    
    /* --- ESTILOS DE LA TABLA DE REPARACIÓN (NUEVO) --- */
    .rep-header {
        background-color: #64748b; color: white; padding: 10px; border-radius: 6px 6px 0 0;
        font-weight: bold; font-size: 0.9em; display: flex; text-transform: uppercase;
    }
    .rep-row {
        background-color: white; border: 1px solid #e2e8f0; border-top: none;
        padding: 15px; display: flex; align-items: flex-start; margin-bottom: 5px;
        transition: background 0.2s;
    }
    .rep-row:hover { background-color: #f8fafc; }
    
    .rep-col { flex: 1; padding: 0 10px; font-size: 0.85em; color: #334155; }
    .rep-col strong { color: #0f172a; font-weight: 700; }
    .rep-col ul { padding-left: 15px; margin: 0; }
    
    .status-badge {
        padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; font-size: 0.75em; text-align: center; display: inline-block;
    }
    .bg-blue { background-color: #3b82f6; } /* Recepcionado */
    .bg-green { background-color: #22c55e; } /* Entregado */
    .bg-red { background-color: #ef4444; } /* Anulado */

</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES ---
def generar_ticket_pdf(t):
    """Ticket 80mm"""
    width = 80 * mm; height = 297 * mm 
    buffer = io.BytesIO(); c = canvas.Canvas(buffer, pagesize=(width, height))
    c.setFont("Helvetica-Bold", 12); c.drawCentredString(width/2, height-10*mm, "VILLAFIX OS")
    c.setFont("Helvetica", 10); c.drawCentredString(width/2, height-15*mm, f"Orden #{t['id']}")
    c.drawString(5*mm, height-25*mm, f"Cliente: {t['cliente_nombre']}")
    c.drawString(5*mm, height-30*mm, f"Equipo: {t['marca']} {t['modelo']}")
    c.drawString(5*mm, height-35*mm, f"Total: S/ {t['precio']:.2f}")
    c.showPage(); c.save(); buffer.seek(0); return buffer

def buscar_dni_reniec(dni):
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd"
    try:
        r = requests.get(f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}", headers={'Authorization': f'Bearer {token}'}, timeout=3)
        if r.status_code == 200: 
            d = r.json(); return f"{d.get('nombres','')} {d.get('apellidoPaterno','')} {d.get('apellidoMaterno','')}".strip()
    except: pass
    return None

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reparaciones')
    return output.getvalue()

# --- 5. MENÚ LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/900/900782.png", width=60)
    st.markdown("<h3 style='color:white; margin-top:-10px;'>VillaFix OS</h3>", unsafe_allow_html=True)
    
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Recepción", "Inventario", "Config"],
        icons=["grid-fill", "tools", "box-seam", "gear-fill"],
        default_index=1,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#06b6d4", "font-size": "18px"},
            "nav-link": {"font-size": "15px", "text-align": "left", "margin": "5px", "color": "white"},
            "nav-link-selected": {"background-color": "#2563EB", "font-weight": "bold"},
        }
    )

# --- 6. PÁGINAS ---

if selected == "Dashboard":
    st.title("📊 Panel de Control")

# ==========================================
# MÓDULO RECEPCIÓN (CON PESTAÑAS)
# ==========================================
elif selected == "Recepción":
    
    # PESTAÑAS PRINCIPALES
    tab_form, tab_list = st.tabs(["🛠️ Nueva Recepción", "📋 Listado de Reparación"])
    
    # --- PESTAÑA 1: FORMULARIO (Tu diseño anterior) ---
    with tab_form:
        st.markdown("#### 📝 Información del cliente")
        c_sel, c_btn1, c_btn2 = st.columns([4, 0.5, 0.5])
        with c_sel:
            try:
                clients_db = supabase.table("clientes").select("dni, nombre").execute().data
                client_options = {f"{c['dni']} - {c['nombre']}": c for c in clients_db}
            except: client_options = {}
            selected_client_key = st.selectbox("Seleccione Cliente", ["Nuevo Cliente"] + list(client_options.keys()), label_visibility="collapsed")

        c_btn1.button("🗑️", help="Limpiar"); c_btn2.button("➕", help="Nuevo")

        if selected_client_key != "Nuevo Cliente":
            cli_data = client_options[selected_client_key]
            def_dni = cli_data['dni']; def_nom = cli_data['nombre']
        else: def_dni = ""; def_nom = ""

        with st.container(border=True):
            f1, f2, f3 = st.columns([2, 1, 1])
            nom = f1.text_input("Nombre completos", value=def_nom)
            dni = f2.text_input("Documento (DNI)", value=def_dni)
            if dni and len(dni)==8 and not nom:
                api_name = buscar_dni_reniec(dni)
                if api_name: nom = api_name; st.rerun()
            cel = f3.text_input("Celular")
            f4, f5 = st.columns(2)
            direc = f4.text_input("Direccion"); email = f5.text_input("Email")

        st.write("")
        st.markdown("#### 🔧 Informacion de la recepción")
        with st.container(border=True):
            r1, r2, r3 = st.columns(3)
            marca = r1.selectbox("Marca", ["Samsung", "Apple", "Xiaomi", "Huawei", "Motorola", "Otro"])
            modelo = r2.text_input("Modelo"); imei = r3.text_input("N° IMEI")
            r4, r5, r6 = st.columns(3)
            motivo = r4.selectbox("Motivo", ["Reparación", "Mantenimiento", "Garantía", "Software"])
            f_recep = r5.date_input("Fecha Recepción", value=date.today())
            f_entr = r6.date_input("Fecha Posible Entrega", value=date.today())
            r7, r8, r9 = st.columns(3)
            costo = r7.number_input("Costo Reparación", min_value=0.0)
            clave = r8.text_input("Contraseña / PIN"); 
            try: tecnicos = [u['nombre'] for u in supabase.table("usuarios").select("nombre").execute().data]
            except: tecnicos = ["Admin"]
            tecnico = r9.selectbox("Tecnico Responsable", tecnicos)
            obs = st.text_area("Detalle / Fallas / Observaciones", height=100)

        if st.button("💾 GUARDAR ORDEN DE SERVICIO", type="primary"):
            if not dni or not nom or not modelo: st.error("❌ Faltan datos")
            else:
                try:
                    cli_payload = {"dni": dni, "nombre": nom, "telefono": cel, "direccion": direc, "email": email}
                    supabase.table("clientes").upsert(cli_payload).execute()
                    ticket_payload = {
                        "cliente_dni": dni, "cliente_nombre": nom, "vendedor_nombre": tecnico,
                        "marca": marca, "modelo": modelo, "imei": imei, "contrasena": clave,
                        "falla_reportada": obs, "motivo": motivo, "precio": costo, "acuenta": 0,
                        "saldo": costo, "fecha_entrega": str(f_entr), "estado": "Pendiente"
                    }
                    supabase.table("tickets").insert(ticket_payload).execute()
                    st.success("✅ Orden Generada Correctamente")
                except Exception as e: st.error(f"Error: {e}")

    # --- PESTAÑA 2: LISTADO (ESTILO IMAGEN) ---
    with tab_list:
        st.markdown("#### 📋 Listado de recepción")
        
        # Filtros y Exportación
        c_search, c_export = st.columns([3, 1])
        search_query = c_search.text_input("Buscar (Cliente, DNI, Ticket)", placeholder="Buscar...")
        
        # Obtener Datos
        query = supabase.table("tickets").select("*").order("created_at", desc=True)
        if search_query: query = query.ilike("cliente_nombre", f"%{search_query}%")
        data = query.execute().data
        
        # Botón Excel
        if data:
            df_export = pd.DataFrame(data)
            excel_data = convert_df_to_excel(df_export)
            c_export.download_button("📗 Exportar a Excel", data=excel_data, file_name="reparaciones.xlsx", mime="application/vnd.ms-excel", use_container_width=True)
        
        # ENCABEZADO TIPO TABLA (GRIS)
        st.markdown("""
        <div class="rep-header">
            <div style="width:10%;">Estado</div>
            <div style="flex:1;">Cliente</div>
            <div style="flex:1;">Información</div>
            <div style="flex:1;">Montos</div>
            <div style="flex:1;">Fechas</div>
        </div>
        """, unsafe_allow_html=True)
        
        # FILAS (Renderizado Manual para diseño exacto)
        if data:
            for t in data:
                # Colores de estado
                st_color = "bg-blue"
                if t['estado'] == 'Entregado': st_color = "bg-green"
                if t['estado'] == 'Anulado': st_color = "bg-red"
                
                # Formato Fechas
                f_rec = datetime.fromisoformat(t['created_at']).strftime('%d-%m-%Y')
                f_ent = t['fecha_entrega'] if t['fecha_entrega'] else "-"
                
                st.markdown(f"""
                <div class="rep-row">
                    <div style="width:10%; text-align:center;">
                        <span class="status-badge {st_color}">{t['estado']}</span>
                    </div>
                    <div class="rep-col">
                        <ul>
                            <li><strong>Ticket:</strong> #{t['id']}</li>
                            <li><strong>Nom:</strong> {t['cliente_nombre']}</li>
                            <li><strong>DNI:</strong> {t['cliente_dni']}</li>
                        </ul>
                    </div>
                    <div class="rep-col">
                        <ul>
                            <li><strong>Motivo:</strong> {t['motivo']}</li>
                            <li><strong>Equipo:</strong> {t['marca']} - {t['modelo']}</li>
                            <li><strong>Técnico:</strong> {t['vendedor_nombre']}</li>
                        </ul>
                    </div>
                    <div class="rep-col">
                        <ul>
                            <li><strong>Total:</strong> S/ {t['precio']:.2f}</li>
                            <li><strong>A Cuenta:</strong> S/ {t['acuenta']:.2f}</li>
                            <li style="color:{'red' if t['saldo']>0 else 'green'};"><strong>Resta:</strong> S/ {t['saldo']:.2f}</li>
                        </ul>
                    </div>
                    <div class="rep-col">
                        <ul>
                            <li><strong>Recepción:</strong> {f_rec}</li>
                            <li><strong>Entrega:</strong> {f_ent}</li>
                        </ul>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No se encontraron reparaciones.")

elif selected == "Inventario":
    st.info("Inventario")

elif selected == "Config":
    st.write("Configuración")
