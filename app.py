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
st.set_page_config(page_title="VillaFix ERP", page_icon="🔧", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except: st.error("⚠️ Error Conexión DB"); st.stop()

# --- 3. ESTILOS CSS "PIXEL PERFECT" (IGUAL A TUS IMÁGENES) ---
st.markdown("""
<style>
    /* FUENTE */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    .stApp { background-color: #f8f9fa; font-family: 'Roboto', sans-serif; }
    
    /* SIDEBAR OSCURO */
    section[data-testid="stSidebar"] { background-color: #343a40; }
    section[data-testid="stSidebar"] h1, h2, h3 { color: white !important; }
    
    /* INPUTS (Bordes suaves) */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea {
        border: 1px solid #ced4da; border-radius: 4px; color: #495057; font-size: 0.9rem;
    }
    label { font-weight: 500; color: #495057; font-size: 0.85rem; }

    /* BOTONES */
    .stButton>button { border-radius: 4px; font-weight: 500; border: none; transition: 0.2s; }
    
    /* Botón Principal (Guardar/Generar) - Azul/Morado del sistema */
    .btn-primary button { background-color: #6f42c1 !important; color: white !important; }
    
    /* Botón Excel (Verde) */
    .btn-excel button { background-color: #28a745 !important; color: white !important; height: 35px; }
    
    /* Botones Pequeños (Iconos Formulario) */
    .btn-icon-red button { background-color: #dc3545 !important; color: white !important; width: 40px; }
    .btn-icon-green button { background-color: #28a745 !important; color: white !important; width: 40px; }

    /* --- BARRA "CRITERIOS DE BÚSQUEDA" --- */
    .search-bar {
        background-color: #5a6268; color: white; padding: 10px 15px; border-radius: 4px;
        font-weight: 500; text-transform: uppercase; font-size: 0.9rem; margin-bottom: 10px;
        display: flex; justify-content: space-between; align-items: center;
    }

    /* --- TABLA EXACTA A LA IMAGEN --- */
    .rep-header {
        background-color: #5a6268; /* Gris oscuro exacto */
        color: white; padding: 12px 15px; font-weight: 700; font-size: 0.85rem;
        display: flex; align-items: center;
    }
    
    .rep-row {
        background-color: white; border-bottom: 1px solid #dee2e6;
        padding: 15px; display: flex; align-items: flex-start;
        font-size: 0.85rem; color: #212529;
    }
    .rep-row:nth-child(even) { background-color: #f2f2f2; } /* Zebra */
    
    .rep-col { flex: 1; padding: 0 10px; line-height: 1.5; }
    
    /* LISTAS DENTRO DE LA TABLA (Bullet Points) */
    .info-list { list-style: none; padding: 0; margin: 0; }
    .info-list li { margin-bottom: 2px; display: flex; }
    .info-list li::before { content: "•"; color: #6c757d; margin-right: 5px; font-weight: bold; }
    
    /* BOTÓN ENGRANAJE CUADRADO */
    .gear-btn {
        background-color: #28a745; color: white; width: 32px; height: 32px;
        display: flex; align-items: center; justify-content: center;
        border-radius: 3px; cursor: pointer; font-size: 1.1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); border: none;
    }
    
    /* BADGE AZUL "RECEPCIONADO" */
    .badge-blue {
        background-color: #007bff; color: white; padding: 3px 8px;
        border-radius: 4px; font-weight: 700; font-size: 0.7rem; text-transform: uppercase;
    }
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
    c.drawString(5*mm, height-35*mm, f"Total: S/ {t['precio']:.2f}")
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

@st.dialog("Agregar Cliente")
def modal_cliente():
    st.markdown("#### 👤 Nuevo Cliente")
    c1, c2 = st.columns([1, 2])
    c1.selectbox("Tipo Doc", ["DNI", "RUC"])
    
    dni_col = c2.columns([3, 1])
    dni = dni_col[0].text_input("Número", label_visibility="collapsed", placeholder="DNI")
    if dni_col[1].button("🔍"):
        if n := buscar_reniec(dni): st.session_state.tn = n; st.rerun()
    
    nom = st.text_input("Nombre / Razón Social", value=st.session_state.get('tn', ''))
    c3, c4 = st.columns(2)
    tel = c3.text_input("Teléfono"); mail = c4.text_input("Email")
    dir = st.text_input("Dirección")
    
    if st.button("Guardar", type="primary", use_container_width=True):
        supabase.table("clientes").upsert({"dni":dni, "nombre":nom, "telefono":tel, "email":mail, "direccion":dir}).execute()
        st.success("Guardado"); st.rerun()

@st.dialog("Gestión de Reparación")
def modal_gestion(t):
    st.markdown(f"#### 🔧 {t['marca']} {t['modelo']}")
    tabs = st.tabs(["💰 Pagar", "📄 Ticket", "🚫 Anular"])
    
    with tabs[0]:
        c1, c2 = st.columns(2)
        c1.metric("Total", f"S/ {t['precio']:.2f}")
        c2.metric("Saldo", f"S/ {t['saldo']:.2f}", delta_color="inverse")
        monto = st.number_input("Monto a Pagar", 0.0, float(t['saldo']), float(t['saldo']))
        if st.button("Confirmar Pago", use_container_width=True):
            n_acu = t['acuenta'] + monto; n_sal = t['precio'] - n_acu
            est = "Entregado" if n_sal == 0 else "Pendiente"
            supabase.table("tickets").update({"acuenta":n_acu, "saldo":n_sal, "estado":est}).eq("id", t['id']).execute()
            st.rerun()

    with tabs[2]:
        if st.button("ANULAR", type="primary"):
            supabase.table("tickets").update({"estado":"Anulado"}).eq("id", t['id']).execute(); st.rerun()

# --- 6. MENU LATERAL ---
with st.sidebar:
    if os.path.exists("Logo-Mockup.jpg"): st.image("Logo-Mockup.jpg", width=180)
    else: st.markdown("### VillaFix ERP")
    
    try: users = [u['nombre'] for u in supabase.table("usuarios").select("nombre").execute().data]
    except: users = ["Admin"]
    st.session_state.user = st.selectbox("Usuario", users)
    
    menu = option_menu(None, ["Dashboard", "Recepción", "Ventas", "Logística", "Clientes"], 
        icons=["speedometer2", "tools", "cart4", "truck", "people"], default_index=1,
        styles={"nav-link-selected": {"background-color": "#007bff"}})

# --- 7. MÓDULO RECEPCIÓN (REPLICA EXACTA) ---
if menu == "Recepción":
    t1, t2 = st.tabs(["Reparación", "Listado Reparación"]) # Nombres exactos imagen
    
    # --- PESTAÑA 1: FORMULARIO (Diseño image_92f3dd.png) ---
    with t1:
        st.subheader("📝 Información del cliente")
        
        # Fila Selector + Botones Rojo/Verde
        c_sel, c_del, c_add = st.columns([6, 0.5, 0.5])
        with c_sel:
            try: clis = {f"{c['dni']} - {c['nombre']}": c for c in supabase.table("clientes").select("*").execute().data}
            except: clis = {}
            sel = st.selectbox("Seleccione Cliente", ["Seleccionar..."] + list(clis.keys()), label_visibility="collapsed")
        
        with c_del:
            st.markdown('<div class="btn-icon-red">', unsafe_allow_html=True)
            st.button("🗑️", key="clean")
            st.markdown('</div>', unsafe_allow_html=True)
        with c_add:
            st.markdown('<div class="btn-icon-green">', unsafe_allow_html=True)
            if st.button("➕", key="add_cli"): modal_cliente()
            st.markdown('</div>', unsafe_allow_html=True)

        # Campos Auto-rellenables
        d_dni = clis[sel]['dni'] if sel != "Seleccionar..." else ""
        d_nom = clis[sel]['nombre'] if sel != "Seleccionar..." else ""
        
        with st.container(border=True):
            r1c1, r1c2, r1c3 = st.columns([3, 2, 2])
            r1c1.text_input("Nombre completos", value=d_nom, disabled=True)
            r1c2.text_input("Documento", value=d_dni, disabled=True)
            r1c3.text_input("Celular")
            r2c1, r2c2 = st.columns(2)
            r2c1.text_input("Dirección"); r2c2.text_input("Email")

        st.subheader("Informacion de la recepción")
        with st.container(border=True):
            e1, e2, e3 = st.columns(3)
            mar = e1.selectbox("Marca", ["Samsung", "Apple", "Xiaomi", "Motorola", "Otro"])
            mod = e2.text_input("Modelo", placeholder="Ejm: iPhone 13 Pro")
            ime = e3.text_input("N° IMEI")
            
            e4, e5, e6 = st.columns(3)
            mot = e4.selectbox("Motivo", ["Reparación", "Mantenimiento", "Garantía"])
            fr = e5.date_input("Fecha Recepción", date.today())
            fe = e6.date_input("Fecha Posible Entrega", date.today())
            
            e7, e8, e9 = st.columns(3)
            cost = e7.number_input("Costo Reparación", 0.0)
            cla = e8.text_input("Contraseña / PIN")
            tec = e9.selectbox("Técnico Responsable", ["Admin", "Técnico 1"])
            
            obs = st.text_area("Detalle / Fallas / Observaciones")
            foto = st.file_uploader("Evidencia", type=['png','jpg'])

        st.write("")
        st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
        if st.button("GENERAR TICKET SERVICIO", use_container_width=False):
            if not d_dni: st.error("Seleccione un cliente válido")
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

    # --- PESTAÑA 2: LISTADO (Diseño image_92fe44.png) ---
    with t2:
        st.markdown("#### 📋 Listado de recepción")
        
        # Barra "CRITERIOS DE BÚSQUEDA"
        st.markdown('<div class="search-bar">CRITERIOS DE BÚSQUEDA <span style="float:right">+</span></div>', unsafe_allow_html=True)
        
        # Botón Excel y Buscador
        c_act, c_sch = st.columns([1, 3])
        with c_act:
            st.markdown('<div class="btn-excel">', unsafe_allow_html=True)
            # Generar Excel
            q = supabase.table("tickets").select("*").order("created_at", desc=True)
            data = q.execute().data
            if data:
                exc = to_excel(pd.DataFrame(data))
                st.download_button("Exportar a Excel 📗", exc, "reporte.xlsx")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with c_sch:
            search = st.text_input("Buscar:", placeholder="", label_visibility="collapsed")
            if search: 
                # Filtrado simple en memoria para rapidez
                data = [d for d in data if search.lower() in str(d).lower()]

        st.write("") # Espacio

        # CABECERA TABLA
        st.markdown("""
        <div class="rep-header">
            <div style="width:50px;"></div>
            <div style="width:120px;">Estado</div>
            <div style="flex:1;">Cliente</div>
            <div style="flex:1;">Información</div>
            <div style="flex:1;">Repuestos</div>
            <div style="flex:1;">Montos</div>
            <div style="flex:1;">Fechas</div>
        </div>
        """, unsafe_allow_html=True)

        # FILAS
        if data:
            for t in data:
                # Lógica visual
                if t['estado']=='Anulado': badge="bg-red"; stt="ANULADO"
                elif t['saldo']<=0: badge="bg-green"; stt="ENTREGADO"
                else: badge="badge-blue"; stt="Recepcionado" # Azul como imagen
                
                f_rec = datetime.fromisoformat(t['created_at']).strftime("%Y-%m-%d")
                
                # Validar nombre para evitar error
                nom_cli = t['cliente_nombre'] if t['cliente_nombre'] else "Sin Nombre"
                
                # Layout Fila
                c_btn, c_info = st.columns([0.6, 11])
                with c_btn:
                    st.write("") # Alineación
                    # BOTÓN ENGRANAJE VERDE (CSS class gear-btn)
                    if st.button("⚙️", key=f"g_{t['id']}", help="Opciones"): modal_gestion(t)
                
                with c_info:
                    st.markdown(f"""
                    <div class="rep-row">
                        <div style="width:120px;"><span class="{badge} badge">{stt}</span></div>
                        <div class="rep-col">
                            <ul class="info-list">
                                <li>TR001 - {t['id']}</li>
                                <li><strong>{nom_cli}</strong></li>
                                <li>DNI: {t['cliente_dni']}</li>
                            </ul>
                        </div>
                        <div class="rep-col">
                            <ul class="info-list">
                                <li>Motivo: {t['motivo']}</li>
                                <li>Equipo: {t['marca']} - {t['modelo']}</li>
                                <li>Clave: {t['contrasena']}</li>
                                <li>Técnico: {t['vendedor_nombre']}</li>
                            </ul>
                        </div>
                        <div class="rep-col" style="color:#6c757d;">Sin repuestos</div>
                        <div class="rep-col">
                            <ul class="info-list">
                                <li>Pagado: {t['acuenta']:.2f}</li>
                                <li>Restante: {t['saldo']:.2f}</li>
                                <li><strong>Total: {t['precio']:.2f}</strong></li>
                            </ul>
                        </div>
                        <div class="rep-col">
                            <ul class="info-list">
                                <li>Recepción: {f_rec}</li>
                                <li>Entrega: {t['fecha_entrega']}</li>
                            </ul>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# (Resto de módulos simplificados para mantener el foco)
elif menu == "Dashboard": st.title("Dashboard")
elif menu == "Ventas": st.title("Ventas")
elif menu == "Logística": st.title("Logística")
elif menu == "Clientes": st.title("Clientes")
