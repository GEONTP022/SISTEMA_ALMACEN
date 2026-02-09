import streamlit as st
import pandas as pd
import requests
from supabase import create_client
from streamlit_option_menu import option_menu
from datetime import datetime, date
import io
import textwrap
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
import tempfile

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="VillaFix OS", page_icon="🛠️", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except: st.error("⚠️ Error DB"); st.stop()

# --- 3. ESTILOS CSS (DISEÑO VILLAFIX PRO) ---
st.markdown("""
<style>
    .stApp { background-color: #f1f5f9; }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] { background-color: #0f172a; } /* Azul noche */
    section[data-testid="stSidebar"] h1, h2, h3 { color: white !important; }
    
    /* INPUTS & BOTONES */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: white !important; border: 1px solid #cbd5e1; border-radius: 6px; color: #333 !important;
    }
    .stButton>button { border-radius: 6px; font-weight: 700; width: 100%; border: none; transition: 0.2s; }
    
    /* --- TABLA DE REPARACIÓN (ESTILO ÚNICO) --- */
    .rep-container { font-family: 'Source Sans Pro', sans-serif; margin-bottom: 8px; }
    
    .rep-header {
        background-color: #334155; color: white; padding: 12px 15px; border-radius: 8px 8px 0 0;
        font-weight: 700; font-size: 0.85em; display: flex; text-transform: uppercase; letter-spacing: 0.5px;
    }
    
    .rep-row {
        background-color: white; border: 1px solid #e2e8f0; border-top: none;
        padding: 12px 15px; display: flex; align-items: center; 
        transition: transform 0.1s, box-shadow 0.1s;
    }
    .rep-row:last-child { border-radius: 0 0 8px 8px; }
    .rep-row:hover { background-color: #f8fafc; border-left: 4px solid #2563EB; }
    
    .rep-col { flex: 1; font-size: 0.85em; color: #475569; padding-right: 10px; }
    .rep-col strong { color: #0f172a; font-weight: 700; }
    .rep-col div { margin-bottom: 3px; }
    
    /* BADGES */
    .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.7em; font-weight: 800; text-transform: uppercase; color: white; display: inline-block; }
    .bg-blue { background-color: #3b82f6; }    /* Recepcionado */
    .bg-green { background-color: #10b981; }   /* Entregado/Pagado */
    .bg-red { background-color: #ef4444; }     /* Anulado/Debe */
    .bg-orange { background-color: #f59e0b; }  /* Pendiente */

    /* BARRA DE HERRAMIENTAS */
    .toolbar { background: #e2e8f0; padding: 10px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #cbd5e1; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES ---
def generar_ticket_pdf(t):
    width = 80 * mm; height = 297 * mm 
    buffer = io.BytesIO(); c = canvas.Canvas(buffer, pagesize=(width, height))
    c.setFont("Helvetica-Bold", 12); c.drawCentredString(width/2, height-10*mm, "VILLAFIX OS")
    c.setFont("Helvetica", 10); c.drawCentredString(width/2, height-15*mm, f"Orden #{t['id']}")
    c.drawString(5*mm, height-25*mm, f"Cliente: {t['cliente_nombre']}")
    c.drawString(5*mm, height-30*mm, f"Equipo: {t['marca']} {t['modelo']}")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(5*mm, height-45*mm, f"Total: S/ {t['precio']:.2f}")
    c.drawString(5*mm, height-50*mm, f"Saldo: S/ {t['saldo']:.2f}")
    c.showPage(); c.save(); buffer.seek(0); return buffer

def buscar_dni_reniec(dni):
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd"
    try:
        r = requests.get(f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}", headers={'Authorization': f'Bearer {token}'}, timeout=3)
        if r.status_code == 200: 
            d = r.json(); return f"{d.get('nombres','')} {d.get('apellidoPaterno','')} {d.get('apellidoMaterno','')}".strip()
    except: pass
    return None

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- 5. MODALES INTERACTIVOS (ST.DIALOG) ---

@st.dialog("Gestión de Reparación")
def gestion_modal(t):
    st.markdown(f"### 🔧 Orden #{t['id']} - {t['cliente_nombre']}")
    
    # Resumen rápido
    c1, c2, c3 = st.columns(3)
    c1.info(f"Equipo: {t['marca']} {t['modelo']}")
    c2.warning(f"Deuda: S/ {t['saldo']:.2f}")
    c3.success(f"Total: S/ {t['precio']:.2f}")

    # Menú de acciones (Pestañas como en tu imagen mental)
    tab_pagar, tab_ver, tab_anular = st.tabs(["💰 Realizar Pago", "📄 Ver Ticket", "🚫 Anular"])

    # --- 1. PAGAR ---
    with tab_pagar:
        if t['saldo'] <= 0:
            st.success("✅ ¡Esta orden ya está pagada en su totalidad!")
        else:
            st.write("Agregar pago a cuenta o cancelar total.")
            monto_pagar = st.number_input("Monto a Pagar (S/)", min_value=0.0, max_value=float(t['saldo']), value=float(t['saldo']))
            metodo = st.selectbox("Medio de Pago", ["Efectivo", "Yape", "Plin", "Tarjeta"])
            
            if st.button("✅ Confirmar Pago", use_container_width=True):
                nuevo_acuenta = t['acuenta'] + monto_pagar
                nuevo_saldo = t['precio'] - nuevo_acuenta
                nuevo_estado = "Entregado" if nuevo_saldo == 0 else "Pendiente"
                
                supabase.table("tickets").update({
                    "acuenta": nuevo_acuenta, "saldo": nuevo_saldo, "estado": nuevo_estado
                }).eq("id", t['id']).execute()
                st.toast("Pago registrado correctamente"); st.rerun()

    # --- 2. VER TICKET ---
    with tab_ver:
        pdf = generar_ticket_pdf(t)
        st.download_button("🖨️ Descargar PDF", pdf, f"Ticket_{t['id']}.pdf", "application/pdf", use_container_width=True)
        st.text_area("Diagnóstico Técnico", value=t['falla_reportada'], disabled=True)

    # --- 3. ANULAR ---
    with tab_anular:
        st.error("⚠️ Zona de Peligro")
        st.write("¿Está seguro de anular esta reparación? Esta acción no se puede deshacer.")
        if st.button("🚨 SÍ, ANULAR ORDEN", type="primary", use_container_width=True):
            supabase.table("tickets").update({"estado": "Anulado", "saldo": 0}).eq("id", t['id']).execute()
            st.rerun()

# --- 6. MENU LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/900/900782.png", width=50)
    st.markdown("### VillaFix OS")
    selected = option_menu(None, ["Dashboard", "Recepción", "Inventario", "Config"], 
        icons=["grid-fill", "tools", "box-seam", "gear-fill"], default_index=1,
        styles={"nav-link-selected": {"background-color": "#2563EB"}})

# --- 7. CONTENIDO ---

if selected == "Recepción":
    tab_new, tab_list = st.tabs(["✨ Nueva Recepción", "📋 Listado de Reparaciones"])

    # --- PESTAÑA 1: FORMULARIO ---
    with tab_new:
        st.markdown("#### Datos del Cliente")
        c_sel, x, y = st.columns([4, 0.5, 0.5])
        try: clients = {f"{c['dni']} - {c['nombre']}": c for c in supabase.table("clientes").select("dni,nombre").execute().data}
        except: clients = {}
        sel_cli = c_sel.selectbox("Buscar Cliente", ["Nuevo"] + list(clients.keys()), label_visibility="collapsed")
        
        # Datos automáticos
        d_dni = clients[sel_cli]['dni'] if sel_cli != "Nuevo" else ""
        d_nom = clients[sel_cli]['nombre'] if sel_cli != "Nuevo" else ""

        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            nom = c1.text_input("Nombre", value=d_nom)
            dni = c2.text_input("DNI", value=d_dni)
            if dni and len(dni)==8 and not nom:
                if n := buscar_dni_reniec(dni): nom = n; st.rerun()
            cel = c3.text_input("Celular")
            c4, c5 = st.columns(2); dir = c4.text_input("Dirección"); em = c5.text_input("Email")

        st.markdown("#### Datos del Equipo")
        with st.container(border=True):
            r1, r2, r3 = st.columns(3)
            mar = r1.selectbox("Marca", ["Samsung", "Apple", "Xiaomi", "Motorola", "Otro"])
            mod = r2.text_input("Modelo")
            imei = r3.text_input("IMEI")
            
            r4, r5, r6 = st.columns(3)
            mot = r4.selectbox("Motivo", ["Reparación", "Mantenimiento", "Garantía"])
            f_ent = r5.date_input("Entrega Aprox", date.today())
            tec = r6.selectbox("Técnico", ["Admin", "Técnico 1"])
            
            r7, r8, r9 = st.columns(3)
            cost = r7.number_input("Costo (S/)", 0.0)
            clav = r8.text_input("Clave/Patrón")
            
            obs = st.text_area("Falla / Observaciones")

        if st.button("💾 GENERAR ORDEN", type="primary"):
            if not dni or not nom or not mod: st.error("Faltan datos")
            else:
                try:
                    supabase.table("clientes").upsert({"dni":dni, "nombre":nom, "telefono":cel, "direccion":dir, "email":em}).execute()
                    supabase.table("tickets").insert({
                        "cliente_dni":dni, "cliente_nombre":nom, "vendedor_nombre":tec,
                        "marca":mar, "modelo":mod, "imei":imei, "contrasena":clav,
                        "falla_reportada":obs, "motivo":mot, "precio":cost, "acuenta":0, "saldo":cost,
                        "fecha_entrega":str(f_ent), "estado":"Pendiente"
                    }).execute()
                    st.success("Orden Creada"); st.rerun()
                except Exception as e: st.error(str(e))

    # --- PESTAÑA 2: LISTADO AVANZADO (DISEÑO VILLAFIX) ---
    with tab_list:
        # BARRA DE HERRAMIENTAS (TOOLBAR)
        with st.container():
            st.markdown('<div class="toolbar">', unsafe_allow_html=True)
            c_filtro, c_excel = st.columns([4, 1])
            search = c_filtro.text_input("🔍 Buscar por Cliente, DNI o Ticket", label_visibility="collapsed", placeholder="Escribe para buscar...")
            
            # Obtener datos
            q = supabase.table("tickets").select("*").order("created_at", desc=True)
            if search: q = q.ilike("cliente_nombre", f"%{search}%")
            data = q.execute().data
            
            if data:
                excel = to_excel(pd.DataFrame(data))
                c_excel.download_button("📗 Exportar Excel", excel, "reporte.xlsx", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ENCABEZADO DE TABLA (GRIS OSCURO)
        st.markdown("""
        <div class="rep-container">
            <div class="rep-header">
                <div style="width:100px; text-align:center;">Acción</div>
                <div style="width:120px; text-align:center;">Estado</div>
                <div class="rep-col">Cliente</div>
                <div class="rep-col">Equipo / Motivo</div>
                <div class="rep-col">Técnico</div>
                <div class="rep-col" style="text-align:right;">Saldo</div>
                <div class="rep-col" style="text-align:right;">Fechas</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # FILAS DE DATOS (CON BOTÓN DE ACCIÓN REAL)
        if data:
            for t in data:
                # Lógica de Colores
                if t['estado'] == 'Anulado': bg = "bg-red"; st_txt = "ANULADO"
                elif t['saldo'] <= 0: bg = "bg-green"; st_txt = "ENTREGADO"
                else: bg = "bg-blue"; st_txt = "EN TALLER"

                f_ing = datetime.fromisoformat(t['created_at']).strftime("%d/%m")
                f_ent = t['fecha_entrega'] if t['fecha_entrega'] else "-"

                # Diseño de Fila (Mix HTML + Streamlit Columns para el botón)
                col_ui, col_btn = st.columns([0.1, 0.9]) # Pequeña columna invisible para alineación
                
                with st.container():
                    # Usamos columnas de Streamlit para poder meter el botón nativo
                    c_btn, c_info = st.columns([1.5, 10])
                    
                    with c_btn:
                        # EL BOTÓN DE ENGRANAJE (Acción Principal)
                        if st.button("⚙️", key=f"act_{t['id']}", help="Gestionar Orden"):
                            gestion_modal(t)
                    
                    with c_info:
                        # El resto de la info en HTML bonito
                        html_row = f"""
                        <div class="rep-row" style="margin-left:-15px;">
                            <div style="width:120px; text-align:center;">
                                <span class="badge {bg}">{st_txt}</span>
                            </div>
                            <div class="rep-col">
                                <div><strong>#{t['id']}</strong></div>
                                <div>{t['cliente_nombre'].split()[0]}</div>
                                <div style="font-size:0.8em; color:#64748b;">{t['cliente_dni']}</div>
                            </div>
                            <div class="rep-col">
                                <div><strong>{t['modelo']}</strong></div>
                                <div>{t['marca']}</div>
                                <div style="font-size:0.8em;">{t['motivo']}</div>
                            </div>
                            <div class="rep-col">
                                <div>{t['vendedor_nombre']}</div>
                                <div style="font-size:0.8em;">Clave: {t['contrasena']}</div>
                            </div>
                            <div class="rep-col" style="text-align:right;">
                                <div style="color:#ef4444; font-weight:bold;">S/ {t['saldo']:.2f}</div>
                                <div style="font-size:0.8em;">Total: {t['precio']:.2f}</div>
                            </div>
                            <div class="rep-col" style="text-align:right;">
                                <div>In: {f_ing}</div>
                                <div>Out: {f_ent}</div>
                            </div>
                        </div>
                        """
                        st.markdown(html_row, unsafe_allow_html=True)
        else:
            st.info("No hay reparaciones registradas.")

# (Resto de módulos simplificados para no exceder longitud)
elif selected == "Dashboard": pass
elif selected == "Inventario": pass
elif selected == "Config": pass
