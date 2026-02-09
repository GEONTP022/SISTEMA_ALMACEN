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

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="VillaFix ERP", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")

# --- CONEXIÓN ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except: st.error("⚠️ Error Conexión DB"); st.stop()

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .stApp { background-color: #f1f5f9; }
    .kpi-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #2563EB; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; }
    .stButton>button { border-radius: 8px; font-weight: 600; text-transform: uppercase; width: 100%; }
    
    /* Tarjeta Ticket */
    .ticket-card { background: white; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px; }
    .badge-ok { background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.8em; float: right; }
    .badge-warn { background: #fee2e2; color: #991b1b; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.8em; float: right; }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES ---

def generar_pdf(t):
    """Ticket 80mm"""
    width = 80 * mm; height = 297 * mm 
    buffer = io.BytesIO(); c = canvas.Canvas(buffer, pagesize=(width, height))
    margin = 5 * mm; y = height - 10 * mm
    
    c.setFont("Helvetica-Bold", 12); c.drawCentredString(width/2, y, "VILLAFIX OS"); y -= 5*mm
    c.setFont("Helvetica", 8); c.drawCentredString(width/2, y, "Servicio Técnico"); y -= 5*mm
    c.line(margin, y, width-margin, y); y -= 5*mm
    
    c.setFont("Helvetica-Bold", 14); c.drawCentredString(width/2, y, f"ORDEN #{t['id']}"); y -= 8*mm
    
    c.setFont("Helvetica", 9); c.drawString(margin, y, f"Cliente: {t['cliente_nombre']}"); y -= 4*mm
    c.drawString(margin, y, f"DNI: {t['cliente_dni']}"); y -= 6*mm
    
    c.line(margin, y, width-margin, y); y -= 5*mm
    c.setFont("Helvetica-Bold", 9); c.drawString(margin, y, f"EQUIPO: {t['marca']} {t['modelo']}"); y -= 5*mm
    
    c.setFont("Helvetica", 9)
    for line in textwrap.wrap(f"Falla: {t['falla_reportada']}", 28):
        c.drawString(margin, y, line); y -= 4*mm
    
    # Fecha Entrega
    if t.get('fecha_entrega'):
        y -= 2*mm
        c.setFont("Helvetica-Bold", 9); c.drawString(margin, y, f"Entrega Aprox: {t['fecha_entrega']}")
        y -= 6*mm

    c.line(margin, y, width-margin, y); y -= 5*mm
    c.setFont("Helvetica", 10); c.drawString(margin, y, "TOTAL:"); c.drawRightString(width-margin, y, f"S/ {t['precio']:.2f}"); y -= 5*mm
    c.drawString(margin, y, "A CUENTA:"); c.drawRightString(width-margin, y, f"S/ {t['acuenta']:.2f}"); y -= 6*mm
    c.setFont("Helvetica-Bold", 12); c.drawString(margin, y, "SALDO:"); c.drawRightString(width-margin, y, f"S/ {t['saldo']:.2f}"); y -= 10*mm
    
    c.showPage(); c.save(); buffer.seek(0); return buffer

def consultar_reniec(dni):
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd" # Tu token
    try:
        r = requests.get(f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}", headers={'Authorization': f'Bearer {token}'}, timeout=3)
        if r.status_code == 200: 
            d = r.json(); return f"{d.get('nombres','')} {d.get('apellidoPaterno','')} {d.get('apellidoMaterno','')}".strip()
    except: pass
    return None

def subir_imagen(archivo):
    try:
        f = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name}"
        supabase.storage.from_("fotos_productos").upload(f, archivo.getvalue(), {"content-type": archivo.type})
        return supabase.storage.from_("fotos_productos").get_public_url(f)
    except: return None

# --- DIALOGOS ---
@st.dialog("Gestión Ticket")
def modal_ticket(t):
    st.subheader(f"#{t['id']} {t['cliente_nombre']}")
    c1, c2 = st.columns(2)
    c1.write(f"📱 **{t['marca']}**"); c2.write(f"🔑 **{t['contrasena']}**")
    st.info(f"Falla: {t['falla_reportada']}")
    if t['fecha_entrega']: st.caption(f"📅 Entrega estimada: {t['fecha_entrega']}")
    
    col_a, col_b = st.columns(2)
    with col_a:
        pdf = generar_pdf(t)
        st.download_button("🖨️ PDF", pdf, f"Ticket_{t['id']}.pdf", "application/pdf", use_container_width=True)
    
    with col_b:
        if t['saldo'] > 0:
            if st.button("💰 Cobrar Saldo", use_container_width=True):
                supabase.table("tickets").update({"saldo":0, "acuenta":t['precio'], "estado":"Entregado"}).eq("id", t['id']).execute()
                st.rerun()
        else: st.success("Pagado")

# --- MENÚ ---
with st.sidebar:
    st.title("VillaFix OS")
    selected = option_menu(None, ["Dashboard", "Recepción", "Inventario", "Config"], icons=["graph-up", "tools", "box-seam", "gear"])

if 'temp_nom' not in st.session_state: st.session_state.temp_nom = ""

# ==========================================
# 1. DASHBOARD
# ==========================================
if selected == "Dashboard":
    st.header("📊 Panel de Control")
    try:
        # Consultamos datos reales
        tickets = supabase.table("tickets").select("*").execute().data
        prods = supabase.table("productos").select("id", count="exact").execute().count
    except: tickets = []; prods = 0
    
    # Cálculos reales
    hoy = datetime.now().strftime('%Y-%m-%d')
    caja = 0.0
    pendientes = 0
    
    for t in tickets:
        if t['estado'] == 'Pendiente': pendientes += 1
        if t['created_at'].startswith(hoy):
            if t['estado'] == 'Anulado': continue
            elif t['estado'] == 'Entregado': caja += float(t['precio'])
            else: caja += float(t['acuenta'])

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="kpi-card"><h3>📦 {prods}</h3><p>Productos</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><h3>🔧 {pendientes}</h3><p>En Taller</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><h3>💰 S/ {caja:.2f}</h3><p>Caja Hoy</p></div>', unsafe_allow_html=True)

# ==========================================
# 2. RECEPCIÓN (CORREGIDO: DNI y FECHA)
# ==========================================
elif selected == "Recepción":
    c_form, c_feed = st.columns([1.5, 2])

    with c_form:
        st.subheader("🛠️ Nuevo Servicio")
        
        # 1. BÚSQUEDA DNI
        col_dni, col_btn = st.columns([2, 1])
        dni = col_dni.text_input("DNI Cliente")
        if col_btn.button("🔍 Buscar"):
            # Primero buscamos en base de datos local
            local = supabase.table("clientes").select("nombre").eq("dni", dni).execute()
            if local.data: 
                st.session_state.temp_nom = local.data[0]['nombre']
                st.toast("Cliente encontrado en BD")
            else:
                # Si no, buscamos en RENIEC
                api_nom = consultar_reniec(dni)
                if api_nom: 
                    st.session_state.temp_nom = api_nom
                    st.toast("Datos obtenidos de RENIEC")
                else: 
                    st.warning("DNI no encontrado, ingrese nombre manual.")

        nombre = st.text_input("Nombre", value=st.session_state.temp_nom)
        
        c1, c2 = st.columns(2)
        eq = c1.text_input("Equipo (Marca/Modelo)")
        imei = c2.text_input("IMEI / Serie")
        falla = st.text_area("Falla Reportada")
        
        # 2. FECHA ENTREGA (NUEVO)
        f_entrega = st.date_input("Fecha Entrega Estimada", min_value=date.today())
        
        c3, c4 = st.columns(2)
        precio = c3.number_input("Costo Total", 0.0)
        acuenta = c4.number_input("Adelanto", 0.0)
        
        if st.button("💾 GUARDAR TICKET", type="primary"):
            if not dni or not nombre or not eq:
                st.error("Falta DNI, Nombre o Equipo")
            else:
                # Guardar cliente
                try: supabase.table("clientes").insert({"dni":dni, "nombre":nombre}).execute()
                except: pass
                
                # Guardar Ticket (Con los campos correctos)
                data = {
                    "cliente_dni": dni, "cliente_nombre": nombre, "marca": eq, "imei": imei,
                    "falla_reportada": falla, "precio": precio, "acuenta": acuenta, "saldo": precio-acuenta,
                    "fecha_entrega": str(f_entrega), "estado": "Pendiente" # <--- AQUI ESTABA EL ERROR DE LA FECHA
                }
                supabase.table("tickets").insert(data).execute()
                st.success("Ticket Generado Exitosamente")
                st.session_state.temp_nom = "" # Limpiar
                st.rerun()

    # FEED DE TICKETS
    with c_feed:
        st.subheader("📋 Tickets de Hoy")
        hoy = datetime.now().strftime('%Y-%m-%d')
        tickets = supabase.table("tickets").select("*").gte("created_at", hoy).order("created_at", desc=True).execute().data
        
        if tickets:
            for t in tickets:
                status_html = '<span class="badge-ok">PAGADO</span>' if t['saldo'] <= 0 else f'<span class="badge-warn">DEBE S/{t["saldo"]}</span>'
                if t['estado'] == 'Anulado': status_html = '<span style="float:right; color:grey; font-weight:bold;">🚫 ANULADO</span>'
                
                with st.container():
                    st.markdown(f"""
                    <div class="ticket-card">
                        <div style="display:flex; justify-content:space-between;">
                            <b>#{t['id']} {t['cliente_nombre'].split()[0]}</b>
                            {status_html}
                        </div>
                        <div style="color:#555; font-size:0.9em;">📱 {t['marca']}</div>
                        <div style="color:#888; font-size:0.8em; margin-top:5px;">📅 Entrega: {t['fecha_entrega']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("👁️ VER", key=f"b_{t['id']}", use_container_width=True):
                        modal_ticket(t)
        else: st.info("No hay ingresos hoy.")

# ==========================================
# 3. INVENTARIO (CORREGIDO ERROR INSERT)
# ==========================================
elif selected == "Inventario":
    st.subheader("📦 Inventario")
    t1, t2 = st.tabs(["Ver", "Nuevo"])
    
    with t1:
        prods = pd.DataFrame(supabase.table("productos").select("*").execute().data)
        if not prods.empty:
            st.dataframe(prods[['nombre', 'stock', 'precio', 'costo']], use_container_width=True)
            
    with t2:
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombre Producto")
        p = c2.number_input("Precio Venta", 0.0)
        s = c1.number_input("Stock", 1)
        c = c2.number_input("Costo Compra", 0.0)
        foto = st.file_uploader("Foto")
        
        if st.button("GUARDAR PRODUCTO"):
            url_foto = subir_imagen(foto) if foto else None
            # Insertar con los nombres de columna EXACTOS de la base de datos nueva
            supabase.table("productos").insert({
                "nombre": n, "precio": p, "stock": s, "costo": c, "imagen_url": url_foto
            }).execute()
            st.success("Producto guardado correctamente")

elif selected == "Config":
    st.write("Configuración")
