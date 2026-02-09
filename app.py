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
import xlsxwriter
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="VillaFix ERP", page_icon="💎", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except: st.error("⚠️ Error Conexión DB"); st.stop()

# --- 3. ESTILOS CSS PRO (RECREANDO EL VIDEO) ---
st.markdown("""
<style>
    /* FUENTE Y FONDO */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #f3f4f6; font-family: 'Inter', sans-serif; }
    
    /* SIDEBAR (AZUL OSCURO DEL VIDEO) */
    section[data-testid="stSidebar"] { background-color: #1e293b; }
    section[data-testid="stSidebar"] h1, h2, h3, span { color: white !important; }
    
    /* INPUTS ESTILO MATERIAL */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input {
        border: 1px solid #e2e8f0; border-radius: 6px; height: 42px; color: #334155; background-color: white;
    }
    label { font-weight: 600; color: #475569; font-size: 0.85rem; margin-bottom: 4px; }

    /* BOTONES */
    .stButton>button { border-radius: 6px; font-weight: 600; height: 42px; transition: all 0.2s; border: none; }
    
    /* Botón Guardar (Verde) */
    .btn-save button { background-color: #10b981 !important; color: white !important; }
    .btn-save button:hover { background-color: #059669 !important; box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.3); }
    
    /* Botón Cancelar/Cerrar (Rojo Suave) */
    .btn-close button { background-color: #ef4444 !important; color: white !important; }
    .btn-close button:hover { background-color: #dc2626 !important; }

    /* --- TABLA ESTILO VIDEO --- */
    .table-container { border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); background: white; margin-top: 15px; }
    
    .table-header {
        background-color: #475569; /* Gris azulado oscuro */
        color: white; padding: 12px 16px; font-weight: 600; font-size: 0.85rem;
        display: grid; grid-template-columns: 0.5fr 1.5fr 2fr 1fr 1fr 1fr; gap: 10px; align-items: center;
        text-transform: uppercase; letter-spacing: 0.05em;
    }
    
    .table-row {
        padding: 14px 16px; border-bottom: 1px solid #f1f5f9; color: #334155; font-size: 0.9rem;
        display: grid; grid-template-columns: 0.5fr 1.5fr 2fr 1fr 1fr 1fr; gap: 10px; align-items: center;
        background-color: white; transition: background 0.15s;
    }
    .table-row:hover { background-color: #f8fafc; }
    .table-row:last-child { border-bottom: none; }

    /* BADGES */
    .status-badge { padding: 4px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: white; display: inline-block; text-align: center; }
    .bg-recep { background-color: #3b82f6; } /* Azul */
    .bg-entr { background-color: #10b981; }  /* Verde */
    .bg-anul { background-color: #ef4444; }  /* Rojo */

    /* CUSTOM MODAL LAYOUT */
    .modal-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-bottom: 15px; }
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

# --- 5. MODALES INTERACTIVOS (DISEÑO VIDEO) ---

# A) MODAL AGREGAR CLIENTE (LAYOUT EXACTO DEL VIDEO)
@st.dialog("Agregar Cliente")
def modal_cliente():
    # FILA 1: Tipo Doc | Número | Nombre
    c1, c2, c3 = st.columns([1, 1, 2])
    tipo = c1.selectbox("Tipo Documento", ["DNI", "RUC", "CE"])
    
    # Búsqueda integrada en el input de DNI
    dni_col = c2.columns([3, 1])
    dni = dni_col[0].text_input("Número Documento", label_visibility="collapsed", placeholder="DNI")
    if dni_col[1].button("🔍", key="search_reniec"):
        if dni and len(dni)==8:
            if n := buscar_reniec(dni): st.session_state.temp_nom = n; st.rerun()
            else: st.toast("No encontrado")
    
    val_nom = st.session_state.get('temp_nom', '')
    nom = c3.text_input("Razón Social / Nombre", value=val_nom)

    # FILA 2: Dirección | Teléfono | Email
    c4, c5, c6 = st.columns(3)
    dire = c4.text_input("Dirección")
    telf = c5.text_input("Teléfono")
    email = c6.text_input("Correo Electrónico")

    st.write("") # Espacio
    
    # FOOTER: Botones Close y Guardar
    cf1, cf2 = st.columns([1, 4])
    with cf1:
        st.markdown('<div class="btn-close">', unsafe_allow_html=True)
        if st.button("Close"): st.rerun() # Cierra el modal
        st.markdown('</div>', unsafe_allow_html=True)
    with cf2:
        st.markdown('<div class="btn-save">', unsafe_allow_html=True)
        if st.button("Guardar", use_container_width=True):
            if not dni or not nom: st.error("DNI y Nombre obligatorios")
            else:
                supabase.table("clientes").upsert({"dni":dni, "nombre":nom, "telefono":telf, "direccion":dire, "email":email}).execute()
                st.success("Guardado"); st.session_state.temp_nom = ""; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# B) MODAL GESTIÓN DE ORDEN (PAGAR/VER)
@st.dialog("Gestión de Reparación")
def modal_gestion(t):
    st.markdown(f"#### 🔧 Orden #{t['id']} - {t['cliente_nombre']}")
    
    t_pagar, t_ver, t_anular = st.tabs(["💵 Pagar", "📄 Ticket", "🚫 Anular"])
    
    with t_pagar:
        if t['saldo'] <= 0: st.success("✅ PAGADO")
        else:
            c_monto, c_metodo = st.columns(2)
            monto = c_monto.number_input("Monto", 0.0, float(t['saldo']), float(t['saldo']))
            metodo = c_metodo.selectbox("Método", ["Efectivo", "Yape", "Plin"])
            
            st.markdown('<div class="btn-save">', unsafe_allow_html=True)
            if st.button("Confirmar Pago", use_container_width=True):
                n_acu = t['acuenta'] + monto; n_sal = t['precio'] - n_acu
                est = "Entregado" if n_sal == 0 else "Pendiente"
                supabase.table("tickets").update({"acuenta":n_acu, "saldo":n_sal, "estado":est, "metodo_pago":metodo}).eq("id", t['id']).execute()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with t_ver:
        pdf = generar_pdf(t)
        st.download_button("Descargar PDF", pdf, f"T_{t['id']}.pdf", "application/pdf", use_container_width=True)
        c_a, c_d = st.columns(2)
        if t['foto_antes']: c_a.image(t['foto_antes'], caption="Antes")
        if t['foto_despues']: c_d.image(t['foto_despues'], caption="Después")

    with t_anular:
        st.markdown('<div class="btn-close">', unsafe_allow_html=True)
        if st.button("ANULAR ORDEN", use_container_width=True):
            supabase.table("tickets").update({"estado":"Anulado", "saldo":0}).eq("id", t['id']).execute(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 6. MENU LATERAL ---
with st.sidebar:
    if os.path.exists("Logo-Mockup.jpg"): st.image("Logo-Mockup.jpg", width=180)
    else: st.title("VillaFix")
    
    try: users = [u['nombre'] for u in supabase.table("usuarios").select("nombre").execute().data]
    except: users = ["Admin"]
    st.session_state.user = st.selectbox("Usuario", users)
    
    menu = option_menu(None, ["Dashboard", "Recepción", "Ventas", "Logística", "Clientes"], 
        icons=["speedometer2", "tools", "cart4", "truck", "people"], default_index=1,
        styles={"nav-link-selected": {"background-color": "#2563EB"}})

# --- 7. MÓDULOS ---

# === RECEPCIÓN (UI MEJORADA) ===
if menu == "Recepción":
    t_new, t_list = st.tabs(["✨ Nueva Recepción", "📋 Listado"])
    
    # 1. FORMULARIO DE INGRESO
    with t_new:
        st.markdown("##### 👤 Información del Cliente")
        c_sel, c_add = st.columns([6, 1])
        try: clis = {f"{c['dni']} - {c['nombre']}": c for c in supabase.table("clientes").select("*").execute().data}
        except: clis = {}
        sel = c_sel.selectbox("Buscar Cliente", ["Seleccionar..."] + list(clis.keys()), label_visibility="collapsed")
        
        # Botón Verde "+" Estilo Video
        with c_add:
            st.markdown('<div class="btn-save">', unsafe_allow_html=True)
            if st.button("➕", help="Nuevo Cliente"): modal_cliente()
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Auto-fill
        d_dni = ""; d_nom = ""
        if sel != "Seleccionar...": d_dni = clis[sel]['dni']; d_nom = clis[sel]['nombre']

        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 1])
            dni = c1.text_input("DNI", value=d_dni, disabled=True if d_dni else False)
            nom = c2.text_input("Nombre", value=d_nom, disabled=True if d_nom else False)
            cel = c3.text_input("Celular")

        st.markdown("##### 📱 Información de Recepción")
        with st.container(border=True):
            r1, r2, r3 = st.columns(3)
            mar = r1.selectbox("Marca", ["Samsung", "Apple", "Xiaomi", "Motorola", "Otro"])
            mod = r2.text_input("Modelo")
            imei = r3.text_input("IMEI")
            
            r4, r5, r6 = st.columns(3)
            mot = r4.selectbox("Motivo", ["Reparación", "Garantía", "Mantenimiento"])
            f_ent = r5.date_input("Entrega", date.today())
            foto = r6.file_uploader("Evidencia", type=['jpg','png'])
            
            r7, r8, r9 = st.columns(3)
            costo = r7.number_input("Costo", 0.0)
            acuenta = r8.number_input("A Cuenta", 0.0)
            falla = st.text_area("Falla / Observaciones")

        st.markdown('<div class="btn-save">', unsafe_allow_html=True)
        if st.button("GENERAR TICKET", use_container_width=True):
            if not dni or not nom: st.error("Datos incompletos")
            else:
                url = subir_evidencia(foto)
                if not d_dni: supabase.table("clientes").upsert({"dni":dni, "nombre":nom, "telefono":cel}).execute()
                supabase.table("tickets").insert({
                    "cliente_dni":dni, "cliente_nombre":nom, "vendedor_nombre":st.session_state.user,
                    "marca":mar, "modelo":mod, "motivo":mot, "falla_reportada":falla,
                    "precio":costo, "acuenta":acuenta, "saldo":costo-acuenta,
                    "foto_antes":url, "fecha_entrega":str(f_ent), "estado":"Pendiente"
                }).execute()
                st.success("Ticket Generado"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # 2. LISTADO TIPO TABLA (ESTILO VIDEO)
    with t_list:
        # Barra superior
        c_search, c_excel = st.columns([4, 1])
        search = c_search.text_input("🔍 Buscar...", label_visibility="collapsed")
        
        q = supabase.table("tickets").select("*").order("created_at", desc=True)
        if search: q = q.ilike("cliente_nombre", f"%{search}%")
        data = q.execute().data
        
        if data:
            with c_excel:
                st.download_button("📗 Excel", to_excel(pd.DataFrame(data)), "data.xlsx", use_container_width=True)

            # TABLA PERSONALIZADA
            st.markdown("""
            <div class="table-container">
                <div class="table-header">
                    <div>Estado</div>
                    <div>Cliente</div>
                    <div>Equipo</div>
                    <div>Técnico</div>
                    <div>Saldo</div>
                    <div>Acción</div>
                </div>
            """, unsafe_allow_html=True)
            
            for t in data:
                if t['estado']=='Anulado': bg="bg-anul"; txt="ANULADO"
                elif t['saldo']<=0: bg="bg-entr"; txt="PAGADO"
                else: bg="bg-recep"; txt="TALLER"
                
                # Fila (Grid Layout)
                col1, col2, col3, col4, col5, col6 = st.columns([0.5, 1.5, 2, 1, 1, 1])
                
                # Renderizado limpio
                with st.container():
                    st.markdown(f"""
                    <div class="table-row">
                        <div><span class="status-badge {bg}">{txt}</span></div>
                        <div><strong>{t['cliente_nombre'].split()[0]}</strong><br><small>{t['cliente_dni']}</small></div>
                        <div>{t['marca']} {t['modelo']}<br><small>{t['motivo']}</small></div>
                        <div>{t['vendedor_nombre']}</div>
                        <div style="font-weight:bold; color:{'#10b981' if t['saldo']<=0 else '#ef4444'}">S/ {t['saldo']:.2f}</div>
                    """, unsafe_allow_html=True)
                    
                    # El botón de acción TIENE que ir en una columna de Streamlit para funcionar
                    if st.button("⚙️", key=f"g_{t['id']}", help="Gestionar"): modal_gestion(t)
                    
                    st.markdown("</div>", unsafe_allow_html=True) # Cierra div row
            
            st.markdown("</div>", unsafe_allow_html=True) # Cierra container

# === DASHBOARD ===
elif menu == "Dashboard":
    st.title("📊 Panel de Control")
    c1, c2, c3 = st.columns(3)
    try: 
        tks = pd.DataFrame(supabase.table("tickets").select("*").execute().data)
        vts = pd.DataFrame(supabase.table("ventas").select("*").execute().data)
        caja = tks['acuenta'].sum() + (vts['total'].sum() if not vts.empty else 0)
    except: tks=pd.DataFrame(); caja=0
    
    c1.metric("Caja Total", f"S/ {caja:.2f}")
    c2.metric("En Taller", len(tks[tks['estado']=='Pendiente']) if not tks.empty else 0)
    
    if not tks.empty:
        st.subheader("Ingresos por Día")
        tks['fecha'] = pd.to_datetime(tks['created_at']).dt.date
        st.bar_chart(tks.groupby('fecha')['acuenta'].sum())

# === OTROS MÓDULOS (SIMPLIFICADOS) ===
elif menu == "Ventas": st.info("Módulo Ventas (Integrado en V6.0)")
elif menu == "Logística": st.info("Módulo Logística (Integrado en V6.0)")
elif menu == "Clientes": st.info("CRM Clientes (Integrado en V6.0)")
