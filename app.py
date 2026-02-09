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

# --- 3. ESTILOS CSS "PIXEL PERFECT" (IGUAL A TUS IMÁGENES) ---
st.markdown("""
<style>
    /* FUENTE */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    .stApp { background-color: #f2f4f8; font-family: 'Roboto', sans-serif; }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] { background-color: #343a40; }
    section[data-testid="stSidebar"] h1, h2, h3, span, p { color: white !important; }
    
    /* INPUTS */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea {
        border: 1px solid #d1d5db; border-radius: 4px; color: #495057; background-color: white; height: 38px;
    }
    label { font-weight: 500; color: #495057; font-size: 0.85rem; }

    /* BOTONES GLOBALES */
    .stButton>button { border-radius: 4px; font-weight: 500; border: none; transition: 0.2s; height: 38px; }
    
    /* CLASES PARA BOTONES PERSONALIZADOS */
    .btn-green button { background-color: #28a745 !important; color: white !important; }
    .btn-green button:hover { background-color: #218838 !important; }
    
    .btn-red button { background-color: #dc3545 !important; color: white !important; }
    .btn-red button:hover { background-color: #c82333 !important; }
    
    .btn-blue button { background-color: #007bff !important; color: white !important; }

    /* --- BARRA TITULO SECCION (GRIS OSCURO) --- */
    .section-title {
        background-color: #5a6268; color: white; padding: 10px 15px;
        font-weight: 500; border-radius: 4px; margin-bottom: 15px;
        text-transform: uppercase; font-size: 0.9rem;
    }

    /* --- TABLA REPARACIÓN (IDÉNTICA A FIGMA) --- */
    .rep-container {
        border: 1px solid #ced4da; border-radius: 4px; overflow: hidden; background: white; margin-top: 10px;
    }
    
    .rep-header {
        background-color: #6c757d; /* Gris Header */
        color: white; padding: 12px 15px; font-weight: 700; font-size: 0.85rem;
        display: flex; align-items: center;
    }
    
    .rep-row {
        background-color: white; border-bottom: 1px solid #e9ecef;
        padding: 15px; display: flex; align-items: flex-start;
        font-size: 0.85rem; color: #212529; line-height: 1.6;
    }
    .rep-row:hover { background-color: #f1f3f5; }
    
    .rep-col { flex: 1; padding: 0 10px; }
    
    /* LISTAS DE DATOS (Bullets) */
    ul.d-list { list-style: none; padding: 0; margin: 0; }
    ul.d-list li { margin-bottom: 2px; display: flex; }
    ul.d-list li::before { content: "•"; color: #6c757d; margin-right: 8px; font-weight: bold; }
    
    /* BOTÓN ENGRANAJE (VERDE CUADRADO) */
    .gear-btn {
        background-color: #28a745; color: white; width: 32px; height: 32px;
        display: flex; align-items: center; justify-content: center;
        border-radius: 4px; cursor: pointer; font-size: 1.1rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1); border: none;
    }
    
    /* BADGE AZUL "RECEPCIONADO" */
    .badge-blue {
        background-color: #007bff; color: white; padding: 4px 10px;
        border-radius: 4px; font-weight: 700; font-size: 0.7rem; text-transform: uppercase;
        display: inline-block;
    }
    .badge-green { background-color: #28a745; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 700; font-size: 0.7rem; }
    .badge-red { background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 700; font-size: 0.7rem; }

    /* MODAL FOOTER */
    .modal-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px; }
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
    c.setFont("Helvetica-Bold", 12); c.drawCentredString(width/2, height-10*mm, "VILLAFIX POS")
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

# A) MODAL AGREGAR CLIENTE (DISEÑO FIGMA: 2 FILAS + FOOTER)
@st.dialog("Agregar Cliente")
def modal_cliente():
    # FILA 1: Tipo | DNI | Nombre
    c1, c2, c3 = st.columns([1, 1.2, 2])
    c1.selectbox("Tipo Documento", ["DNI", "RUC", "CE"])
    
    col_dni, col_btn = c2.columns([3, 1])
    dni = col_dni.text_input("Número Documento", label_visibility="collapsed", placeholder="DNI")
    if col_btn.button("🔍"):
        if n := buscar_reniec(dni): st.session_state.tn = n; st.rerun()
    
    nom = c3.text_input("Razón Social / Nombre", value=st.session_state.get('tn', ''), placeholder="Nombre Completo")

    # FILA 2: Dirección | Teléfono | Email
    c4, c5, c6 = st.columns(3)
    dire = c4.text_input("Dirección")
    telf = c5.text_input("Teléfono")
    email = c6.text_input("Correo Electrónico")

    st.write("") # Separador
    
    # FOOTER: Botones a la derecha
    cf1, cf2, cf3 = st.columns([3, 1, 1])
    with cf2:
        st.markdown('<div class="btn-red">', unsafe_allow_html=True)
        if st.button("Cerrar"): st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with cf3:
        st.markdown('<div class="btn-green">', unsafe_allow_html=True)
        if st.button("Guardar", use_container_width=True):
            if not dni or not nom: st.error("Faltan datos")
            else:
                supabase.table("clientes").upsert({"dni":dni, "nombre":nom, "telefono":telf, "direccion":dire, "email":email}).execute()
                st.success("Guardado"); st.session_state.tn=""; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# B) MODAL GESTIÓN
@st.dialog("Gestión de Orden")
def modal_gestion(t):
    st.markdown(f"#### ⚙️ Orden #{t['id']}")
    tab1, tab2, tab3 = st.tabs(["💰 Pagar", "📄 Ticket", "🚫 Anular"])
    
    with tab1:
        c1, c2 = st.columns(2)
        c1.metric("Total", f"S/ {t['precio']:.2f}")
        c2.metric("Saldo", f"S/ {t['saldo']:.2f}", delta_color="inverse")
        
        monto = st.number_input("Monto a Pagar", 0.0, float(t['saldo']), float(t['saldo']))
        metodo = st.selectbox("Método", ["Efectivo", "Yape", "Plin"])
        
        st.write("")
        st.markdown('<div class="btn-green">', unsafe_allow_html=True)
        if st.button("Realizar Pago", use_container_width=True):
            n_acu = t['acuenta'] + monto; n_sal = t['precio'] - n_acu
            est = "Entregado" if n_sal == 0 else "Pendiente"
            supabase.table("tickets").update({"acuenta":n_acu, "saldo":n_sal, "estado":est, "metodo_pago":metodo}).eq("id", t['id']).execute()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        pdf = generar_pdf(t)
        st.download_button("🖨️ Imprimir", pdf, f"Ticket_{t['id']}.pdf", "application/pdf", use_container_width=True)
        
    with tab3:
        st.markdown('<div class="btn-red">', unsafe_allow_html=True)
        if st.button("ANULAR REPARACIÓN", use_container_width=True):
            supabase.table("tickets").update({"estado":"Anulado", "saldo":0}).eq("id", t['id']).execute(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 6. MENU LATERAL ---
with st.sidebar:
    if os.path.exists("Logo-Mockup.jpg"): st.image("Logo-Mockup.jpg", width=180)
    else: st.markdown("### VillaFix POS")
    
    try: users = [u['nombre'] for u in supabase.table("usuarios").select("nombre").execute().data]
    except: users = ["Admin"]
    st.session_state.user = st.selectbox("Usuario", users)
    
    menu = option_menu(None, ["Dashboard", "Recepción", "Ventas", "Logística", "Clientes"], 
        icons=["speedometer2", "tools", "cart4", "truck", "people"], default_index=1,
        styles={"nav-link-selected": {"background-color": "#007bff"}})

# --- 7. MÓDULOS ---

# === RECEPCIÓN (VISTA IGUAL A FIGMA) ===
if menu == "Recepción":
    t1, t2 = st.tabs(["Reparación", "Listado Reparación"])
    
    # NUEVA REPARACIÓN
    with t1:
        st.markdown('<div class="section-title">Información del Cliente</div>', unsafe_allow_html=True)
        
        # Fila Cliente + Botones
        c_sel, c_del, c_add = st.columns([6, 0.5, 0.5])
        with c_sel:
            try: clis = {f"{c['dni']} - {c['nombre']}": c for c in supabase.table("clientes").select("*").execute().data}
            except: clis = {}
            sel = st.selectbox("Seleccione Cliente", ["Seleccionar..."] + list(clis.keys()), label_visibility="collapsed")
        
        with c_del:
            st.markdown('<div class="btn-red">', unsafe_allow_html=True)
            st.button("🗑️", key="del")
            st.markdown('</div>', unsafe_allow_html=True)
        with c_add:
            st.markdown('<div class="btn-green">', unsafe_allow_html=True)
            if st.button("➕", key="add"): modal_cliente()
            st.markdown('</div>', unsafe_allow_html=True)

        d_dni = clis[sel]['dni'] if sel != "Seleccionar..." else ""
        d_nom = clis[sel]['nombre'] if sel != "Seleccionar..." else ""

        with st.container(border=True):
            r1c1, r1c2, r1c3 = st.columns([3, 2, 2])
            r1c1.text_input("Nombre completos", value=d_nom, disabled=True)
            r1c2.text_input("Documento", value=d_dni, disabled=True)
            r1c3.text_input("Celular")
            r2c1, r2c2 = st.columns(2); r2c1.text_input("Dirección"); r2c2.text_input("Email")

        st.markdown('<div class="section-title">Información de la Recepción</div>', unsafe_allow_html=True)
        with st.container(border=True):
            e1, e2, e3 = st.columns(3)
            mar = e1.selectbox("Marca", ["Samsung", "Apple", "Xiaomi", "Motorola", "Honor"])
            mod = e2.text_input("Modelo", placeholder="Ej: Redmi Note 10")
            ime = e3.text_input("N° IMEI")
            
            e4, e5, e6 = st.columns(3)
            mot = e4.selectbox("Motivo", ["Reparación", "Garantía", "Mantenimiento"])
            fr = e5.date_input("Fecha Recepción", date.today())
            fe = e6.date_input("Fecha Posible Entrega", date.today())
            
            e7, e8, e9 = st.columns(3)
            cost = e7.number_input("Costo Reparación", 0.0)
            cla = e8.text_input("Contraseña / PIN")
            tec = e9.selectbox("Técnico", ["Admin", "Técnico 1"])
            
            obs = st.text_area("Detalle / Fallas / Observaciones")
            foto = st.file_uploader("Evidencia", type=['png','jpg'])

        st.write("")
        st.markdown('<div class="btn-blue">', unsafe_allow_html=True)
        if st.button("GENERAR TICKET SERVICIO", use_container_width=True):
            if not d_dni: st.error("Falta Cliente")
            else:
                url = subir_evidencia(foto)
                supabase.table("tickets").insert({
                    "cliente_dni":d_dni, "cliente_nombre":d_nom, "vendedor_nombre":st.session_state.user,
                    "marca":mar, "modelo":mod, "motivo":mot, "falla_reportada":obs,
                    "precio":cost, "acuenta":0, "saldo":cost, "fecha_entrega":str(fe), "estado":"Pendiente",
                    "foto_antes":url
                }).execute()
                st.success("Ticket Generado"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # LISTADO (REPLICA VISUAL)
    with t2:
        st.markdown('<div class="section-title">CRITERIOS DE BÚSQUEDA</div>', unsafe_allow_html=True)
        
        c_exp, c_sch = st.columns([1, 3])
        with c_exp:
            st.markdown('<div class="btn-green">', unsafe_allow_html=True)
            if st.button("Exportar a Excel 📗", use_container_width=True):
                pass # Lógica exportar
            st.markdown('</div>', unsafe_allow_html=True)
        with c_sch:
            search = st.text_input("Buscar:", placeholder="", label_visibility="collapsed")

        # TABLA HEADER
        st.markdown("""
        <div class="rep-container">
            <div class="rep-header">
                <div style="width:60px; text-align:center;">⚙️</div>
                <div style="width:120px;">Estado</div>
                <div class="rep-col">Cliente</div>
                <div class="rep-col">Información</div>
                <div class="rep-col">Repuestos</div>
                <div class="rep-col">Montos</div>
                <div class="rep-col">Fechas</div>
            </div>
        """, unsafe_allow_html=True)

        # TABLA DATA
        q = supabase.table("tickets").select("*").order("created_at", desc=True)
        if search: q = q.ilike("cliente_nombre", f"%{search}%")
        data = q.execute().data

        if data:
            for t in data:
                if t['estado']=='Anulado': bg="badge-red"; stt="ANULADO"
                elif t['saldo']<=0: bg="badge-green"; stt="ENTREGADO"
                else: bg="badge-blue"; stt="RECEPCIONADO"
                
                f_rec = datetime.fromisoformat(t['created_at']).strftime("%Y-%m-%d")
                nom_cli = t['cliente_nombre'] if t['cliente_nombre'] else "Sin Nombre"
                
                # Render Fila
                c_btn, c_info = st.columns([0.8, 11])
                with c_btn:
                    st.write("")
                    st.markdown('<div class="btn-green">', unsafe_allow_html=True)
                    if st.button("⚙️", key=f"g_{t['id']}"): modal_gestion(t)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with c_info:
                    st.markdown(f"""
                    <div class="rep-row">
                        <div style="width:120px;"><span class="{bg} badge">{stt}</span></div>
                        <div class="rep-col">
                            <ul class="d-list">
                                <li>TR-{t['id']}</li>
                                <li><strong>{nom_cli.split()[0]}</strong></li>
                                <li>DNI: {t['cliente_dni']}</li>
                            </ul>
                        </div>
                        <div class="rep-col">
                            <ul class="d-list">
                                <li>{t['motivo']}</li>
                                <li>{t['marca']} - {t['modelo']}</li>
                                <li>Téc: {t['vendedor_nombre']}</li>
                            </ul>
                        </div>
                        <div class="rep-col" style="color:#6c757d;">Sin repuestos</div>
                        <div class="rep-col">
                            <ul class="d-list">
                                <li>Pagado: {t['acuenta']:.2f}</li>
                                <li>Restante: {t['saldo']:.2f}</li>
                                <li><strong>Total: {t['precio']:.2f}</strong></li>
                            </ul>
                        </div>
                        <div class="rep-col">
                            <ul class="d-list">
                                <li>Recepción: {f_rec}</li>
                                <li>Entrega: {t['fecha_entrega']}</li>
                            </ul>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True) # Cierre container
        else:
            st.info("No hay registros que coincidan.")

# (Otros módulos simplificados)
elif menu == "Dashboard": st.title("Panel de Control")
elif menu == "Ventas": st.title("Punto de Venta")
elif menu == "Logística": st.title("Logística")
elif menu == "Clientes": st.title("Clientes")
