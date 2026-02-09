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
st.set_page_config(page_title="VillaFix POS", page_icon="💻", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except: st.error("⚠️ Error Conexión DB"); st.stop()

# --- 3. ESTILOS CSS "FIGMA CLONE" ---
st.markdown("""
<style>
    /* FUENTE ESTILO FIGMA */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    .stApp { background-color: #f4f6f9; font-family: 'Roboto', sans-serif; }
    
    /* SIDEBAR OSCURO (GRIS AZULADO) */
    section[data-testid="stSidebar"] { background-color: #343a40; }
    section[data-testid="stSidebar"] h1, h2, h3 { color: white !important; }
    
    /* INPUTS LIMPIOS */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea {
        border: 1px solid #ced4da; border-radius: 4px; height: 38px;
    }
    
    /* --- BOTONES PERSONALIZADOS --- */
    .stButton>button { border-radius: 4px; border: none; font-weight: 500; transition: 0.2s; height: 38px; }
    
    /* Botón Verde (Guardar / Excel / +) */
    .btn-green button { background-color: #28a745 !important; color: white !important; }
    .btn-green button:hover { background-color: #218838 !important; }
    
    /* Botón Rojo (Cerrar / Borrar) */
    .btn-red button { background-color: #dc3545 !important; color: white !important; }
    .btn-red button:hover { background-color: #c82333 !important; }
    
    /* Botón Azul (Primario) */
    .btn-blue button { background-color: #007bff !important; color: white !important; }

    /* --- BARRA TITULO SECCION (GRIS OSCURO) --- */
    .section-header {
        background-color: #5a6268; color: white; padding: 10px 15px;
        font-weight: 500; border-radius: 4px; margin-bottom: 15px;
        text-transform: uppercase; font-size: 0.9rem;
        display: flex; justify-content: space-between; align-items: center;
    }

    /* --- TABLA ESTILO FIGMA --- */
    .rep-header {
        background-color: #6c757d; /* Gris medio */
        color: white; padding: 12px 15px; font-weight: 700; font-size: 0.85rem;
        display: flex; align-items: center; border-radius: 4px 4px 0 0;
    }
    
    .rep-row {
        background-color: white; border: 1px solid #dee2e6; border-top: none;
        padding: 12px 15px; display: flex; align-items: flex-start;
        font-size: 0.85rem; color: #212529; line-height: 1.5;
    }
    .rep-row:nth-child(even) { background-color: #f8f9fa; }
    .rep-row:hover { background-color: #e9ecef; }
    
    .rep-col { flex: 1; padding-right: 10px; }
    
    /* LISTAS DE DATOS (BULLETS) */
    ul.data-list { list-style: none; padding: 0; margin: 0; }
    ul.data-list li { margin-bottom: 3px; display: flex; }
    ul.data-list li::before { content: "•"; color: #6c757d; margin-right: 6px; font-weight: bold; }
    
    /* BADGES */
    .badge { padding: 4px 8px; border-radius: 4px; color: white; font-weight: 700; font-size: 0.75rem; text-transform: uppercase; }
    .bg-blue { background-color: #007bff; }
    .bg-green { background-color: #28a745; }
    .bg-red { background-color: #dc3545; }

    /* TARJETAS DASHBOARD */
    .kpi-card {
        background: white; padding: 15px; border-radius: 4px;
        border-left: 4px solid #17a2b8; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .kpi-num { font-size: 1.5rem; font-weight: 700; color: #343a40; }
    .kpi-txt { font-size: 0.85rem; color: #6c757d; text-transform: uppercase; }
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

def subir_evidencia(archivo):
    try:
        if archivo:
            nombre = f"img_{datetime.now().strftime('%Y%m%d%H%M%S')}_{archivo.name}"
            supabase.storage.from_("evidencias").upload(nombre, archivo.getvalue(), {"content-type": archivo.type})
            return supabase.storage.from_("evidencias").get_public_url(nombre)
    except: return None

def generar_pdf(t):
    width = 80 * mm; height = 297 * mm 
    buffer = io.BytesIO(); c = canvas.Canvas(buffer, pagesize=(width, height))
    c.setFont("Helvetica-Bold", 12); c.drawCentredString(width/2, height-10*mm, "VILLAFIX POS")
    c.setFont("Helvetica", 9); c.drawCentredString(width/2, height-15*mm, f"TICKET #{t['id']}")
    c.drawString(5*mm, height-25*mm, f"Cliente: {t['cliente_nombre']}")
    c.drawString(5*mm, height-30*mm, f"Equipo: {t['marca']} {t['modelo']}")
    c.drawString(5*mm, height-35*mm, f"Total: S/ {t['precio']:.2f}")
    c.showPage(); c.save(); buffer.seek(0); return buffer

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

# --- 5. MODALES (POP-UPS) ---

@st.dialog("Agregar Cliente")
def modal_cliente():
    st.markdown("#### 👤 Nuevo Cliente")
    c1, c2 = st.columns([1, 2])
    c1.selectbox("Tipo Doc", ["DNI", "RUC"])
    
    col_dni, col_btn = c2.columns([3, 1])
    dni = col_dni.text_input("N° Documento", placeholder="DNI", label_visibility="collapsed")
    if col_btn.button("🔍"):
        if n := buscar_reniec(dni): st.session_state.tn = n; st.rerun()
    
    nom = st.text_input("Razón Social / Nombre", value=st.session_state.get('tn', ''))
    c3, c4, c5 = st.columns(3)
    tel = c3.text_input("Teléfono"); mail = c4.text_input("Email"); dire = c5.text_input("Dirección")
    
    st.markdown("---")
    cb, cg = st.columns([1, 4])
    with cb:
        st.markdown('<div class="btn-red">', unsafe_allow_html=True)
        if st.button("Cerrar"): st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with cg:
        st.markdown('<div class="btn-green">', unsafe_allow_html=True)
        if st.button("Guardar", use_container_width=True):
            supabase.table("clientes").upsert({"dni":dni, "nombre":nom, "telefono":tel, "email":mail, "direccion":dire}).execute()
            st.success("Guardado"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("Gestión de Orden")
def modal_gestion(t):
    st.markdown(f"#### ⚙️ Orden #{t['id']}")
    tabs = st.tabs(["💰 Pagar", "📄 Ticket", "🚫 Anular"])
    
    with tabs[0]:
        c1, c2 = st.columns(2)
        c1.metric("Total", f"S/ {t['precio']:.2f}")
        c2.metric("Saldo Pendiente", f"S/ {t['saldo']:.2f}", delta_color="inverse")
        
        if t['saldo'] <= 0: st.success("✅ Orden Pagada")
        else:
            monto = st.number_input("Monto a Pagar", 0.0, float(t['saldo']), float(t['saldo']))
            metodo = st.selectbox("Medio de Pago", ["Efectivo", "Yape", "Plin", "Tarjeta"])
            
            st.markdown('<div class="btn-green">', unsafe_allow_html=True)
            if st.button("Confirmar Pago", use_container_width=True):
                n_acu = t['acuenta'] + monto; n_sal = t['precio'] - n_acu
                est = "Entregado" if n_sal == 0 else "Pendiente"
                supabase.table("tickets").update({"acuenta":n_acu, "saldo":n_sal, "estado":est, "metodo_pago":metodo}).eq("id", t['id']).execute()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        pdf = generar_pdf(t)
        st.download_button("🖨️ Imprimir Ticket", pdf, f"Ticket_{t['id']}.pdf", "application/pdf", use_container_width=True)
        
    with tabs[2]:
        st.markdown('<div class="btn-red">', unsafe_allow_html=True)
        if st.button("ANULAR ORDEN", use_container_width=True):
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

# === RECEPCIÓN (EL MÓDULO ESTRELLA) ===
if menu == "Recepción":
    t1, t2 = st.tabs(["Reparación", "Listado Reparación"])
    
    # 1. FORMULARIO DE INGRESO
    with t1:
        st.markdown('<div class="section-header">Información del Cliente</div>', unsafe_allow_html=True)
        
        # Fila Selector + Botones
        c_sel, c_del, c_add = st.columns([6, 0.5, 0.5])
        with c_sel:
            try: clis = {f"{c['dni']} - {c['nombre']}": c for c in supabase.table("clientes").select("*").execute().data}
            except: clis = {}
            sel = st.selectbox("Seleccione Cliente", ["Seleccionar..."] + list(clis.keys()), label_visibility="collapsed")
        
        with c_del:
            st.markdown('<div class="btn-red">', unsafe_allow_html=True)
            st.button("🗑️", key="del_sel", help="Limpiar")
            st.markdown('</div>', unsafe_allow_html=True)
        with c_add:
            st.markdown('<div class="btn-green">', unsafe_allow_html=True)
            if st.button("➕", key="add_cli", help="Nuevo"): modal_cliente()
            st.markdown('</div>', unsafe_allow_html=True)

        # Datos auto-llenados
        v_dni = clis[sel]['dni'] if sel != "Seleccionar..." else ""
        v_nom = clis[sel]['nombre'] if sel != "Seleccionar..." else ""

        with st.container(border=True):
            r1c1, r1c2, r1c3 = st.columns([3, 2, 2])
            r1c1.text_input("Nombre completos", value=v_nom, disabled=True)
            r1c2.text_input("Documento", value=v_dni, disabled=True)
            r1c3.text_input("Celular")
            r2c1, r2c2 = st.columns(2); r2c1.text_input("Dirección"); r2c2.text_input("Email")

        st.markdown('<div class="section-header">Información de la Recepción</div>', unsafe_allow_html=True)
        with st.container(border=True):
            e1, e2, e3 = st.columns(3)
            mar = e1.selectbox("Marca", ["Samsung", "Apple", "Xiaomi", "Motorola", "Oppo"])
            mod = e2.text_input("Modelo", placeholder="Ej: A54")
            ime = e3.text_input("N° IMEI")
            
            e4, e5, e6 = st.columns(3)
            mot = e4.selectbox("Motivo", ["Reparación", "Garantía", "Mantenimiento"])
            fr = e5.date_input("Fecha Recepción", date.today())
            fe = e6.date_input("Fecha Entrega", date.today())
            
            e7, e8, e9 = st.columns(3)
            cost = e7.number_input("Costo Reparación", 0.0)
            cla = e8.text_input("Clave / Patrón")
            tec = e9.selectbox("Técnico", ["Admin", "Técnico 1"])
            
            obs = st.text_area("Falla / Observaciones")
            foto = st.file_uploader("Evidencia (Foto)", type=['png','jpg'])

        st.write("")
        st.markdown('<div class="btn-blue">', unsafe_allow_html=True)
        if st.button("GENERAR TICKET SERVICIO", use_container_width=True):
            if not v_dni: st.error("Falta Cliente")
            else:
                url = subir_evidencia(foto)
                supabase.table("tickets").insert({
                    "cliente_dni":v_dni, "cliente_nombre":v_nom, "vendedor_nombre":st.session_state.user,
                    "marca":mar, "modelo":mod, "motivo":mot, "falla_reportada":obs,
                    "precio":cost, "acuenta":0, "saldo":cost, "fecha_entrega":str(fe), "estado":"Pendiente",
                    "foto_antes":url
                }).execute()
                st.success("Ticket Generado"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # 2. LISTADO (DISEÑO FIGMA)
    with t2:
        # Barra "Criterios de Búsqueda"
        st.markdown('<div class="section-header">Criterios de Búsqueda</div>', unsafe_allow_html=True)
        
        # Botones Exportar y Buscar
        c_exp, c_sch = st.columns([1, 3])
        with c_exp:
            st.markdown('<div class="btn-green">', unsafe_allow_html=True)
            if st.button("Exportar a Excel 📗", use_container_width=True):
                # Lógica dummy para exportar
                pass 
            st.markdown('</div>', unsafe_allow_html=True)
        
        with c_sch:
            search = st.text_input("Buscar:", placeholder="Cliente, Ticket, DNI...", label_visibility="collapsed")

        # TABLA PERSONALIZADA
        st.markdown("""
        <div style="margin-top:15px;">
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

        # Datos
        q = supabase.table("tickets").select("*").order("created_at", desc=True)
        if search: q = q.ilike("cliente_nombre", f"%{search}%")
        data = q.execute().data

        if data:
            for t in data:
                if t['estado']=='Anulado': bg="bg-red"; stt="ANULADO"
                elif t['saldo']<=0: bg="bg-green"; stt="ENTREGADO"
                else: bg="bg-blue"; stt="RECEPCIONADO"
                
                f_rec = datetime.fromisoformat(t['created_at']).strftime("%Y-%m-%d")
                
                # Fila Renderizada
                c_btn, c_info = st.columns([0.8, 11])
                with c_btn:
                    st.write("")
                    # Botón Engranaje Verde Cuadrado
                    st.markdown('<div class="btn-green">', unsafe_allow_html=True)
                    if st.button("⚙️", key=f"g_{t['id']}"): modal_gestion(t)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with c_info:
                    st.markdown(f"""
                    <div class="rep-row">
                        <div style="width:120px;"><span class="badge {bg}">{stt}</span></div>
                        <div class="rep-col">
                            <ul class="data-list">
                                <li>TR-{t['id']}</li>
                                <li><strong>{t['cliente_nombre'].split()[0]}</strong></li>
                                <li>DNI: {t['cliente_dni']}</li>
                            </ul>
                        </div>
                        <div class="rep-col">
                            <ul class="data-list">
                                <li>{t['motivo']}</li>
                                <li>{t['marca']} - {t['modelo']}</li>
                                <li>Téc: {t['vendedor_nombre']}</li>
                            </ul>
                        </div>
                        <div class="rep-col" style="color:#6c757d;">Sin repuestos</div>
                        <div class="rep-col">
                            <ul class="data-list">
                                <li>Pagado: {t['acuenta']:.2f}</li>
                                <li>Restante: {t['saldo']:.2f}</li>
                                <li><strong>Total: {t['precio']:.2f}</strong></li>
                            </ul>
                        </div>
                        <div class="rep-col">
                            <ul class="data-list">
                                <li>Recepción: {f_rec}</li>
                                <li>Entrega: {t['fecha_entrega']}</li>
                            </ul>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No hay registros.")

# === DASHBOARD (SIMPLIFICADO ESTILO FIGMA) ===
elif menu == "Dashboard":
    st.markdown('<div class="section-header">Panel de Control</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    try: 
        ts = pd.DataFrame(supabase.table("tickets").select("*").execute().data)
        caja = ts['acuenta'].sum()
    except: ts=pd.DataFrame(); caja=0
    
    c1.markdown(f'<div class="kpi-card"><div class="kpi-num">S/ {caja:.2f}</div><div class="kpi-txt">Caja Total</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-num">{len(ts)}</div><div class="kpi-txt">Tickets</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-num">0</div><div class="kpi-txt">Alertas</div></div>', unsafe_allow_html=True)

# === OTROS ===
elif menu == "Ventas": st.title("Módulo Ventas")
elif menu == "Logística": st.title("Módulo Logística")
elif menu == "Clientes": st.title("Módulo Clientes")
