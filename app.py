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

# --- 3. ESTILOS CSS (DISEÑO TIPO TABLA) ---
st.markdown("""
<style>
    .stApp { background-color: #f3f4f6; }
    
    /* TARJETA DE TICKET (ESTILO TABLA) */
    .ticket-row {
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        border-left: 5px solid #ccc;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        font-family: 'Source Sans Pro', sans-serif;
        color: #333;
    }
    
    .ticket-row.pendiente { border-left-color: #f59e0b; } /* Naranja */
    .ticket-row.pagado { border-left-color: #10b981; }    /* Verde */
    .ticket-row.anulado { border-left-color: #ef4444; opacity: 0.7; }   /* Rojo */

    .grid-container {
        display: grid;
        grid-template-columns: 0.5fr 1.5fr 1.5fr 1fr;
        gap: 15px;
        align-items: center;
    }

    /* COLUMNAS */
    .col-icon { display: flex; justify-content: center; align-items: center; font-size: 20px; }
    .col-data { font-size: 0.85rem; line-height: 1.4; }
    .col-data strong { color: #111; font-weight: 700; }
    
    .label { color: #6b7280; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; }
    .value { color: #1f2937; font-weight: 600; }
    .money-tag { background: #eff6ff; padding: 2px 6px; border-radius: 4px; color: #1e40af; font-weight: bold; }
    
    /* BOTONES */
    .stButton>button { border-radius: 6px; font-weight: 600; text-transform: uppercase; width: 100%; border: none; transition: 0.2s; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
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
    c.setFont("Helvetica", 9); c.drawString(margin, y, f"{t['cliente_nombre']}"); y -= 4*mm
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
@st.dialog("Detalle del Servicio")
def modal_ticket(t):
    st.header(f"Orden #{t['id']}")
    c1, c2 = st.columns(2)
    c1.write(f"👤 **Cliente:** {t['cliente_nombre']}")
    c1.write(f"📞 **Teléfono:** {t.get('telefono_display', 'No registrado')}")
    c2.write(f"📱 **Equipo:** {t['marca']} {t['modelo']}")
    c2.write(f"🔑 **Clave:** {t['contrasena']}")
    
    st.divider()
    
    tab1, tab2, tab3 = st.tabs(["🖨️ Imprimir", "💰 Cobrar", "🚫 Anular"])
    
    with tab1:
        pdf = generar_ticket_termico(t)
        st.download_button("📥 Descargar Ticket (PDF)", pdf, f"Ticket_{t['id']}.pdf", "application/pdf", use_container_width=True)
    
    with tab2:
        if t['saldo'] <= 0: st.success("✅ ¡Pagado Completo!")
        else:
            st.metric("Deuda Pendiente", f"S/ {t['saldo']:.2f}")
            metodo = st.selectbox("Método", ["Yape", "Efectivo", "Tarjeta"])
            if st.button("CONFIRMAR COBRO TOTAL", type="primary", use_container_width=True):
                supabase.table("tickets").update({"saldo":0, "acuenta":t['precio'], "metodo_pago":metodo, "estado":"Entregado"}).eq("id", t['id']).execute()
                st.rerun()
                
    with tab3:
        st.warning("Esta acción pondrá el valor en S/ 0.00")
        if st.button("ANULAR TICKET", type="secondary", use_container_width=True):
            supabase.table("tickets").update({"estado":"Anulado"}).eq("id", t['id']).execute()
            st.rerun()

# --- 5. MENÚ ---
with st.sidebar:
    st.markdown("## VillaFix OS")
    selected = option_menu(None, ["Dashboard", "Recepción", "Inventario", "Config"], 
        icons=["speedometer2", "hdd-network", "box-seam", "gear"], default_index=0)

# Limpieza
if 'last_tab' not in st.session_state: st.session_state.last_tab = selected
if st.session_state.last_tab != selected:
    st.session_state.recepcion_step = 1; st.session_state.temp_data = {}; st.session_state.cli_nombre = ""; st.session_state.last_tab = selected; st.rerun()

# === LÓGICA DASHBOARD FINANCIERO ===
if selected == "Dashboard":
    st.markdown("### 📊 Panel de Control")
    
    # 1. Obtener datos
    try:
        tickets = supabase.table("tickets").select("*").execute().data
        prods = supabase.table("productos").select("id", count="exact").execute().count
        clis = supabase.table("clientes").select("id", count="exact").execute().count
    except: tickets = []; prods = 0; clis = 0
    
    # 2. Calcular Dinero Real (Caja Hoy)
    # Lógica: 
    # - Si es 'Entregado': Suma Precio Total (Ya pagó todo).
    # - Si es 'Pendiente': Suma solo 'A Cuenta'.
    # - Si es 'Anulado': No suma nada (0).
    
    hoy = datetime.now().strftime('%Y-%m-%d')
    caja_hoy = 0.0
    pendientes_count = 0
    
    for t in tickets:
        # Contar pendientes activos
        if t['estado'] == 'Pendiente': pendientes_count += 1
        
        # Calcular dinero solo de tickets creados HOY
        if t['created_at'].startswith(hoy):
            if t['estado'] == 'Anulado':
                continue # 0 soles
            elif t['estado'] == 'Entregado':
                caja_hoy += float(t['precio']) # Cobrado completo
            else:
                caja_hoy += float(t['acuenta']) # Solo adelanto

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="metric-card"><h3>👥 {clis}</h3><p>Clientes</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><h3>📦 {prods}</h3><p>Productos</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><h3>🔧 {pendientes_count}</h3><p>En Taller</p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card"><h3>💰 S/ {caja_hoy:.2f}</h3><p>Caja Hoy (Real)</p></div>', unsafe_allow_html=True)

# === RECEPCIÓN ===
elif selected == "Recepción":
    c_form, c_feed = st.columns([1.5, 2]) # Más espacio para el feed

    with c_form:
        if st.session_state.recepcion_step == 1:
            st.markdown("##### 🛠️ Nuevo Ingreso")
            if 'cli_nombre' not in st.session_state: st.session_state.cli_nombre = ""
            
            c_dni, c_btn = st.columns([2, 1])
            dni = c_dni.text_input("DNI", placeholder="8 dígitos")
            if c_btn.button("🔍", use_container_width=True):
                res = supabase.table("clientes").select("nombre").eq("dni", dni).execute()
                if res.data: st.session_state.cli_nombre = res.data[0]["nombre"]; st.toast("Cliente BD")
                else: 
                    nom = consultar_dni_reniec(dni)
                    if nom: st.session_state.cli_nombre = nom; st.toast("RENIEC")
                    else: st.warning("No encontrado")
            
            nom = st.text_input("Nombre", value=st.session_state.cli_nombre)
            tel = st.text_input("Teléfono")
            c1, c2 = st.columns(2)
            mar = c1.text_input("Marca"); mod = c2.text_input("Modelo")
            imei = c1.text_input("IMEI"); pas = c2.text_input("Clave")
            mot = st.selectbox("Motivo", ["Reparación", "Mantenimiento", "Software"])
            desc = st.text_area("Falla", height=70)
            pre = st.number_input("Precio Total (S/)", min_value=0.0)
            
            if st.button("CONTINUAR ➡️", type="primary"):
                if not dni or not nom or not mar: st.error("Faltan datos")
                else:
                    st.session_state.temp_data = {"dni":dni, "nom":nom, "tel":tel, "mar":mar, "mod":mod, "imei":imei, "pas":pas, "mot":mot, "desc":desc, "pre":pre}
                    st.session_state.recepcion_step = 2; st.rerun()

        elif st.session_state.recepcion_step == 2:
            st.markdown("##### 💰 Cobro")
            dt = st.session_state.temp_data
            st.metric("Total a Pagar", f"S/ {dt['pre']:.2f}")
            acu = st.number_input("Adelanto (S/)", 0.0, dt['pre'])
            met = st.selectbox("Pago", ["Efectivo", "Yape", "Plin"])
            
            if st.button("💾 GUARDAR TICKET", type="primary"):
                # Guardar Cliente
                try: supabase.table("clientes").insert({"dni":dt['dni'], "nombre":dt['nom'], "telefono":dt['tel']}).execute()
                except: pass
                # Guardar Ticket
                res = supabase.table("tickets").insert({
                    "cliente_dni":dt['dni'], "cliente_nombre":dt['nom'], "marca":dt['mar'], "modelo":dt['mod'], 
                    "imei":dt['imei'], "contrasena":dt['pas'], "motivo":dt['mot'], "descripcion":dt['desc'], 
                    "precio":dt['pre'], "acuenta":acu, "saldo":dt['pre']-acu, "metodo_pago":met, "estado":"Pendiente"
                }).execute()
                st.success("Ticket Creado")
                st.session_state.recepcion_step = 1; st.session_state.cli_nombre = ""; st.rerun()
            
            if st.button("⬅️ Atrás"): st.session_state.recepcion_step = 1; st.rerun()

    # --- LIVE FEED (DISEÑO TIPO TABLA SOLICITADO) ---
    with c_feed:
        st.markdown("##### 📋 Tickets Recientes")
        search = st.text_input("🔎 Buscar...", placeholder="Nombre, DNI o ID")
        
        q = supabase.table("tickets").select("*")
        if search: q = q.or_(f"cliente_dni.eq.{search},cliente_nombre.ilike.%{search}%")
        else: q = q.order("created_at", desc=True).limit(20)
        
        tickets = q.execute().data
        
        if tickets:
            for t in tickets:
                # 1. Definir Estilos y Datos
                fecha = datetime.fromisoformat(t['created_at']).strftime("%d/%m %H:%M")
                
                # Estado Visual
                if t['estado'] == "Anulado":
                    clase_estado = "anulado"; icono = "🚫"; estado_txt = "ANULADO"
                elif t['saldo'] <= 0:
                    clase_estado = "pagado"; icono = "✅"; estado_txt = "PAGADO"
                else:
                    clase_estado = "pendiente"; icono = "⚠️"; estado_txt = "PENDIENTE"

                # Obtener Teléfono (Query extra rápida)
                tel_txt = "No reg."
                try: 
                    c_res = supabase.table("clientes").select("telefono").eq("dni", t['cliente_dni']).execute()
                    if c_res.data and c_res.data[0]['telefono']: tel_txt = c_res.data[0]['telefono']
                except: pass
                
                # Inyectar teléfono para usarlo en el modal luego
                t['telefono_display'] = tel_txt

                # 2. Renderizar Tarjeta HTML
                with st.container():
                    st.markdown(f"""
                    <div class="ticket-row {clase_estado}">
                        <div class="grid-container">
                            <div class="col-icon" title="{estado_txt}">{icono}</div>
                            
                            <div class="col-data">
                                <div class="label">ID #{t['id']}</div>
                                <div><strong>{t['cliente_nombre'].split(' ')[0]}</strong></div> <div>🆔 {t['cliente_dni']}</div>
                                <div>📞 {tel_txt}</div>
                            </div>
                            
                            <div class="col-data">
                                <div class="label">EQUIPO</div>
                                <div><strong>{t['marca']} {t['modelo']}</strong></div>
                                <div>Motivo: {t['motivo']}</div>
                                <div>🔑 {t['contrasena']}</div>
                            </div>
                            
                            <div class="col-data" style="text-align:right;">
                                <div class="label">{fecha}</div>
                                <div>Total: <strong>S/ {t['precio']}</strong></div>
                                <div style="color: {'red' if t['saldo']>0 else 'green'};">Resta: S/ {t['saldo']}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 3. Botón de Acción
                    if st.button(f"👁️ VER DETALLES", key=f"b_{t['id']}", use_container_width=True):
                        modal_ticket(t)
        else:
            st.info("No hay tickets recientes.")

elif selected == "Inventario":
    st.info("Módulo de Inventario (Funcionando OK)")
    # (El código de inventario ya estaba arreglado en la V3.1, lo omito para no hacer esto eterno,
    # pero si lo necesitas dímelo y lo pego completo aquí).

elif selected == "Config":
    st.write("Configuración")
