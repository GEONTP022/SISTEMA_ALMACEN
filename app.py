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
import xlsxwriter
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="VillaFix POS",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except:
    st.error("⚠️ Configura los secrets de Supabase.")
    st.stop()

# --- 3. ESTILOS CSS "HIGH FIDELITY" (ESTILO FIGMA REAL) ---
st.markdown("""
<style>
    /* FUENTE: Inter (La estándar en UI moderna) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* SIDEBAR: Oscuro Profundo (Slate-900) */
    section[data-testid="stSidebar"] { background-color: #0f172a; }
    section[data-testid="stSidebar"] h1, h2, h3, p, span { color: #f1f5f9 !important; }
    
    /* INPUTS: Diseño Clean */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea {
        border: 1px solid #cbd5e1; 
        border-radius: 6px; 
        color: #334155; 
        background-color: white; 
        height: 40px;
        font-size: 0.9rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .stTextInput>div>div>input:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.2); }
    
    label { font-weight: 600; color: #475569; font-size: 0.85rem; margin-bottom: 6px; }

    /* BOTONES: Sistema de Diseño */
    .stButton>button { 
        border-radius: 6px; 
        font-weight: 600; 
        border: none; 
        transition: all 0.2s; 
        height: 40px; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    /* Verde (Acción Principal/Excel) */
    .btn-green button { background-color: #10b981 !important; color: white !important; }
    .btn-green button:hover { background-color: #059669 !important; transform: translateY(-1px); }
    
    /* Rojo (Peligro/Cerrar) */
    .btn-red button { background-color: #ef4444 !important; color: white !important; }
    .btn-red button:hover { background-color: #dc2626 !important; }
    
    /* Azul (Primario) */
    .btn-blue button { background-color: #3b82f6 !important; color: white !important; }
    
    /* --- COMPONENTES UI PERSONALIZADOS --- */
    
    /* Barra de Título de Sección (Gris Oscuro Sólido) */
    .ui-header {
        background-color: #475569; 
        color: white; 
        padding: 12px 20px; 
        border-radius: 6px; 
        margin-bottom: 20px;
        font-weight: 600; 
        font-size: 0.9rem;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        display: flex; 
        align-items: center; 
        justify-content: space-between;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    /* Tabla de Datos (Estilo Dashboard) */
    .ui-table-container {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-top: 15px;
    }
    
    .ui-table-header {
        background-color: #f1f5f9;
        color: #475569;
        padding: 12px 16px;
        font-weight: 700;
        font-size: 0.8rem;
        text-transform: uppercase;
        border-bottom: 2px solid #e2e8f0;
        display: flex;
        align-items: center;
    }
    
    .ui-table-row {
        background-color: white;
        border-bottom: 1px solid #f1f5f9;
        padding: 16px;
        display: flex;
        align-items: flex-start; /* Alineación superior para listas */
        font-size: 0.9rem;
        color: #334155;
        transition: background 0.1s;
    }
    .ui-table-row:last-child { border-bottom: none; }
    .ui-table-row:hover { background-color: #f8fafc; }
    
    .col-flex { flex: 1; padding: 0 12px; }
    
    /* Listas dentro de la tabla */
    ul.ui-list { list-style: none; padding: 0; margin: 0; }
    ul.ui-list li { margin-bottom: 4px; display: flex; align-items: center; }
    ul.ui-list li::before { 
        content: ""; 
        width: 6px; height: 6px; 
        background-color: #94a3b8; 
        border-radius: 50%; 
        margin-right: 8px; 
    }
    
    /* Badges (Etiquetas) */
    .ui-badge { 
        padding: 4px 10px; 
        border-radius: 99px; 
        font-size: 0.7rem; 
        font-weight: 700; 
        text-transform: uppercase; 
        display: inline-block;
        min-width: 90px;
        text-align: center;
    }
    .badge-blue { background-color: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }
    .badge-green { background-color: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
    .badge-red { background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }

</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES ---
def buscar_reniec(dni):
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd"
    try:
        r = requests.get(f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}", headers={'Authorization': f'Bearer {token}'}, timeout=3)
        if r.status_code == 200: 
            d = r.json(); return f"{d.get('nombres','')} {d.get('apellidoPaterno','')} {d.get('apellidoMaterno','')}".strip()
    except: pass
    return None

def generar_pdf(t):
    width = 80 * mm; height = 297 * mm 
    buffer = io.BytesIO(); c = canvas.Canvas(buffer, pagesize=(width, height))
    c.setFont("Helvetica-Bold", 12); c.drawCentredString(width/2, height-10*mm, "VILLAFIX OS")
    c.setFont("Helvetica", 9); c.drawCentredString(width/2, height-15*mm, f"TICKET #{t['id']}")
    c.drawString(5*mm, height-25*mm, f"Cliente: {t['cliente_nombre']}")
    c.drawString(5*mm, height-30*mm, f"Equipo: {t['marca']} {t['modelo']}")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(5*mm, height-40*mm, f"TOTAL: S/ {t['precio']:.2f}")
    c.showPage(); c.save(); buffer.seek(0); return buffer

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

def subir_evidencia(archivo):
    try:
        if archivo:
            nombre = f"img_{datetime.now().strftime('%Y%m%d%H%M%S')}_{archivo.name}"
            supabase.storage.from_("evidencias").upload(nombre, archivo.getvalue(), {"content-type": archivo.type})
            return supabase.storage.from_("evidencias").get_public_url(nombre)
    except: return None

# --- 5. MODALES ---

@st.dialog("Nuevo Cliente")
def modal_cliente():
    st.markdown("##### 👤 Datos Personales")
    c1, c2 = st.columns([1, 1.5])
    c1.selectbox("Tipo Doc", ["DNI", "RUC"])
    
    col_dni, col_btn = c2.columns([3, 1])
    dni = col_dni.text_input("N° Documento", placeholder="Ingrese DNI", label_visibility="collapsed")
    if col_btn.button("🔍"):
        if n := buscar_reniec(dni): st.session_state.tn = n; st.rerun()
    
    nom = st.text_input("Nombre Completo", value=st.session_state.get('tn', ''))
    
    st.markdown("##### 📍 Contacto")
    c3, c4 = st.columns(2)
    tel = c3.text_input("Teléfono"); mail = c4.text_input("Email")
    dir = st.text_input("Dirección")
    
    st.markdown("---")
    cf1, cf2 = st.columns([1, 3])
    with cf1:
        st.markdown('<div class="btn-red">', unsafe_allow_html=True)
        if st.button("Cancelar"): st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with cf2:
        st.markdown('<div class="btn-green">', unsafe_allow_html=True)
        if st.button("Guardar Cliente", use_container_width=True):
            supabase.table("clientes").upsert({"dni":dni, "nombre":nom, "telefono":tel, "email":mail, "direccion":dir}).execute()
            st.success("Guardado"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("Detalle de Orden")
def modal_gestion(t):
    st.markdown(f"#### ⚙️ Orden #{t['id']} | {t['cliente_nombre']}")
    
    tabs = st.tabs(["💰 Pagos", "📄 Comprobante", "🛠️ Acciones"])
    
    with tabs[0]:
        c1, c2 = st.columns(2)
        c1.metric("Total", f"S/ {t['precio']:.2f}")
        c2.metric("Pendiente", f"S/ {t['saldo']:.2f}", delta_color="inverse")
        
        if t['saldo'] > 0:
            monto = st.number_input("Monto a cobrar", 0.0, float(t['saldo']), float(t['saldo']))
            metodo = st.selectbox("Método de Pago", ["Efectivo", "Yape", "Plin"])
            
            st.markdown('<div class="btn-green">', unsafe_allow_html=True)
            if st.button("Registrar Pago", use_container_width=True):
                n_acu = t['acuenta'] + monto; n_sal = t['precio'] - n_acu
                est = "Entregado" if n_sal == 0 else "Pendiente"
                supabase.table("tickets").update({"acuenta":n_acu, "saldo":n_sal, "estado":est, "metodo_pago":metodo}).eq("id", t['id']).execute()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.success("Esta orden está totalmente pagada.")

    with tabs[1]:
        pdf = generar_pdf(t)
        st.download_button("🖨️ Imprimir Ticket", pdf, f"Ticket_{t['id']}.pdf", "application/pdf", use_container_width=True)
        if t['foto_antes']: st.image(t['foto_antes'], caption="Evidencia Entrada")

    with tabs[2]:
        st.markdown('<div class="btn-red">', unsafe_allow_html=True)
        if st.button("🚫 ANULAR ORDEN (Irreversible)", use_container_width=True):
            supabase.table("tickets").update({"estado":"Anulado", "saldo":0}).eq("id", t['id']).execute(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 6. MENU LATERAL ---
with st.sidebar:
    if os.path.exists("Logo-Mockup.jpg"): st.image("Logo-Mockup.jpg", width=180)
    else: st.markdown("## VillaFix OS")
    
    try: users = [u['nombre'] for u in supabase.table("usuarios").select("nombre").execute().data]
    except: users = ["Admin"]
    st.session_state.user = st.selectbox("Usuario", users)
    
    menu = option_menu(None, ["Dashboard", "Recepción", "Ventas", "Logística", "Clientes"], 
        icons=["grid", "phone", "cart", "truck", "people"], default_index=1,
        styles={
            "nav-link": {"font-family": "Inter", "font-size": "15px", "text-align": "left", "margin": "5px", "color": "white"},
            "nav-link-selected": {"background-color": "#3b82f6"}
        })

# --- 7. MÓDULOS ---

# === RECEPCIÓN (UI FINAMENTE DETALLADA) ===
if menu == "Recepción":
    t1, t2 = st.tabs(["Reparación", "Listado Reparación"])
    
    # NUEVA REPARACIÓN
    with t1:
        st.markdown('<div class="ui-header">Información del Cliente</div>', unsafe_allow_html=True)
        
        # Selector inteligente + Botones
        c_sel, c_del, c_add = st.columns([6, 0.5, 0.5])
        with c_sel:
            try: clis = {f"{c['dni']} - {c['nombre']}": c for c in supabase.table("clientes").select("*").execute().data}
            except: clis = {}
            sel = st.selectbox("Buscar Cliente", ["Seleccionar..."] + list(clis.keys()), label_visibility="collapsed")
        
        with c_del:
            st.markdown('<div class="btn-red">', unsafe_allow_html=True)
            st.button("✕", key="del", help="Limpiar selección")
            st.markdown('</div>', unsafe_allow_html=True)
        with c_add:
            st.markdown('<div class="btn-green">', unsafe_allow_html=True)
            if st.button("＋", key="add", help="Nuevo Cliente"): modal_cliente()
            st.markdown('</div>', unsafe_allow_html=True)

        d_dni = clis[sel]['dni'] if sel != "Seleccionar..." else ""
        d_nom = clis[sel]['nombre'] if sel != "Seleccionar..." else ""

        with st.container():
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.text_input("Nombre", value=d_nom, disabled=True)
            c2.text_input("DNI", value=d_dni, disabled=True)
            c3.text_input("Celular")
            
            c4, c5 = st.columns(2)
            c4.text_input("Dirección"); c5.text_input("Email")

        st.markdown('<div class="ui-header">Datos del Equipo</div>', unsafe_allow_html=True)
        with st.container():
            e1, e2, e3 = st.columns(3)
            mar = e1.selectbox("Marca", ["Samsung", "Apple", "Xiaomi", "Motorola", "Honor", "Otro"])
            mod = e2.text_input("Modelo")
            ime = e3.text_input("IMEI / Serie")
            
            e4, e5, e6 = st.columns(3)
            mot = e4.selectbox("Motivo", ["Reparación", "Garantía", "Mantenimiento", "Software"])
            fr = e5.date_input("Recepción", date.today())
            fe = e6.date_input("Entrega Aprox", date.today())
            
            e7, e8, e9 = st.columns(3)
            cost = e7.number_input("Costo (S/)", 0.0)
            cla = e8.text_input("Patrón / Clave")
            tec = e9.selectbox("Técnico", ["Admin", "Técnico 1"])
            
            obs = st.text_area("Diagnóstico / Falla")
            foto = st.file_uploader("Subir Evidencia (Foto)", type=['jpg','png'])

        st.write("")
        st.markdown('<div class="btn-blue">', unsafe_allow_html=True)
        if st.button("GENERAR ORDEN DE SERVICIO", use_container_width=True):
            if not d_dni: st.error("⚠️ Debe seleccionar un cliente primero.")
            else:
                url = subir_evidencia(foto)
                supabase.table("tickets").insert({
                    "cliente_dni":d_dni, "cliente_nombre":d_nom, "vendedor_nombre":st.session_state.user,
                    "marca":mar, "modelo":mod, "motivo":mot, "falla_reportada":obs,
                    "precio":cost, "acuenta":0, "saldo":cost, "fecha_entrega":str(fe), "estado":"Pendiente",
                    "foto_antes":url
                }).execute()
                st.success("✅ Orden registrada correctamente"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # LISTADO (DISEÑO FIGMA TABLE)
    with t2:
        st.markdown('<div class="ui-header">Criterios de Búsqueda</div>', unsafe_allow_html=True)
        
        c_exp, c_sch = st.columns([1, 3])
        with c_exp:
            st.markdown('<div class="btn-green">', unsafe_allow_html=True)
            if st.button("Excel 📗", use_container_width=True): pass
            st.markdown('</div>', unsafe_allow_html=True)
        with c_sch:
            search = st.text_input("Buscar:", placeholder="Buscar por Cliente o DNI...", label_visibility="collapsed")

        # TABLA HTML/CSS
        st.markdown("""
        <div class="ui-table-container">
            <div class="ui-table-header">
                <div style="width:60px; text-align:center;">⚙️</div>
                <div style="width:110px; text-align:center;">Estado</div>
                <div class="col-flex" style="flex:1.5;">Cliente</div>
                <div class="col-flex" style="flex:1.5;">Equipo</div>
                <div class="col-flex">Repuestos</div>
                <div class="col-flex" style="text-align:right;">Montos</div>
                <div class="col-flex" style="text-align:right;">Fechas</div>
            </div>
        """, unsafe_allow_html=True)

        q = supabase.table("tickets").select("*").order("created_at", desc=True)
        if search: q = q.ilike("cliente_nombre", f"%{search}%")
        data = q.execute().data

        if data:
            for t in data:
                # Estilos Badge
                if t['estado']=='Anulado': bg="badge-red"; txt="ANULADO"
                elif t['saldo']<=0: bg="badge-green"; txt="ENTREGADO"
                else: bg="badge-blue"; txt="RECEPCIONADO"
                
                f_rec = datetime.fromisoformat(t['created_at']).strftime("%d/%m/%Y")
                nom = t['cliente_nombre'].split()[0] if t['cliente_nombre'] else "General"
                
                # Botón de Acción
                c_btn, c_info = st.columns([0.8, 11])
                with c_btn:
                    st.write("")
                    st.markdown('<div class="btn-green">', unsafe_allow_html=True)
                    if st.button("⚙️", key=f"act_{t['id']}"): modal_gestion(t)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with c_info:
                    st.markdown(f"""
                    <div class="ui-table-row">
                        <div style="width:110px; text-align:center;"><span class="ui-badge {bg}">{txt}</span></div>
                        <div class="col-flex" style="flex:1.5;">
                            <ul class="ui-list">
                                <li><strong>{nom}</strong></li>
                                <li>{t['cliente_dni']}</li>
                            </ul>
                        </div>
                        <div class="col-flex" style="flex:1.5;">
                            <ul class="ui-list">
                                <li>{t['marca']} - {t['modelo']}</li>
                                <li>{t['motivo']}</li>
                            </ul>
                        </div>
                        <div class="col-flex" style="color:#64748b;">N/A</div>
                        <div class="col-flex" style="text-align:right;">
                            <ul class="ui-list" style="justify-content: flex-end; display:block;">
                                <li>Pagado: {t['acuenta']:.2f}</li>
                                <li><strong>Saldo: {t['saldo']:.2f}</strong></li>
                            </ul>
                        </div>
                        <div class="col-flex" style="text-align:right;">
                            <ul class="ui-list" style="justify-content: flex-end; display:block;">
                                <li>In: {f_rec}</li>
                                <li>Out: {t['fecha_entrega']}</li>
                            </ul>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True) # Fin Container
        else:
            st.info("No se encontraron registros.")

# === OTROS MÓDULOS (SIMPLIFICADOS) ===
elif menu == "Dashboard": st.title("Dashboard")
elif menu == "Ventas": st.title("Ventas")
elif menu == "Logística": st.title("Logística")
elif menu == "Clientes": st.title("Clientes")
