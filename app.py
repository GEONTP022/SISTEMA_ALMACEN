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
import qrcode
import tempfile
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="VillaFix OS | Enterprise",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"⚠️ Error de conexión: {e}")
    st.stop()

# --- 3. ESTILOS ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1, h2, h3, h4 { color: #1e293b !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea {
        background-color: white !important; color: #1e293b !important; border-radius: 8px; border: 1px solid #cbd5e1;
    }
    .metric-card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #2563EB; text-align: center;
    }
    .ticket-card {
        background-color: white; padding: 15px; border-radius: 10px;
        border: 1px solid #e2e8f0; margin-bottom: 12px;
        transition: all 0.2s ease-in-out;
    }
    .ticket-card:hover { border-color: #2563EB; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    .stButton>button { border-radius: 8px; font-weight: 600; text-transform: uppercase; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES ---

def generar_ticket_termico(t):
    """Ticket 80mm"""
    width = 80 * mm; height = 297 * mm 
    buffer = io.BytesIO(); c = canvas.Canvas(buffer, pagesize=(width, height))
    margin = 5 * mm; y = height - 10 * mm
    
    # Header
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12); c.drawCentredString(width/2, y, "VILLAFIX OS"); y -= 5*mm
    c.setFont("Helvetica", 8); c.drawCentredString(width/2, y, "Servicio Técnico Especializado"); y -= 4*mm
    c.drawCentredString(width/2, y, "Av. Revolución 123, VES"); y -= 4*mm
    c.drawCentredString(width/2, y, "WhatsApp: 999-999-999"); y -= 6*mm
    c.setLineWidth(0.5); c.line(margin, y, width-margin, y); y -= 5*mm
    
    # Info
    c.setFont("Helvetica-Bold", 14); c.drawCentredString(width/2, y, f"ORDEN #{t['id']}"); y -= 5*mm
    c.setFont("Helvetica", 8); c.drawCentredString(width/2, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"); y -= 8*mm
    
    # Cliente
    c.setFont("Helvetica-Bold", 9); c.drawString(margin, y, "CLIENTE:"); y -= 4*mm
    c.setFont("Helvetica", 9); nom = t['cliente_nombre'][:25] + "..." if len(t['cliente_nombre']) > 25 else t['cliente_nombre']
    c.drawString(margin, y, f"- {nom}"); y -= 4*mm
    c.drawString(margin, y, f"- DNI: {t['cliente_dni']}"); y -= 6*mm
    
    # Equipo
    c.line(margin, y, width-margin, y); y -= 5*mm
    c.setFont("Helvetica-Bold", 9); c.drawString(margin, y, "EQUIPO:"); c.drawRightString(width-margin, y, f"{t['marca']} {t['modelo']}"); y -= 5*mm
    c.setFont("Helvetica", 8); c.drawString(margin, y, "IMEI:"); c.drawRightString(width-margin, y, t['imei'] if t['imei'] else "N/A"); y -= 5*mm
    
    # Falla
    c.setFont("Helvetica-Bold", 9); c.drawString(margin, y, "FALLA:"); y -= 4*mm
    c.setFont("Helvetica", 9)
    for line in textwrap.wrap(t['descripcion'], width=32):
        c.drawString(margin, y, line); y -= 4*mm
    y -= 2*mm
    
    # Caja
    c.setDash(1, 2); c.line(margin, y, width-margin, y); c.setDash([]); y -= 6*mm
    c.setFont("Helvetica", 10); c.drawString(margin, y, "TOTAL:"); c.drawRightString(width-margin, y, f"S/ {t['precio']:.2f}"); y -= 5*mm
    c.drawString(margin, y, "A CUENTA:"); c.drawRightString(width-margin, y, f"S/ {t['acuenta']:.2f}"); y -= 6*mm
    c.setFont("Helvetica-Bold", 14); c.drawString(margin, y, "SALDO:"); c.drawRightString(width-margin, y, f"S/ {t['saldo']:.2f}"); y -= 8*mm
    c.setFont("Helvetica", 8); c.drawCentredString(width/2, y, f"Pago: {t['metodo_pago']}"); y -= 10*mm
    
    # QR
    qr = qrcode.make(f"TICKET-{t['id']}|SALDO:{t['saldo']}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        qr.save(tmp.name)
        c.drawImage(tmp.name, (width-30*mm)/2, y-30*mm, width=30*mm, height=30*mm)
        os.unlink(tmp.name)
    y -= 35*mm
    c.setFont("Helvetica", 7); c.drawCentredString(width/2, y, "Garantía válida por 30 días."); c.showPage(); c.save()
    buffer.seek(0); return buffer

def consultar_dni_reniec(dni):
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd"
    fuentes = [
        {"url": f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}", "headers": {'Authorization': f'Bearer {token}'}, "tipo": "v2"},
        {"url": f"https://api.apis.net.pe/v1/dni?numero={dni}", "headers": {}, "tipo": "v1"}
    ]
    for f in fuentes:
        try:
            r = requests.get(f["url"], headers=f["headers"], timeout=3)
            if r.status_code == 200:
                d = r.json()
                if f["tipo"] == "v2": return f"{d.get('nombres','')} {d.get('apellidoPaterno','')} {d.get('apellidoMaterno','')}".strip()
                elif f["tipo"] == "v1": return d.get("nombre", "")
        except: continue
    return None

def subir_imagen(archivo):
    try:
        f = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name}"
        supabase.storage.from_("fotos_productos").upload(f, archivo.getvalue(), {"content-type": archivo.type})
        return supabase.storage.from_("fotos_productos").get_public_url(f)
    except: return None

# --- VENTANA FLOTANTE (MODAL) ---
# Usamos st.dialog (requiere streamlit >= 1.37.0)
@st.dialog("Gestión de Ticket")
def mostrar_modal_ticket(t):
    col_a, col_b = st.columns([2,1])
    with col_a:
        st.write(f"👤 **{t['cliente_nombre']}**")
        st.caption(f"DNI: {t['cliente_dni']}")
    with col_b:
        st.markdown(f"## #{t['id']}")
    
    st.divider()
    st.write(f"📱 **Equipo:** {t['marca']} {t['modelo']}")
    st.caption(f"Falla: {t['descripcion']}")
    
    # PESTAÑAS DE ACCIÓN
    tab_ver, tab_pagar, tab_anular = st.tabs(["🖨️ Ver Ticket", "💰 Cobrar", "🚫 Anular"])
    
    with tab_ver:
        pdf = generar_ticket_termico(t)
        st.download_button("📥 Descargar PDF (80mm)", pdf, file_name=f"Ticket_{t['id']}.pdf", mime="application/pdf", use_container_width=True)

    with tab_pagar:
        if t['saldo'] <= 0:
            st.success("✅ ¡Pagado Completo!")
        else:
            st.metric("Deuda Pendiente", f"S/ {t['saldo']:.2f}")
            metodo = st.selectbox("Medio de Pago", ["Yape", "Plin", "Efectivo", "Tarjeta"])
            if st.button("CONFIRMAR PAGO FINAL", type="primary", use_container_width=True):
                supabase.table("tickets").update({
                    "saldo": 0, "acuenta": t['precio'], "metodo_pago": metodo, "estado": "Entregado"
                }).eq("id", t['id']).execute()
                st.rerun()

    with tab_anular:
        st.warning("¿Cancelar este servicio?")
        if st.button("Sí, Anular Ticket", use_container_width=True):
            supabase.table("tickets").update({"estado": "Anulado"}).eq("id", t['id']).execute()
            st.rerun()

# --- 5. MENÚ ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #fff;'>VillaFix OS</h2>", unsafe_allow_html=True)
    st.markdown("---")
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Recepción", "Inventario", "Config"],
        icons=["speedometer2", "hdd-network", "box-seam", "gear"],
        default_index=1,
    )

# Limpieza automática al cambiar pestaña
if 'last_tab' not in st.session_state: st.session_state.last_tab = selected
if st.session_state.last_tab != selected:
    st.session_state.recepcion_step = 1
    st.session_state.temp_data = {}
    st.session_state.cli_nombre = ""
    st.session_state.last_tab = selected
    st.rerun()

if 'recepcion_step' not in st.session_state: st.session_state.recepcion_step = 1
if 'temp_data' not in st.session_state: st.session_state.temp_data = {}

# === PÁGINAS ===

if selected == "Dashboard":
    st.markdown("### 📊 Panel de Control")
    try:
        c_prod = supabase.table("productos").select("id", count="exact").execute().count
        c_cli = supabase.table("clientes").select("id", count="exact").execute().count
        c_tic = supabase.table("tickets").select("id", count="exact").eq("estado", "Pendiente").execute().count
    except: c_prod=0; c_cli=0; c_tic=0
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="metric-card"><h3>👥 {c_cli}</h3><p>Clientes</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><h3>📦 {c_prod}</h3><p>Productos</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><h3>🔧 {c_tic}</h3><p>En Taller</p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card"><h3>💰 S/ 0</h3><p>Caja Hoy</p></div>', unsafe_allow_html=True)

elif selected == "Recepción":
    col_form, col_feed = st.columns([1.6, 1])

    with col_form:
        if st.session_state.recepcion_step == 1:
            st.markdown("### 🛠️ Nuevo Servicio")
            st.caption("Paso 1: Datos del Cliente y Equipo")
            if 'cli_nombre' not in st.session_state: st.session_state.cli_nombre = ""
            
            c_dni, c_btn = st.columns([3, 1])
            dni = c_dni.text_input("DNI Cliente", placeholder="8 dígitos")
            if c_btn.button("🔍"):
                res = supabase.table("clientes").select("nombre").eq("dni", dni).execute()
                if res.data: st.session_state.cli_nombre = res.data[0]["nombre"]; st.toast("Cliente Frecuente")
                else: 
                    nom = consultar_dni_reniec(dni)
                    if nom: st.session_state.cli_nombre = nom; st.toast("RENIEC OK")
                    else: st.warning("No encontrado")

            nombre = st.text_input("Nombre *", value=st.session_state.cli_nombre)
            c1, c2 = st.columns(2)
            tel = c1.text_input("Teléfono")
            dir_cli = c2.text_input("Dirección")
            
            st.markdown("---")
            c_eq1, c_eq2 = st.columns(2)
            marca = c_eq1.text_input("Marca *")
            modelo = c_eq1.text_input("Modelo *")
            motivo = c_eq1.selectbox("Servicio", ["Reparación", "Mantenimiento", "Software", "Garantía"])
            imei = c_eq2.text_input("IMEI / Serie")
            passw = c_eq2.text_input("Contraseña *")
            precio = c_eq2.number_input("Costo Total (S/)", min_value=0.0, step=5.0)
            desc = st.text_area("Falla / Detalles *", height=80)
            fecha_ent = st.date_input("Fecha Entrega", min_value=date.today())

            if st.button("➡️ CONTINUAR AL PAGO", type="primary", use_container_width=True):
                if not dni or not nombre or not marca or not modelo: st.error("❌ Faltan datos obligatorios")
                else:
                    st.session_state.temp_data = {
                        "dni": dni, "nombre": nombre.upper(), "tel": tel, "dir": dir_cli,
                        "marca": marca.upper(), "modelo": modelo.upper(), "imei": imei,
                        "pass": passw, "motivo": motivo, "precio": precio, "desc": desc, "fecha": str(fecha_ent)
                    }
                    st.session_state.recepcion_step = 2
                    st.rerun()

        elif st.session_state.recepcion_step == 2:
            data = st.session_state.temp_data
            st.markdown(f"### 💰 Caja: {data['nombre']}")
            c_tot, c_pen = st.columns(2)
            c_tot.metric("Total", f"S/ {data['precio']:.2f}")
            with st.container(border=True):
                acuenta = st.number_input("Monto Adelanto", min_value=0.0, max_value=data['precio'], step=5.0)
                saldo = data['precio'] - acuenta
                c_pen.metric("Saldo", f"S/ {saldo:.2f}", delta_color="inverse" if saldo > 0 else "normal")
                cm, co = st.columns(2)
                metodo = cm.selectbox("Método", ["Yape", "Plin", "Efectivo", "Tarjeta"])
                operacion = co.text_input("N° Operación")
                
                def guardar(fin_acu, fin_met):
                    try:
                        try:
                            supabase.table("clientes").insert({
                                "dni": data['dni'], "nombre": data['nombre'], "telefono": data['tel'], "direccion": data['dir']
                            }).execute()
                        except: pass
                        
                        res = supabase.table("tickets").insert({
                            "cliente_dni": data['dni'], "cliente_nombre": data['nombre'],
                            "marca": data['marca'], "modelo": data['modelo'], "imei": data['imei'],
                            "contrasena": data['pass'], "motivo": data['motivo'], "descripcion": data['desc'],
                            "precio": data['precio'], "fecha_entrega": data['fecha'],
                            "acuenta": fin_acu, "saldo": data['precio']-fin_acu, 
                            "metodo_pago": fin_met, "cod_operacion": operacion if fin_acu > 0 else "",
                            "estado": "Pendiente"
                        }).execute()
                        if res.data:
                            tid = res.data[0]['id']
                            st.session_state.updf = generar_ticket_termico({**data, "id": tid, "cliente_nombre": data['nombre'], "cliente_dni": data['dni'], "acuenta": fin_acu, "saldo": data['precio']-fin_acu, "metodo_pago": fin_met})
                            st.session_state.uid = tid
                            st.session_state.recepcion_step = 3
                            st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

                cp, co = st.columns(2)
                with cp:
                    if st.button("💾 CONFIRMAR PAGO", type="primary", use_container_width=True): guardar(acuenta, metodo)
                with co:
                    if st.button("⏩ OMITIR PAGO", use_container_width=True): guardar(0.00, "Contra-entrega")
            if st.button("⬅️ Editar"): st.session_state.recepcion_step = 1; st.rerun()

        elif st.session_state.recepcion_step == 3:
            st.success("✅ ¡Ticket Generado!")
            st.balloons()
            st.download_button("📥 DESCARGAR TICKET (80mm)", st.session_state.updf, f"Ticket_{st.session_state.uid}.pdf", "application/pdf", type="primary", use_container_width=True)
            if st.button("➕ NUEVO CLIENTE (Limpiar)", use_container_width=True):
                st.session_state.recepcion_step = 1; st.session_state.temp_data = {}; st.session_state.cli_nombre = ""; st.rerun()

    # --- LISTA DE TICKETS (DERECHA) ---
    with col_feed:
        st.markdown("### ⏱️ Tickets de Hoy")
        search = st.text_input("🔎 Buscar...", placeholder="DNI o Ticket")
        q = supabase.table("tickets").select("*")
        if search: q = q.or_(f"cliente_dni.eq.{search},id.eq.{search if search.isdigit() else 0}")
        else: q = q.gte("created_at", datetime.now().strftime('%Y-%m-%dT00:00:00'))
        
        tickets = q.order("created_at", desc=True).execute().data
        if tickets:
            for t in tickets:
                # TARJETA INTELIGENTE
                with st.container():
                    st.markdown(f"""
                    <div class="ticket-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <b>#{t['id']} {t['cliente_nombre'].split(' ')[0]}</b>
                            <span style="font-size:0.8em; background:#eee; padding:2px 6px; border-radius:4px;">{t['estado']}</span>
                        </div>
                        <div style="color:#555; font-size:0.9em; margin:5px 0;">
                            📱 {t['marca']} {t['modelo']}
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="color:{'#dc2626' if t['saldo']>0 else '#16a34a'}; font-weight:bold;">
                                {'Debe S/' + str(t['saldo']) if t['saldo']>0 else 'PAGADO'}
                            </span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # BOTÓN DE ACCIÓN (Abre la ventana flotante)
                    if st.button("👁️ VER / GESTIONAR", key=f"btn_{t['id']}", use_container_width=True):
                        mostrar_modal_ticket(t)
        else: st.info("Sin movimientos.")

elif selected == "Inventario":
    st.markdown("### 📦 Inventario")
    t1, t2 = st.tabs(["Ver", "Nuevo"])
    with t1:
        q = st.text_input("Buscar...")
        query = supabase.table("productos").select("*")
        if q: query = query.ilike("nombre", f"%{q}%")
        data = query.execute().data
        if data:
            cols = st.columns(3)
            for i, r in enumerate(data):
                with cols[i%3]:
                    with st.container(border=True):
                        if r['imagen_url']: st.image(r['imagen_url'], use_container_width=True)
                        else: st.markdown("🖼️ *Sin imagen*")
                        st.write(f"**{r['nombre']}**")
                        st.caption(f"Stock: {r['stock']} | S/ {r['precio']}")
    with t2:
        with st.form("add"):
            c1,c2=st.columns(2)
            n=c1.text_input("Nombre"); p=c2.number_input("Precio")
            s=c2.number_input("Stock",min_value=1); f=st.file_uploader("Foto")
            if st.form_submit_button("Guardar"):
                u = subir_imagen(f) if f else None
                supabase.table("productos").insert({"nombre":n,"precio":p,"stock":s,"imagen_url":u}).execute()
                st.success("Guardado")

elif selected == "Config":
    st.title("⚙️ Configuración"); st.write("v3.3 Final")
