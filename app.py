import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from supabase import create_client
from streamlit_option_menu import option_menu
from datetime import datetime, date
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import qrcode
import tempfile
import os

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="VillaFix OS | Enterprise",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed" # Menú cerrado para mas espacio
)

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"⚠️ Error de conexión: {e}")
    st.stop()

# --- 3. ESTILOS CSS "PREMIUM DARK/LIGHT" ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    
    /* Títulos y Textos */
    h1, h2, h3, h4 { color: #1e293b !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    p, label { color: #475569 !important; font-weight: 500; }
    
    /* Inputs de Alta Gama */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stDateInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea {
        background-color: white !important;
        color: #1e293b !important;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        transition: all 0.2s;
    }
    .stTextInput>div>div>input:focus { border-color: #2563EB; box-shadow: 0 0 0 3px rgba(37,99,235,0.2); }

    /* Tarjetas del Dashboard y Feed */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border-left: 5px solid #2563EB;
        margin-bottom: 15px;
    }
    
    /* Botones */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        transition: transform 0.1s;
    }
    .stButton>button:active { transform: scale(0.98); }

    /* Ticket Feed (Derecha) */
    .ticket-item {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        margin-bottom: 10px;
        font-size: 0.9em;
    }
    .status-badge {
        background-color: #dbeafe;
        color: #1e40af;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES DE ALTO NIVEL ---

def generar_ticket_pdf(datos_ticket):
    """Genera un PDF Profesional con QR en memoria"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # --- ENCABEZADO ---
    c.setFillColorRGB(0.1, 0.2, 0.4) # Azul oscuro profesional
    c.rect(0, height - 100, width, 100, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(30, height - 50, "VILLAFIX REPARACIONES")
    c.setFont("Helvetica", 12)
    c.drawString(30, height - 70, "Especialistas en Hardware y Software")
    
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(width - 30, height - 50, f"TICKET #{datos_ticket['id']}")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 30, height - 70, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # --- CUERPO ---
    c.setFillColor(colors.black)
    y = height - 150
    
    # Sección Cliente
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y, "DATOS DEL CLIENTE")
    c.line(30, y-5, width-30, y-5)
    y -= 25
    c.setFont("Helvetica", 10)
    c.drawString(30, y, f"Cliente: {datos_ticket['cliente_nombre']}")
    c.drawString(300, y, f"DNI: {datos_ticket['cliente_dni']}")
    y -= 15
    c.drawString(30, y, f"Teléfono: {datos_ticket.get('telefono', 'No registrado')}")
    
    y -= 40
    
    # Sección Equipo
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y, "DETALLES DEL SERVICIO")
    c.line(30, y-5, width-30, y-5)
    y -= 25
    c.setFont("Helvetica", 10)
    c.drawString(30, y, f"Equipo: {datos_ticket['marca']} {datos_ticket['modelo']}")
    c.drawString(300, y, f"IMEI/Serie: {datos_ticket['imei']}")
    y -= 15
    c.drawString(30, y, f"Motivo: {datos_ticket['motivo']}")
    c.drawString(300, y, f"Contraseña: {datos_ticket['contrasena']}")
    y -= 20
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(30, y, f"Falla Reportada: {datos_ticket['descripcion']}")
    
    y -= 40
    
    # Sección Costos (Caja)
    c.setStrokeColorRGB(0.9, 0.9, 0.9)
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(30, y-40, width-60, 50, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y-20, "Total Estimado:")
    c.drawRightString(width - 50, y-20, f"S/ {datos_ticket['precio']:.2f}")
    
    y -= 100
    
    # --- GENERAR QR (El toque caro) ---
    qr_data = f"VILLAFIX | Ticket: {datos_ticket['id']} | Estado: {datos_ticket['estado']}"
    qr = qrcode.make(qr_data)
    
    # Guardar QR temporalmente
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        qr.save(tmp.name)
        c.drawImage(tmp.name, width - 130, y - 50, width=100, height=100)
        os.unlink(tmp.name) # Borrar archivo temporal

    # --- LEGAL / TÉRMINOS ---
    c.setFont("Helvetica", 7)
    terms = [
        "TÉRMINOS Y CONDICIONES:",
        "1. La empresa no se hace responsable por equipos no recogidos después de 30 días.",
        "2. La garantía solo cubre la mano de obra y repuestos cambiados.",
        "3. No nos hacemos responsables por pérdida de información. Se recomienda backup.",
        "4. Equipos mojados o golpeados no tienen garantía posterior."
    ]
    text_y = 100
    for line in terms:
        c.drawString(30, text_y, line)
        text_y -= 10
        
    c.line(30, 50, 200, 50)
    c.drawString(30, 40, "Firma del Cliente")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def consultar_dni_reniec(dni):
    """Estrategia Híbrida de Búsqueda"""
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd" 
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

# Sidebar Moderno
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/6024/6024190.png", width=50)
    st.markdown("### VillaFix OS")
    selected = option_menu(
        menu_title=None,
        options=["Recepción", "Inventario", "Caja & Ventas", "Configuración"],
        icons=["hdd-network", "box-seam", "wallet2", "sliders"],
        default_index=0,
    )
    st.info("🟢 Sistema Online v2.5")

# --- LÓGICA POR PÁGINA ---

if selected == "Recepción":
    # DISEÑO DE DOS COLUMNAS (60% Formulario, 40% Live Feed)
    col_form, col_feed = st.columns([1.5, 1])
    
    # --- COLUMNA IZQUIERDA: FORMULARIO DE INGRESO ---
    with col_form:
        st.markdown("### 🛠️ Nueva Recepción")
        st.caption("Complete los datos para generar la Orden de Servicio.")
        
        # Estado del Cliente
        if 'cli_nombre' not in st.session_state: st.session_state.cli_nombre = ""
        if 'cli_dni' not in st.session_state: st.session_state.cli_dni = ""

        # 1. Búsqueda Rápida
        c_dni, c_search, c_clean = st.columns([3, 1, 0.5])
        dni = c_dni.text_input("DNI Cliente", value=st.session_state.cli_dni, placeholder="Ingrese DNI")
        
        if c_search.button("🔍"):
            if len(dni) == 8:
                # BD Local
                res = supabase.table("clientes").select("*").eq("dni", dni).execute()
                if res.data:
                    st.session_state.cli_nombre = res.data[0]["nombre"]
                    st.toast("Cliente Frecuente Identificado", icon="👤")
                else:
                    # API
                    nom = consultar_dni_reniec(dni)
                    if nom: 
                        st.session_state.cli_nombre = nom
                        st.toast("Datos obtenidos de RENIEC", icon="☁️")
                    else: st.warning("No encontrado")
                st.session_state.cli_dni = dni
            else: st.error("DNI inválido")
            
        if c_clean.button("🧹"):
            st.session_state.cli_nombre = ""; st.session_state.cli_dni = ""; st.rerun()

        # Formulario
        nombre = st.text_input("Nombre Completo *", value=st.session_state.cli_nombre)
        
        c1, c2 = st.columns(2)
        telefono = c1.text_input("WhatsApp (Opcional)")
        direccion = c2.text_input("Dirección (Opcional)")
        
        st.markdown("---")
        st.markdown("##### 📱 Datos del Equipo")
        
        c_eq1, c_eq2 = st.columns(2)
        marca = c_eq1.text_input("Marca *", placeholder="Ej: Samsung")
        modelo = c_eq1.text_input("Modelo *", placeholder="Ej: A50")
        motivo = c_eq1.selectbox("Tipo de Servicio", ["Reparación", "Mantenimiento", "Software", "Garantía"])
        
        imei = c_eq2.text_input("IMEI / Serie")
        contrasena = c_eq2.text_input("Contraseña *", placeholder="Patrón o Clave")
        precio = c_eq2.number_input("Presupuesto (S/)", min_value=0.0, step=10.0)
        
        descripcion = st.text_area("Diagnóstico / Falla *", height=80, placeholder="Describa el problema...")
        
        fecha_entrega = st.date_input("Fecha Entrega Aprox.", min_value=date.today())

        # Botón Guardar
        if st.button("💾 PROCESAR INGRESO", type="primary", use_container_width=True):
            if not dni or not nombre or not marca or not modelo or not contrasena or not descripcion:
                st.error("❌ Complete los campos obligatorios (DNI, Nombre, Marca, Modelo, Clave, Falla)")
            else:
                try:
                    # Guardar Cliente (Upsert)
                    try:
                        supabase.table("clientes").insert({
                            "dni": dni, "nombre": nombre.upper(), "telefono": telefono, "direccion": direccion
                        }).execute()
                    except: pass
                    
                    # Guardar Ticket
                    data_t = {
                        "cliente_dni": dni, "cliente_nombre": nombre.upper(),
                        "marca": marca.upper(), "modelo": modelo.upper(),
                        "imei": imei, "contrasena": contrasena,
                        "descripcion": descripcion, "motivo": motivo,
                        "precio": precio, "fecha_entrega": str(fecha_entrega),
                        "estado": "En Taller", "created_at": datetime.now().isoformat()
                    }
                    new_ticket = supabase.table("tickets").insert(data_t).execute()
                    
                    # Guardar ID del ticket nuevo para el PDF
                    if new_ticket.data:
                        t_id = new_ticket.data[0]['id']
                        # Preparar datos para PDF
                        pdf_data = data_t.copy()
                        pdf_data['id'] = t_id
                        pdf_data['telefono'] = telefono
                        
                        st.session_state['ultimo_pdf'] = generar_ticket_pdf(pdf_data)
                        st.session_state['ultimo_ticket_id'] = t_id
                        
                        st.success(f"✅ Ticket #{t_id} Generado Correctamente")
                        st.session_state.cli_nombre = ""; st.session_state.cli_dni = "" # Limpiar
                        st.rerun() # Recargar para que aparezca en el feed
                        
                except Exception as e: st.error(f"Error crítico: {e}")

        # ZONA DE DESCARGA DE PDF (Aparece después de guardar)
        if 'ultimo_pdf' in st.session_state:
            st.success("🖨️ Ticket listo para imprimir")
            st.download_button(
                label=f"📥 Descargar Ticket #{st.session_state['ultimo_ticket_id']} (PDF)",
                data=st.session_state['ultimo_pdf'],
                file_name=f"Ticket_VillaFix_{st.session_state['ultimo_ticket_id']}.pdf",
                mime="application/pdf",
                type="secondary"
            )

    # --- COLUMNA DERECHA: LIVE FEED (HISTORIAL HOY) ---
    with col_feed:
        st.markdown("### ⏱️ Actividad de Hoy")
        st.caption(f"Ingresos del {date.today().strftime('%d/%m/%Y')}")
        
        # Filtro de búsqueda global
        search_q = st.text_input("🔎 Buscar historial antiguo...", placeholder="DNI o ID Ticket")
        
        # Lógica: Si busca, busca en todo. Si no, solo muestra hoy.
        query = supabase.table("tickets").select("*")
        
        if search_q:
            # Búsqueda global (Por DNI o ID)
            if search_q.isdigit() and len(search_q) < 6: # Asumimos ID si es corto
                query = query.eq("id", search_q)
            else:
                query = query.eq("cliente_dni", search_q)
        else:
            # Filtro solo HOY (Usamos gte = Greater Than or Equal al inicio del día)
            today_start = datetime.now().strftime('%Y-%m-%dT00:00:00')
            query = query.gte("created_at", today_start)
            
        tickets = query.order("created_at", desc=True).execute().data
        
        if not tickets:
            st.info("No hay movimientos recientes.")
        else:
            for t in tickets:
                # CARD DE TICKET (Estilo Caro)
                with st.container():
                    st.markdown(f"""
                    <div class="ticket-item">
                        <div style="display:flex; justify-content:space-between;">
                            <strong>#{t['id']} | {t['cliente_nombre']}</strong>
                            <span class="status-badge">{t['estado']}</span>
                        </div>
                        <div style="color:#64748b; font-size:0.85em; margin-top:5px;">
                            📱 {t['marca']} {t['modelo']}<br>
                            🔧 {t['motivo']} - S/ {t['precio']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Botonera de acciones
                    ca, cb = st.columns(2)
                    # Botón WhatsApp
                    tel_res = supabase.table("clientes").select("telefono").eq("dni", t['cliente_dni']).execute()
                    tel = tel_res.data[0]['telefono'] if tel_res.data else ""
                    
                    if tel:
                        url_wa = f"https://wa.me/51{tel}?text=Hola {t['cliente_nombre']}, su equipo {t['marca']} (Ticket #{t['id']}) ha ingresado a VillaFix."
                        ca.link_button("💬 WhatsApp", url_wa, use_container_width=True)
                    else:
                        ca.button("No Tel", disabled=True, key=f"btn_no_{t['id']}", use_container_width=True)
                    
                    # Botón Ver Detalles (Simulado)
                    cb.button("👁️ Ver", key=f"ver_{t['id']}", use_container_width=True)


elif selected == "Inventario":
    # (Tu código de inventario va aquí - Lo resumo para que encaje)
    st.markdown("### 📦 Inventario")
    t_ver, t_add = st.tabs(["Catálogo", "Nuevo"])
    
    with t_ver:
        q = st.text_input("Buscar producto...")
        df = pd.DataFrame(supabase.table("productos").select("*").execute().data)
        if not df.empty:
            if q: df = df[df['nombre'].str.contains(q, case=False)]
            cols = st.columns(4)
            for i, row in df.iterrows():
                with cols[i%4]:
                    with st.container(border=True):
                        if row['imagen_url']: st.image(row['imagen_url'])
                        st.write(f"**{row['nombre']}**")
                        st.caption(f"Stock: {row['stock']} | S/ {row['precio']}")

    with t_add:
        with st.form("add"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nombre"); p = c2.number_input("Precio")
            s = c2.number_input("Stock", min_value=1); f = st.file_uploader("Foto")
            if st.form_submit_button("Guardar"):
                u = subir_imagen(f) if f else None
                supabase.table("productos").insert({"nombre":n,"precio":p,"stock":s,"imagen_url":u}).execute()
                st.success("Guardado")

elif selected == "Caja & Ventas":
    st.info("🚧 Módulo de Facturación y Cierre de Caja (Próximamente)")

elif selected == "Configuración":
    st.markdown("### ⚙️ Ajustes del Sistema")
    st.write("Configuración de Logo, Usuarios y Permisos.")
