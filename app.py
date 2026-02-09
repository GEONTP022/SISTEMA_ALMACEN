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

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="VillaFix OS | Enterprise",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CONEXIÓN A SUPABASE ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"⚠️ Error de conexión: {e}")
    st.stop()

# --- 3. ESTILOS CSS (TEMA PREMIUM) ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1, h2, h3, h4 { color: #1e293b !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    
    /* Inputs Estilizados */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea {
        background-color: white !important; color: #1e293b !important; 
        border-radius: 8px; border: 1px solid #cbd5e1;
    }
    
    /* Tarjetas */
    .metric-card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #2563EB;
        text-align: center;
    }
    
    /* Live Feed (Tickets) */
    .ticket-item { 
        background: white; padding: 15px; border-radius: 10px; 
        border: 1px solid #e2e8f0; margin-bottom: 10px; 
        transition: transform 0.2s;
    }
    .ticket-item:hover { transform: scale(1.02); border-color: #2563EB; }
    
    .status-badge { 
        background: #dbeafe; color: #1e40af; padding: 2px 8px; 
        border-radius: 12px; font-size: 0.75em; font-weight: bold; 
    }
    
    /* Botones */
    .stButton>button { border-radius: 8px; font-weight: 600; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES DEL SISTEMA ---

def generar_ticket_termico(t):
    """
    Genera un PDF formato Tira (80mm) para impresoras térmicas.
    """
    # Configuración de papel (80mm ancho x Largo dinámico)
    width = 80 * mm
    height = 297 * mm # Largo suficiente A4 vertical
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height))
    
    # Márgenes
    margin = 5 * mm
    y = height - 10 * mm # Cursor inicial
    printable_width = width - (2 * margin)
    
    # --- CABECERA ---
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width/2, y, "VILLAFIX OS")
    y -= 5 * mm
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, y, "Servicio Técnico Especializado")
    y -= 4 * mm
    c.drawCentredString(width/2, y, "Av. Revolución 123, VES")
    y -= 4 * mm
    c.drawCentredString(width/2, y, "WhatsApp: 999-999-999")
    y -= 6 * mm
    
    # Separador
    c.setLineWidth(0.5)
    c.line(margin, y, width-margin, y)
    y -= 5 * mm
    
    # Datos del Ticket
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width/2, y, f"ORDEN #{t['id']}")
    y -= 5 * mm
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 8 * mm
    
    # --- CLIENTE ---
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, "CLIENTE:")
    y -= 4 * mm
    c.setFont("Helvetica", 9)
    # Cortar nombre si es muy largo
    nom = t['cliente_nombre']
    if len(nom) > 25: nom = nom[:25] + "..."
    c.drawString(margin, y, f"- {nom}")
    y -= 4 * mm
    c.drawString(margin, y, f"- DNI: {t['cliente_dni']}")
    y -= 6 * mm
    
    # --- EQUIPO ---
    c.line(margin, y, width-margin, y)
    y -= 5 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, "EQUIPO:")
    c.drawRightString(width-margin, y, f"{t['marca']} {t['modelo']}")
    y -= 5 * mm
    c.setFont("Helvetica", 8)
    c.drawString(margin, y, "IMEI/Serie:")
    c.drawRightString(width-margin, y, t['imei'] if t['imei'] else "N/A")
    y -= 5 * mm
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, "FALLA REPORTADA:")
    y -= 4 * mm
    c.setFont("Helvetica", 9)
    
    # Texto multilinea para la descripción
    lines = textwrap.wrap(t['descripcion'], width=32)
    for line in lines:
        c.drawString(margin, y, line)
        y -= 4 * mm
    
    y -= 2 * mm
    
    # --- FINANCIERO (CAJA) ---
    c.setDash(1, 2)
    c.line(margin, y, width-margin, y)
    c.setDash([])
    y -= 6 * mm
    
    c.setFont("Helvetica", 10)
    c.drawString(margin, y, "TOTAL:")
    c.drawRightString(width-margin, y, f"S/ {t['precio']:.2f}")
    y -= 5 * mm
    
    c.drawString(margin, y, "A CUENTA:")
    c.drawRightString(width-margin, y, f"S/ {t['acuenta']:.2f}")
    y -= 6 * mm
    
    # SALDO GIGANTE
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, "SALDO:")
    c.drawRightString(width-margin, y, f"S/ {t['saldo']:.2f}")
    y -= 8 * mm
    
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, y, f"Pago: {t['metodo_pago']}")
    y -= 10 * mm
    
    # --- QR y PIE ---
    qr_data = f"TICKET-{t['id']}|SALDO:{t['saldo']}"
    qr = qrcode.make(qr_data)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        qr.save(tmp.name)
        # Centrar QR
        qr_size = 30 * mm
        c.drawImage(tmp.name, (width-qr_size)/2, y-qr_size, width=qr_size, height=qr_size)
        os.unlink(tmp.name)
        
    y -= (qr_size + 5 * mm)
    
    c.setFont("Helvetica", 7)
    c.drawCentredString(width/2, y, "Garantía válida por 30 días.")
    y -= 3 * mm
    c.drawCentredString(width/2, y, "No cubre pantallas mojadas/rotas.")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def consultar_dni_reniec(dni):
    """Búsqueda Híbrida Inteligente"""
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd" # Tu Token
    fuentes = [
        {"url": f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}", "headers": {'Authorization': f'Bearer {token}'}, "tipo": "v2"},
        {"url": f"https://api.apis.net.pe/v1/dni?numero={dni}", "headers": {}, "tipo": "v1"}
    ]
    for fuente in fuentes:
        try:
            r = requests.get(fuente["url"], headers=fuente["headers"], timeout=3)
            if r.status_code == 200:
                d = r.json()
                if fuente["tipo"] == "v2": return f"{d.get('nombres','')} {d.get('apellidoPaterno','')} {d.get('apellidoMaterno','')}".strip()
                elif fuente["tipo"] == "v1": return d.get("nombre", "")
        except: continue
    return None

def subir_imagen(archivo):
    try:
        f = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name}"
        supabase.storage.from_("fotos_productos").upload(f, archivo.getvalue(), {"content-type": archivo.type})
        return supabase.storage.from_("fotos_productos").get_public_url(f)
    except: return None

# --- 5. INTERFAZ PRINCIPAL ---

with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #fff;'>VillaFix OS</h2>", unsafe_allow_html=True)
    st.markdown("---")
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Recepción", "Inventario", "Config"],
        icons=["speedometer2", "hdd-network", "box-seam", "gear"],
        default_index=1, # Inicia en Recepción por defecto
        styles={
            "container": {"padding": "0!important", "background-color": "#262b3d"},
            "icon": {"color": "white", "font-size": "18px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "color": "white"},
            "nav-link-selected": {"background-color": "#2563EB"},
        }
    )

# --- ESTADOS DE SESIÓN ---
if 'recepcion_step' not in st.session_state: st.session_state.recepcion_step = 1
if 'temp_data' not in st.session_state: st.session_state.temp_data = {}

# === LÓGICA DE PÁGINAS ===

if selected == "Dashboard":
    st.markdown("### 📊 Panel de Control")
    try:
        c_prod = supabase.table("productos").select("id", count="exact").execute().count
        c_cli = supabase.table("clientes").select("id", count="exact").execute().count
        c_tic = supabase.table("tickets").select("id", count="exact").eq("estado", "Pendiente").execute().count
    except: c_prod=0; c_cli=0; c_tic=0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f'<div class="metric-card"><h3>👥 {c_cli}</h3><p>Clientes</p></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-card"><h3>📦 {c_prod}</h3><p>Productos</p></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="metric-card"><h3>🔧 {c_tic}</h3><p>En Taller</p></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="metric-card"><h3>💰 S/ 0</h3><p>Caja Hoy</p></div>', unsafe_allow_html=True)

elif selected == "Recepción":
    # Layout Principal: 60% Formulario | 40% Live Feed
    col_form, col_feed = st.columns([1.5, 1])

    with col_form:
        # === PASO 1: DATOS (Ingreso) ===
        if st.session_state.recepcion_step == 1:
            st.markdown("### 🛠️ Nuevo Servicio")
            st.caption("Complete los datos del cliente y equipo.")
            
            # Variables locales
            if 'cli_nombre' not in st.session_state: st.session_state.cli_nombre = ""
            
            # Búsqueda DNI
            c_dni, c_btn = st.columns([3, 1])
            dni = c_dni.text_input("DNI Cliente", placeholder="8 dígitos")
            if c_btn.button("🔍"):
                res = supabase.table("clientes").select("nombre").eq("dni", dni).execute()
                if res.data: 
                    st.session_state.cli_nombre = res.data[0]["nombre"]
                    st.toast("Cliente Frecuente")
                else: 
                    nom = consultar_dni_reniec(dni)
                    if nom: st.session_state.cli_nombre = nom; st.toast("RENIEC OK")
                    else: st.warning("No encontrado")

            nombre = st.text_input("Nombre Completo *", value=st.session_state.cli_nombre)
            c1, c2 = st.columns(2)
            tel = c1.text_input("Teléfono / WhatsApp")
            dir_cli = c2.text_input("Dirección (Opcional)")
            
            st.markdown("---")
            # Datos Equipo
            c_eq1, c_eq2 = st.columns(2)
            marca = c_eq1.text_input("Marca *", placeholder="Ej: Samsung")
            modelo = c_eq1.text_input("Modelo *", placeholder="Ej: A54")
            motivo = c_eq1.selectbox("Servicio", ["Reparación", "Mantenimiento", "Software", "Garantía"])
            imei = c_eq2.text_input("IMEI / Serie")
            passw = c_eq2.text_input("Contraseña *", placeholder="Patrón o Clave")
            precio = c_eq2.number_input("Costo Total (S/)", min_value=0.0, step=5.0)
            
            desc = st.text_area("Falla / Detalles *", height=80)
            fecha_ent = st.date_input("Fecha Entrega", min_value=date.today())

            if st.button("➡️ CONTINUAR AL PAGO", type="primary", use_container_width=True):
                if not dni or not nombre or not marca or not modelo or not passw:
                    st.error("❌ Faltan datos obligatorios")
                else:
                    # Guardar en memoria y pasar al paso 2
                    st.session_state.temp_data = {
                        "dni": dni, "nombre": nombre.upper(), "tel": tel, "dir": dir_cli,
                        "marca": marca.upper(), "modelo": modelo.upper(), "imei": imei,
                        "pass": passw, "motivo": motivo, "precio": precio, 
                        "desc": desc, "fecha": str(fecha_ent)
                    }
                    st.session_state.recepcion_step = 2
                    st.rerun()

        # === PASO 2: CAJA (Cobro y Ticket) ===
        elif st.session_state.recepcion_step == 2:
            data = st.session_state.temp_data
            st.markdown(f"### 💰 Caja: {data['nombre']}")
            
            # Resumen
            c_tot, c_acu, c_pen = st.columns(3)
            c_tot.metric("Total", f"S/ {data['precio']:.2f}")
            
            with st.container(border=True):
                acuenta = st.number_input("Monto a Cuenta (Adelanto) *", min_value=0.0, max_value=data['precio'], step=5.0)
                saldo = data['precio'] - acuenta
                
                c_acu.metric("A Cuenta", f"S/ {acuenta:.2f}")
                c_pen.metric("Saldo", f"S/ {saldo:.2f}", delta_color="inverse" if saldo > 0 else "normal")
                
                st.write("")
                cm, co = st.columns(2)
                metodo = cm.selectbox("Método Pago", ["Yape", "Plin", "Efectivo", "Tarjeta"])
                operacion = co.text_input("N° Operación", placeholder="Opcional")
                
                if st.button("🖨️ CONFIRMAR Y GENERAR TICKET", type="primary", use_container_width=True):
                    try:
                        # 1. Guardar Cliente
                        try:
                            supabase.table("clientes").insert({
                                "dni": data['dni'], "nombre": data['nombre'], "telefono": data['tel'], "direccion": data['dir']
                            }).execute()
                        except: pass
                        
                        # 2. Guardar Ticket
                        ticket_final = {
                            "cliente_dni": data['dni'], "cliente_nombre": data['nombre'],
                            "marca": data['marca'], "modelo": data['modelo'],
                            "imei": data['imei'], "contrasena": data['pass'],
                            "motivo": data['motivo'], "descripcion": data['desc'],
                            "precio": data['precio'], "fecha_entrega": data['fecha'],
                            "acuenta": acuenta, "saldo": saldo, 
                            "metodo_pago": metodo, "cod_operacion": operacion,
                            "estado": "Pendiente"
                        }
                        res_t = supabase.table("tickets").insert(ticket_final).execute()
                        
                        # 3. Generar PDF
                        if res_t.data:
                            t_id = res_t.data[0]['id']
                            ticket_final['id'] = t_id
                            
                            st.session_state.ultimo_pdf = generar_ticket_termico(ticket_final)
                            st.session_state.ultimo_id = t_id
                            st.session_state.recepcion_step = 3
                            st.rerun()
                            
                    except Exception as e: st.error(f"Error: {e}")

            if st.button("⬅️ Editar datos"):
                st.session_state.recepcion_step = 1
                st.rerun()

        # === PASO 3: ÉXITO ===
        elif st.session_state.recepcion_step == 3:
            st.success("✅ ¡Operación Exitosa!")
            st.balloons()
            
            st.download_button(
                label="📥 IMPRIMIR TICKET (80mm)",
                data=st.session_state.ultimo_pdf,
                file_name=f"Ticket_{st.session_state.ultimo_id}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
            
            if st.button("➕ NUEVO SERVICIO", use_container_width=True):
                st.session_state.recepcion_step = 1
                st.session_state.temp_data = {}
                st.rerun()

    # --- LIVE FEED (Derecha) ---
    with col_feed:
        st.markdown("### ⏱️ Hoy")
        search = st.text_input("🔎 Buscar...", placeholder="DNI o Ticket")
        
        query = supabase.table("tickets").select("*")
        if search:
            query = query.or_(f"cliente_dni.eq.{search},id.eq.{search if search.isdigit() else 0}")
        else:
            today = datetime.now().strftime('%Y-%m-%dT00:00:00')
            query = query.gte("created_at", today)
            
        tickets = query.order("created_at", desc=True).execute().data
        
        if tickets:
            for t in tickets:
                st.markdown(f"""
                <div class="ticket-item">
                    <div style="display:flex; justify-content:space-between;">
                        <b>#{t['id']}</b> <span class="status-badge">{t['estado']}</span>
                    </div>
                    <div style="font-size:0.9em; margin-top:5px;">
                        👤 {t['cliente_nombre']}<br>
                        📱 {t['marca']} {t['modelo']}<br>
                        <b style="color:#d9534f">Debe: S/ {t['saldo']}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Botón WhatsApp
                res_tel = supabase.table("clientes").select("telefono").eq("dni", t['cliente_dni']).execute()
                tel = res_tel.data[0]['telefono'] if res_tel.data else ""
                if tel:
                    msg = f"Hola {t['cliente_nombre']}, su Ticket #{t['id']} ({t['marca']}) ya está registrado."
                    st.link_button("💬 WhatsApp", f"https://wa.me/51{tel}?text={msg}", use_container_width=True)
        else:
            st.info("Sin movimientos recientes.")

elif selected == "Inventario":
    st.markdown("### 📦 Inventario")
    t_ver, t_add = st.tabs(["Catálogo", "Nuevo Producto"])
    
    with t_ver:
        q = st.text_input("Buscar producto...")
        query = supabase.table("productos").select("*")
        if q: query = query.ilike("nombre", f"%{q}%")
        data = query.execute().data
        
        if data:
            cols = st.columns(3)
            for i, row in enumerate(data):
                with cols[i%3]:
                    with st.container(border=True):
                        if row['imagen_url']: st.image(row['imagen_url'])
                        st.write(f"**{row['nombre']}**")
                        st.caption(f"Stock: {row['stock']} | S/ {row['precio']}")
    
    with t_add:
        with st.form("new_prod"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nombre"); p = c2.number_input("Precio")
            s = c2.number_input("Stock", min_value=1); f = st.file_uploader("Foto")
            if st.form_submit_button("Guardar"):
                u = subir_imagen(f) if f else None
                supabase.table("productos").insert({"nombre":n,"precio":p,"stock":s,"imagen_url":u}).execute()
                st.success("Producto Agregado")

elif selected == "Config":
    st.title("⚙️ Configuración")
    st.write("Versión 2.5 Enterprise")
