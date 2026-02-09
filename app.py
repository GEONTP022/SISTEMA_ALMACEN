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
import plotly.express as px

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="VillaFix OS",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIÓN A BASE DE DATOS ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except:
    st.error("⚠️ Error crítico de conexión. Verifica tus 'secrets'.")
    st.stop()

# --- 3. ESTILOS CSS (DISEÑO PROFESIONAL VILLAFIX) ---
st.markdown("""
<style>
    /* FONDO Y TEXTOS */
    .stApp { background-color: #f1f5f9; font-family: 'Source Sans Pro', sans-serif; }
    
    /* SIDEBAR (AZUL NOCHE) */
    section[data-testid="stSidebar"] { background-color: #0f172a; }
    section[data-testid="stSidebar"] h1, h2, h3 { color: white !important; }
    section[data-testid="stSidebar"] span { color: #e2e8f0; }
    
    /* INPUTS & FORMULARIOS */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: white !important; 
        border: 1px solid #cbd5e1; 
        border-radius: 6px; 
        color: #1e293b !important;
    }
    
    /* BOTONES */
    .stButton>button {
        border-radius: 6px; font-weight: 700; width: 100%; 
        border: none; transition: 0.2s; background-color: #2563EB; color: white;
    }
    .stButton>button:hover { background-color: #1d4ed8; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    
    /* --- TABLA DE REPARACIÓN (ESTILO PERSONALIZADO) --- */
    .rep-container { margin-bottom: 5px; }
    
    .rep-header {
        background-color: #334155; color: white; padding: 12px 10px; border-radius: 8px 8px 0 0;
        font-weight: 700; font-size: 0.85em; display: flex; text-transform: uppercase; letter-spacing: 0.5px;
    }
    
    /* FILA DE DATOS (Diseño limpio) */
    .rep-card {
        background-color: white; border: 1px solid #e2e8f0; border-top: none;
        padding: 10px; transition: all 0.1s; display: flex; align-items: center;
    }
    .rep-card:hover { background-color: #f8fafc; border-left: 4px solid #2563EB; }
    
    .rep-col { flex: 1; font-size: 0.85em; color: #475569; padding: 0 8px; }
    .rep-col strong { color: #0f172a; font-weight: 700; display: block; margin-bottom: 2px; }
    .rep-col span { display: block; line-height: 1.3; }
    
    /* BADGES DE ESTADO */
    .badge { padding: 3px 8px; border-radius: 12px; font-size: 0.7em; font-weight: 800; text-transform: uppercase; color: white; display: inline-block; text-align: center; min-width: 80px; }
    .bg-blue { background-color: #3b82f6; }    /* En Taller */
    .bg-green { background-color: #10b981; }   /* Entregado */
    .bg-red { background-color: #ef4444; }     /* Anulado */
    .bg-orange { background-color: #f59e0b; }  /* Pendiente */

    /* DASHBOARD CARDS */
    .kpi-card { background: white; padding: 20px; border-radius: 10px; border-left: 5px solid #06b6d4; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
    .kpi-val { font-size: 24px; font-weight: 800; color: #1e293b; }
    .kpi-lbl { font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; }

</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES UTILITARIAS ---

def generar_ticket_pdf(t):
    """Genera PDF térmico 80mm"""
    width = 80 * mm; height = 297 * mm 
    buffer = io.BytesIO(); c = canvas.Canvas(buffer, pagesize=(width, height))
    c.setFont("Helvetica-Bold", 12); c.drawCentredString(width/2, height-10*mm, "VILLAFIX OS")
    c.setFont("Helvetica", 10); c.drawCentredString(width/2, height-15*mm, f"Orden #{t['id']}")
    c.setFont("Helvetica", 9); c.drawString(5*mm, height-25*mm, f"Cliente: {t['cliente_nombre']}")
    c.drawString(5*mm, height-30*mm, f"DNI: {t['cliente_dni']}")
    c.line(5*mm, height-35*mm, width-5*mm, height-35*mm)
    c.drawString(5*mm, height-40*mm, f"Equipo: {t['marca']} {t['modelo']}")
    c.drawString(5*mm, height-45*mm, f"Falla: {t['falla_reportada'][:30]}...")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(5*mm, height-55*mm, f"TOTAL: S/ {t['precio']:.2f}")
    c.drawString(5*mm, height-60*mm, f"SALDO: S/ {t['saldo']:.2f}")
    c.setFont("Helvetica", 8); c.drawCentredString(width/2, height-70*mm, "Gracias por su preferencia")
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
        df.to_excel(writer, index=False, sheet_name='Data')
    return output.getvalue()

# --- 5. MODALES (ST.DIALOG) ---

@st.dialog("Gestión de Orden")
def gestion_modal(t):
    st.markdown(f"### 🔧 Orden #{t['id']} - {t['cliente_nombre']}")
    
    c1, c2 = st.columns(2)
    c1.info(f"📱 **{t['marca']} {t['modelo']}**")
    if t['saldo'] > 0: c2.error(f"💰 Debe: S/ {t['saldo']:.2f}")
    else: c2.success("✅ Pagado")

    tab1, tab2, tab3 = st.tabs(["💵 Cobrar", "🖨️ Ticket", "⚠️ Anular"])

    with tab1:
        if t['saldo'] <= 0: st.success("¡Sin deuda pendiente!")
        else:
            monto = st.number_input("Monto a pagar (S/)", 0.0, float(t['saldo']), float(t['saldo']))
            metodo = st.selectbox("Método", ["Efectivo", "Yape", "Plin", "Tarjeta"])
            if st.button("Confirmar Pago", use_container_width=True):
                nuevo_acuenta = t['acuenta'] + monto
                nuevo_saldo = t['precio'] - nuevo_acuenta
                estado = "Entregado" if nuevo_saldo == 0 else "Pendiente"
                supabase.table("tickets").update({"acuenta":nuevo_acuenta, "saldo":nuevo_saldo, "estado":estado, "metodo_pago":metodo}).eq("id", t['id']).execute()
                st.rerun()

    with tab2:
        pdf = generar_ticket_pdf(t)
        st.download_button("Descargar PDF", pdf, f"T_{t['id']}.pdf", "application/pdf", use_container_width=True)
        st.caption(f"Clave: {t['contrasena']}")

    with tab3:
        st.warning("Esta acción es irreversible.")
        if st.button("ANULAR ORDEN", type="primary", use_container_width=True):
            supabase.table("tickets").update({"estado":"Anulado", "saldo":0}).eq("id", t['id']).execute()
            st.rerun()

# --- 6. BARRA LATERAL (MENU PRINCIPAL) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/900/900782.png", width=50)
    st.markdown("### VillaFix OS")
    
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Recepción", "Inventario", "Config"],
        icons=["speedometer2", "tools", "box-seam", "gear"],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#06b6d4", "font-size": "18px"},
            "nav-link": {"font-size": "15px", "text-align": "left", "margin": "5px", "color": "white"},
            "nav-link-selected": {"background-color": "#2563EB"},
        }
    )

# --- 7. LÓGICA DE PÁGINAS ---

# === DASHBOARD ===
if selected == "Dashboard":
    st.markdown("### 📊 Panel de Control")
    try:
        tickets = supabase.table("tickets").select("*").execute().data
        prods = supabase.table("productos").select("id", count="exact").execute().count
    except: tickets = []; prods = 0
    
    hoy = datetime.now().strftime('%Y-%m-%d')
    caja = 0.0
    pendientes = 0
    
    for t in tickets:
        if t['estado'] == 'Pendiente': pendientes += 1
        if t['created_at'].startswith(hoy):
            if t['estado'] == 'Entregado': caja += float(t['precio'])
            elif t['estado'] != 'Anulado': caja += float(t['acuenta'])

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="kpi-card"><div class="kpi-val">S/ {caja:.2f}</div><div class="kpi-lbl">Caja Hoy</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-val">{pendientes}</div><div class="kpi-lbl">En Taller</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-val">{prods}</div><div class="kpi-lbl">Productos</div></div>', unsafe_allow_html=True)

    st.markdown("#### 📈 Actividad Reciente")
    if tickets:
        df_t = pd.DataFrame(tickets)
        df_t['fecha'] = pd.to_datetime(df_t['created_at']).dt.date
        grafico = df_t.groupby('fecha').size().reset_index(name='Tickets')
        st.bar_chart(grafico.set_index('fecha'))

# === RECEPCIÓN (EL NÚCLEO) ===
elif selected == "Recepción":
    tab_form, tab_list = st.tabs(["✨ Nueva Recepción", "📋 Listado de Reparaciones"])

    # PESTAÑA 1: FORMULARIO
    with tab_form:
        st.markdown("#### Datos del Cliente")
        c_sel, x = st.columns([3, 1])
        try: clients = {f"{c['dni']} - {c['nombre']}": c for c in supabase.table("clientes").select("dni,nombre").execute().data}
        except: clients = {}
        sel_cli = c_sel.selectbox("Buscar Cliente", ["Nuevo"] + list(clients.keys()), label_visibility="collapsed")
        
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
            mod = r2.text_input("Modelo"); imei = r3.text_input("IMEI")
            r4, r5, r6 = st.columns(3)
            mot = r4.selectbox("Motivo", ["Reparación", "Mantenimiento", "Garantía"])
            f_ent = r5.date_input("Entrega", date.today()); tec = r6.selectbox("Técnico", ["Admin", "Técnico 1"])
            r7, r8, r9 = st.columns(3)
            cost = r7.number_input("Costo (S/)", 0.0); clav = r8.text_input("Clave")
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

    # PESTAÑA 2: LISTADO AVANZADO (DISEÑO VILLAFIX)
    with tab_list:
        # Barra de Herramientas
        with st.container():
            c_filtro, c_excel = st.columns([4, 1])
            search = c_filtro.text_input("🔍 Buscar...", placeholder="Cliente, DNI o Ticket", label_visibility="collapsed")
            
            q = supabase.table("tickets").select("*").order("created_at", desc=True)
            if search: q = q.ilike("cliente_nombre", f"%{search}%")
            data = q.execute().data
            
            if data:
                excel = to_excel(pd.DataFrame(data))
                c_excel.download_button("📗 Excel", excel, "data.xlsx", use_container_width=True)

        # Encabezado Tabla
        st.markdown("""
        <div class="rep-header">
            <div style="width:50px; text-align:center;">⚙️</div>
            <div style="width:100px; text-align:center;">Estado</div>
            <div class="rep-col">Cliente</div>
            <div class="rep-col">Información</div>
            <div class="rep-col">Técnico</div>
            <div class="rep-col" style="text-align:right;">Monto</div>
            <div class="rep-col" style="text-align:right;">Fechas</div>
        </div>
        """, unsafe_allow_html=True)

        # Filas
        if data:
            for t in data:
                if t['estado'] == 'Anulado': bg = "bg-red"; st_txt = "ANULADO"
                elif t['saldo'] <= 0: bg = "bg-green"; st_txt = "PAGADO"
                else: bg = "bg-blue"; st_txt = "PENDIENTE"

                f_ing = datetime.fromisoformat(t['created_at']).strftime("%d/%m")
                f_ent = t['fecha_entrega'] if t['fecha_entrega'] else "-"

                # Fila Híbrida (Columnas Streamlit + HTML)
                col_btn, col_info = st.columns([0.8, 11])
                
                with col_btn:
                    st.write("") # Espaciado vertical
                    if st.button("⚙️", key=f"btn_{t['id']}", help="Gestionar"):
                        gestion_modal(t)
                
                with col_info:
                    st.markdown(f"""
                    <div class="rep-card">
                        <div style="width:100px; text-align:center; margin-right:10px;">
                            <span class="badge {bg}">{st_txt}</span>
                        </div>
                        <div class="rep-col">
                            <strong>{t['cliente_nombre'].split()[0]}</strong>
                            <span>{t['cliente_dni']}</span>
                        </div>
                        <div class="rep-col">
                            <strong>{t['modelo']}</strong>
                            <span>{t['marca']}</span>
                        </div>
                        <div class="rep-col">
                            <strong>{t['vendedor_nombre']}</strong>
                            <span>Clave: {t['contrasena']}</span>
                        </div>
                        <div class="rep-col" style="text-align:right;">
                            <strong style="color:#ef4444;">S/ {t['saldo']:.2f}</strong>
                            <span>Total: {t['precio']:.2f}</span>
                        </div>
                        <div class="rep-col" style="text-align:right;">
                            <strong>In: {f_ing}</strong>
                            <span>Out: {f_ent}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Sin registros.")

# === INVENTARIO ===
elif selected == "Inventario":
    st.markdown("### 📦 Inventario")
    t1, t2 = st.tabs(["Ver Stock", "Nuevo Producto"])
    
    with t1:
        try: prods = pd.DataFrame(supabase.table("productos").select("*").execute().data)
        except: prods = pd.DataFrame()
        if not prods.empty: st.dataframe(prods[['nombre', 'stock', 'precio']], use_container_width=True)
        else: st.info("Inventario vacío.")
        
    with t2:
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombre"); p = c2.number_input("Precio", 0.0)
        s = c1.number_input("Stock", 1); c = c2.number_input("Costo", 0.0)
        if st.button("Guardar Producto"):
            supabase.table("productos").insert({"nombre":n, "precio":p, "stock":s, "costo":c}).execute()
            st.success("Guardado")

# === CONFIG ===
elif selected == "Config":
    st.write("Configuración del sistema v5.0")
