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

# --- 3. ESTILOS CSS (NUEVO DISEÑO TIPO "NÓMINA" ORGANIZADO) ---
st.markdown("""
<style>
    .stApp { background-color: #f0f2f5; }
    h1, h2, h3, h4 { font-family: 'Source Sans Pro', sans-serif; font-weight: 700; color: #1f2937; }
    
    /* Inputs standard */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea {
        background-color: white !important; border-radius: 8px; border: 1px solid #d1d5db;
    }

    /* TARJETA DE TICKET ORGANIZADA (FLEXBOX) */
    .ticket-flex-card {
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 12px;
        overflow: hidden;
        border-left: 6px solid #ccc;
        transition: transform 0.2s;
    }
    .ticket-flex-card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.1); }

    /* Colores de estado lateral */
    .status-pendiente { border-left-color: #f59e0b; } /* Naranja */
    .status-pagado { border-left-color: #10b981; }    /* Verde */
    .status-anulado { border-left-color: #ef4444; opacity: 0.6; }   /* Rojo */

    /* Contenedor principal de datos */
    .ticket-data-container {
        display: flex;
        padding: 12px;
        gap: 15px;
        align-items: center;
    }

    /* COLUMNAS FLEXIBLES */
    .flex-col-client { flex: 2; border-right: 1px solid #eee; padding-right: 10px; }
    .flex-col-equip { flex: 3; border-right: 1px solid #eee; padding-right: 10px; }
    .flex-col-fin { flex: 2; text-align: right; }

    /* Elementos internos */
    .tk-id { font-weight: 900; color: #2563EB; font-size: 1.1em; }
    .tk-name { font-weight: 700; font-size: 1em; display: block; }
    .tk-meta { font-size: 0.8em; color: #6b7280; display: block; margin-top: 2px; }
    
    .tk-equip { font-weight: 700; font-size: 0.95em; }
    .tk-equip-meta { font-size: 0.8em; background: #f3f4f6; padding: 2px 6px; border-radius: 4px; color: #4b5563; margin-top: 4px; display: inline-block; }

    .tk-badge { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 0.7em; font-weight: 800; text-transform: uppercase; margin-bottom: 6px; }
    .badge-red { background: #fee2e2; color: #991b1b; }
    .badge-green { background: #d1fae5; color: #065f46; }
    .badge-grey { background: #e5e7eb; color: #374151; }
    
    .tk-price { font-weight: 800; font-size: 1.1em; color: #111; }
    .tk-date { font-size: 0.75em; color: #9ca3af; }

    /* Botón */
    .stButton>button { border-radius: 8px; font-weight: 700; text-transform: uppercase; width: 100%; border: none; background-color: #e5e7eb; color: #374151; }
    .stButton>button:hover { background-color: #2563EB; color: white; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES ---

def generar_ticket_termico(t):
    """Ticket 80mm"""
    width = 80 * mm; height = 297 * mm 
    buffer = io.BytesIO(); c = canvas.Canvas(buffer, pagesize=(width, height))
    margin = 5 * mm; y = height - 10 * mm
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12); c.drawCentredString(width/2, y, "VILLAFIX OS"); y -= 5*mm
    c.setFont("Helvetica", 8); c.drawCentredString(width/2, y, "Servicio Técnico"); y -= 4*mm
    c.drawCentredString(width/2, y, "WhatsApp: 999-999-999"); y -= 6*mm
    c.line(margin, y, width-margin, y); y -= 5*mm
    
    c.setFont("Helvetica-Bold", 14); c.drawCentredString(width/2, y, f"ORDEN #{t['id']}"); y -= 5*mm
    c.setFont("Helvetica", 8); c.drawCentredString(width/2, y, f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"); y -= 8*mm
    
    c.setFont("Helvetica-Bold", 9); c.drawString(margin, y, "CLIENTE:"); y -= 4*mm
    c.drawString(margin, y, f"{t['cliente_nombre']}"); y -= 4*mm
    c.drawString(margin, y, f"DNI: {t['cliente_dni']}"); y -= 6*mm
    
    c.line(margin, y, width-margin, y); y -= 5*mm
    c.setFont("Helvetica-Bold", 9); c.drawString(margin, y, "EQUIPO:"); c.drawRightString(width-margin, y, f"{t['marca']} {t['modelo']}"); y -= 5*mm
    c.setFont("Helvetica", 9); c.drawString(margin, y, "FALLA:"); 
    for line in textwrap.wrap(t['descripcion'], 25):
        y -= 4*mm; c.drawString(margin+10*mm, y, line)
    y -= 6*mm
    
    c.line(margin, y, width-margin, y); y -= 5*mm
    c.setFont("Helvetica", 10); c.drawString(margin, y, "TOTAL:"); c.drawRightString(width-margin, y, f"S/ {t['precio']:.2f}"); y -= 5*mm
    c.drawString(margin, y, "A CUENTA:"); c.drawRightString(width-margin, y, f"S/ {t['acuenta']:.2f}"); y -= 6*mm
    c.setFont("Helvetica-Bold", 12); c.drawString(margin, y, "SALDO:"); c.drawRightString(width-margin, y, f"S/ {t['saldo']:.2f}"); y -= 10*mm
    
    c.showPage(); c.save(); buffer.seek(0); return buffer

def consultar_dni_reniec(dni):
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd"
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

# --- VENTANA FLOTANTE (MODAL) ---
@st.dialog("Detalle de Servicio")
def modal_ticket(t):
    st.header(f"Orden #{t['id']}")
    # Datos en columnas dentro del modal
    c1, c2, c3 = st.columns(3)
    c1.caption("Cliente"); c1.write(f"**{t['cliente_nombre']}**")
    c2.caption("Equipo"); c2.write(f"**{t['marca']} {t['modelo']}**")
    c3.caption("Estado"); 
    if t['estado']=='Anulado': c3.error("Anulado")
    elif t['saldo']<=0: c3.success("Pagado")
    else: c3.warning(f"Debe S/{t['saldo']}")

    st.divider()
    st.caption("Falla Reportada:"); st.info(t['descripcion'])
    st.caption("Datos Internos:"); st.write(f"🆔 DNI: {t['cliente_dni']} | 🔑 Clave: {t['contrasena']}")

    tab1, tab2, tab3 = st.tabs(["🖨️ Imprimir", "💰 Cobrar", "🚫 Anular"])
    
    with tab1:
        pdf = generar_ticket_termico(t)
        st.download_button("📥 Descargar Ticket PDF", pdf, f"Ticket_{t['id']}.pdf", "application/pdf", use_container_width=True)
    
    with tab2:
        if t['estado']=='Anulado': st.error("Ticket Anulado.")
        elif t['saldo'] <= 0: st.success("✅ ¡No hay deuda!")
        else:
            st.metric("Saldo a Cobrar", f"S/ {t['saldo']:.2f}")
            metodo = st.selectbox("Pago Final", ["Efectivo", "Yape", "Plin", "Tarjeta"])
            if st.button("✅ CONFIRMAR COBRO", type="primary", use_container_width=True):
                supabase.table("tickets").update({"saldo":0, "acuenta":t['precio'], "metodo_pago":metodo, "estado":"Entregado"}).eq("id", t['id']).execute()
                st.toast("¡Cobrado!"); st.rerun()
                
    with tab3:
        st.warning("⚠️ ¿Anular servicio? El monto en caja será 0.")
        if st.button("❌ CONFIRMAR ANULACIÓN", type="secondary", use_container_width=True):
            supabase.table("tickets").update({"estado":"Anulado"}).eq("id", t['id']).execute()
            st.rerun()

# --- 5. MENÚ ---
with st.sidebar:
    st.markdown("### VillaFix OS")
    selected = option_menu(None, ["Dashboard", "Recepción", "Inventario", "Config"], 
        icons=["speedometer2", "hdd-network", "box-seam", "gear"], default_index=0)

# Limpieza
if 'last_tab' not in st.session_state: st.session_state.last_tab = selected
if st.session_state.last_tab != selected:
    st.session_state.recepcion_step = 1; st.session_state.temp_data = {}; st.session_state.cli_nombre = ""; st.session_state.last_tab = selected; st.rerun()

# === PÁGINAS ===

if selected == "Dashboard":
    st.subheader("📊 Resumen de Hoy")
    
    # Cálculo Financiero Real
    try:
        tickets = supabase.table("tickets").select("*").execute().data
        prods = supabase.table("productos").select("id", count="exact").execute().count
        pendientes = supabase.table("tickets").select("id", count="exact").eq("estado", "Pendiente").execute().count
    except: tickets = []; prods = 0; pendientes = 0
    
    hoy = datetime.now().strftime('%Y-%m-%d')
    caja = 0.0
    clientes_hoy = 0
    
    for t in tickets:
        if t['created_at'].startswith(hoy):
            clientes_hoy += 1
            if t['estado'] == 'Anulado': continue
            elif t['estado'] == 'Entregado': caja += float(t['precio'])
            else: caja += float(t['acuenta'])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clientes Hoy", clientes_hoy)
    c2.metric("Inventario", prods)
    c3.metric("Pendientes", pendientes)
    c4.metric("Caja Real (Hoy)", f"S/ {caja:.2f}")

elif selected == "Recepción":
    c_form, c_feed = st.columns([1.4, 2.2]) # Más ancho para el feed organizado

    with c_form:
        st.subheader("🛠️ Nuevo Ingreso")
        if st.session_state.recepcion_step == 1:
            if 'cli_nombre' not in st.session_state: st.session_state.cli_nombre = ""
            c_dni, c_btn = st.columns([2, 1])
            dni = c_dni.text_input("DNI", placeholder="8 dígitos")
            if c_btn.button("🔍 RENIEC", use_container_width=True):
                res = supabase.table("clientes").select("nombre").eq("dni", dni).execute()
                if res.data: st.session_state.cli_nombre = res.data[0]["nombre"]; st.toast("Cliente Recurrente")
                else: 
                    nom = consultar_dni_reniec(dni)
                    if nom: st.session_state.cli_nombre = nom; st.toast("DNI Validado")
                    else: st.warning("No encontrado")
            
            nom = st.text_input("Nombre", value=st.session_state.cli_nombre)
            tel = st.text_input("Teléfono (WhatsApp)")
            st.divider()
            c1, c2 = st.columns(2)
            mar = c1.text_input("Marca"); mod = c2.text_input("Modelo")
            imei = c1.text_input("IMEI/Serie"); pas = c2.text_input("Contraseña")
            mot = st.selectbox("Tipo Servicio", ["Reparación", "Mantenimiento", "Garantía"])
            desc = st.text_area("Falla / Observaciones", height=70)
            pre = st.number_input("PRECIO TOTAL (S/)", min_value=0.0, step=5.0)
            
            if st.button("CONTINUAR AL COBRO ➡️", type="primary", use_container_width=True):
                if not dni or not nom or not mar: st.error("Faltan datos obligatorios")
                else:
                    st.session_state.temp_data = {"dni":dni, "nom":nom, "tel":tel, "mar":mar, "mod":mod, "imei":imei, "pas":pas, "mot":mot, "desc":desc, "pre":pre}
                    st.session_state.recepcion_step = 2; st.rerun()

        elif st.session_state.recepcion_step == 2:
            st.subheader("💰 Caja y Confirmación")
            dt = st.session_state.temp_data
            st.info(f"Cliente: {dt['nom']} | Total: S/ {dt['pre']:.2f}")
            
            c1, c2 = st.columns(2)
            acu = c1.number_input("A Cuenta (Adelanto)", 0.0, dt['pre'], step=5.0)
            sal = dt['pre'] - acu
            c2.metric("Saldo Restante", f"S/ {sal:.2f}")
            met = st.selectbox("Medio de Pago Adelanto", ["Efectivo", "Yape", "Plin", "Tarjeta"])
            
            st.divider()
            
            # Lógica de estado inicial
            estado_inicial = "Entregado" if sal == 0 else "Pendiente"

            if st.button("✅ FINALIZAR Y GUARDAR", type="primary", use_container_width=True):
                # Guardar Cliente
                try: supabase.table("clientes").insert({"dni":dt['dni'], "nombre":dt['nom'], "telefono":dt['tel']}).execute()
                except: pass
                # Guardar Ticket
                res = supabase.table("tickets").insert({
                    "cliente_dni":dt['dni'], "cliente_nombre":dt['nom'], "marca":dt['mar'], "modelo":dt['mod'], 
                    "imei":dt['imei'], "contrasena":dt['pas'], "motivo":dt['mot'], "descripcion":dt['desc'], 
                    "precio":dt['pre'], "acuenta":acu, "saldo":sal, "metodo_pago":met, "estado":estado_inicial
                }).execute()
                st.success("¡Servicio Registrado!")
                st.session_state.recepcion_step = 1; st.session_state.cli_nombre = ""; st.rerun()
            
            if st.button("⬅️ Corregir Datos", use_container_width=True): st.session_state.recepcion_step = 1; st.rerun()

    # --- LIVE FEED (DISEÑO ORGANIZADO EN COLUMNAS V3.7) ---
    with c_feed:
        st.subheader("📋 Tickets del Día")
        search = st.text_input("🔎 Filtro rápido...", placeholder="DNI, Nombre o ID")
        
        q = supabase.table("tickets").select("*")
        if search: q = q.or_(f"cliente_dni.eq.{search},cliente_nombre.ilike.%{search}%")
        else: q = q.gte("created_at", datetime.now().strftime('%Y-%m-%dT00:00:00')).order("created_at", desc=True)
        
        tickets = q.execute().data
        
        if tickets:
            for t in tickets:
                # 1. Preparar Datos y Estilos
                fecha = datetime.fromisoformat(t['created_at']).strftime("%H:%M")
                
                if t['estado'] == "Anulado":
                    status_class = "status-anulado"; badge_html = '<span class="tk-badge badge-grey">🚫 ANULADO</span>'
                    nombre_style = "text-decoration: line-through; opacity: 0.7;"
                elif t['saldo'] <= 0:
                    status_class = "status-pagado"; badge_html = '<span class="tk-badge badge-green">✅ PAGADO</span>'
                    nombre_style = ""
                else:
                    status_class = "status-pendiente"; badge_html = f'<span class="tk-badge badge-red">⚠️ DEBE S/{t["saldo"]:.0f}</span>'
                    nombre_style = ""

                # Obtener teléfono
                tel_txt = ""
                try: 
                    c_res = supabase.table("clientes").select("telefono").eq("dni", t['cliente_dni']).execute()
                    if c_res.data and c_res.data[0]['telefono']: tel_txt = f"📞 {c_res.data[0]['telefono']}"
                except: pass
                
                t['telefono_display'] = tel_txt # Guardar para el modal

                # 2. Renderizar HTML Organizado (Flexbox)
                with st.container():
                    st.markdown(f"""
                    <div class="ticket-flex-card {status_class}">
                        <div class="ticket-data-container">
                            <div class="flex-col-client">
                                <span class="tk-id">#{t['id']}</span>
                                <span class="tk-name" style="{nombre_style}">{t['cliente_nombre'].split(' ')[0]}</span>
                                <span class="tk-meta">🆔 {t['cliente_dni']}</span>
                            </div>
                            
                            <div class="flex-col-equip">
                                <span class="tk-equip">{t['marca']} {t['modelo']}</span>
                                <div>
                                    <span class="tk-equip-meta">🔑 {t['contrasena']}</span>
                                    <span class="tk-equip-meta">{tel_txt}</span>
                                </div>
                            </div>
                            
                            <div class="flex-col-fin">
                                {badge_html}
                                <div class="tk-price">S/ {t['precio']:.0f}</div>
                                <div class="tk-date">{fecha}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 3. Botón de Acción
                    if st.button(f"👁️ GESTIONAR #{t['id']}", key=f"b_{t['id']}", use_container_width=True):
                        modal_ticket(t)
        else:
            st.info("No hay tickets registrados hoy.")

elif selected == "Inventario":
    st.info("Módulo de Inventario activo.")
    # (Código del inventario omitido por brevedad, ya funcionaba bien)

elif selected == "Config":
    st.write("Configuración del Sistema")
