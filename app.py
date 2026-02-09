import streamlit as st
import pandas as pd
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

# --- 3. ESTILOS CSS ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1, h2, h3, h4 { color: #1e293b !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
        background-color: white !important; color: #1e293b !important; border-radius: 8px; border: 1px solid #cbd5e1;
    }
    .metric-card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #2563EB;
        text-align: center;
    }
    .big-money { font-size: 24px; font-weight: bold; color: #16a34a; }
    .big-debt { font-size: 24px; font-weight: bold; color: #dc2626; }
    
    /* Ticket Feed */
    .ticket-item { background: white; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px; }
    .status-badge { background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES ---

def generar_ticket_pdf(t):
    """Genera PDF con desglose financiero"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Header
    c.setFillColorRGB(0.1, 0.2, 0.4)
    c.rect(0, height - 100, width, 100, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(30, height - 50, "VILLAFIX REPARACIONES")
    c.setFont("Helvetica", 12)
    c.drawString(30, height - 70, "Especialistas en Hardware y Software")
    c.drawRightString(width - 30, height - 50, f"TICKET #{t['id']}")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 30, height - 70, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Cuerpo
    c.setFillColor(colors.black)
    y = height - 150
    
    # Cliente
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y, "CLIENTE")
    c.line(30, y-5, width-30, y-5); y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(30, y, f"Nombre: {t['cliente_nombre']}")
    c.drawString(300, y, f"DNI: {t['cliente_dni']}")
    y -= 15
    c.drawString(30, y, f"Contacto: {t.get('telefono', '')}")
    y -= 30
    
    # Equipo
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y, "EQUIPO")
    c.line(30, y-5, width-30, y-5); y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(30, y, f"Modelo: {t['marca']} {t['modelo']}")
    c.drawString(300, y, f"IMEI: {t['imei']}")
    y -= 15
    c.drawString(30, y, f"Motivo: {t['motivo']}")
    c.drawString(300, y, f"Pass: {t['contrasena']}")
    y -= 30
    
    # Falla
    c.setFillColor(colors.gray)
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(30, y, f"Detalle: {t['descripcion']}")
    y -= 40
    
    # --- ZONA FINANCIERA (La parte importante) ---
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.setFillColorRGB(0.96, 0.96, 0.96)
    c.rect(30, y-80, width-60, 90, fill=1) # Caja gris
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y-20, "COSTO TOTAL:")
    c.drawRightString(width-50, y-20, f"S/ {t['precio']:.2f}")
    
    c.setFillColor(colors.darkgreen)
    c.drawString(50, y-40, "A CUENTA (ADELANTO):")
    c.drawRightString(width-50, y-40, f"- S/ {t['acuenta']:.2f}")
    
    c.setFillColor(colors.red)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y-70, "SALDO PENDIENTE:")
    c.drawRightString(width-50, y-70, f"S/ {t['saldo']:.2f}")
    
    # Info Pago
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    y -= 100
    pago_info = f"Método: {t['metodo_pago']}"
    if t['cod_operacion']: pago_info += f" | Op: {t['cod_operacion']}"
    c.drawString(50, y+15, pago_info)
    
    y -= 50
    # QR
    qr = qrcode.make(f"TICKET-{t['id']}|SALDO:{t['saldo']}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        qr.save(tmp.name)
        c.drawImage(tmp.name, width-130, y-60, 90, 90)
        os.unlink(tmp.name)

    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(30, 50, "Gracias por su preferencia. Garantía válida solo con este ticket.")
    
    c.save()
    buffer.seek(0)
    return buffer

def consultar_dni_reniec(dni):
    """Búsqueda Híbrida"""
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

# --- 5. APP PRINCIPAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/6024/6024190.png", width=50)
    st.markdown("### VillaFix OS")
    selected = option_menu(
        menu_title=None,
        options=["Recepción", "Inventario", "Caja", "Config"],
        icons=["hdd-network", "box-seam", "wallet2", "gear"],
        default_index=0,
    )

# --- ESTADO DE FLUJO (STEP) ---
if 'recepcion_step' not in st.session_state: st.session_state.recepcion_step = 1 # 1: Datos, 2: Pago, 3: Ticket
if 'temp_data' not in st.session_state: st.session_state.temp_data = {}

if selected == "Recepción":
    col_izq, col_der = st.columns([1.5, 1])

    with col_izq:
        # === PASO 1: DATOS (FORMULARIO) ===
        if st.session_state.recepcion_step == 1:
            st.markdown("### 🛠️ Nueva Recepción")
            st.caption("Paso 1: Datos del Cliente y Equipo")
            
            # Variables Locales
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
            tel = c1.text_input("Teléfono (Opcional)")
            dir_cli = c2.text_input("Dirección (Opcional)")
            
            st.markdown("---")
            c_eq1, c_eq2 = st.columns(2)
            marca = c_eq1.text_input("Marca *")
            modelo = c_eq1.text_input("Modelo *")
            motivo = c_eq1.selectbox("Servicio", ["Reparación", "Mantenimiento", "Software", "Garantía"])
            imei = c_eq2.text_input("IMEI/Serie")
            passw = c_eq2.text_input("Contraseña *", placeholder="Patrón o Clave")
            precio = c_eq2.number_input("Costo Total (S/)", min_value=0.0, step=5.0)
            desc = st.text_area("Falla / Detalles *")
            fecha_ent = st.date_input("Entrega", min_value=date.today())

            if st.button("➡️ CONTINUAR AL PAGO", type="primary", use_container_width=True):
                if not dni or not nombre or not marca or not modelo or not passw:
                    st.error("Faltan datos obligatorios")
                else:
                    # Guardamos temporalmente en memoria
                    st.session_state.temp_data = {
                        "dni": dni, "nombre": nombre.upper(), "tel": tel, "dir": dir_cli,
                        "marca": marca.upper(), "modelo": modelo.upper(), "imei": imei,
                        "pass": passw, "motivo": motivo, "precio": precio, 
                        "desc": desc, "fecha": str(fecha_ent)
                    }
                    st.session_state.recepcion_step = 2 # Pasamos al pago
                    st.rerun()

        # === PASO 2: VENTANA DE PAGO (COBRANZA) ===
        elif st.session_state.recepcion_step == 2:
            data = st.session_state.temp_data
            st.markdown(f"### 💰 Caja Rápida: {data['nombre']}")
            st.info("Ingrese el monto a cuenta para cerrar el ticket.")
            
            # Tarjeta de Resumen Financiero
            c_tot, c_acu, c_res = st.columns(3)
            c_tot.metric("Total a Pagar", f"S/ {data['precio']:.2f}")
            
            # Formulario de Pago
            with st.container(border=True):
                acuenta = st.number_input("Monto a Cuenta (Adelanto) *", min_value=0.0, max_value=data['precio'], step=5.0)
                
                # Cálculo dinámico del saldo
                saldo = data['precio'] - acuenta
                c_acu.metric("Deja a Cuenta", f"S/ {acuenta:.2f}")
                c_res.metric("Saldo Pendiente", f"S/ {saldo:.2f}", delta_color="inverse" if saldo > 0 else "normal")
                
                st.write("")
                cm, co = st.columns(2)
                metodo = cm.selectbox("Método de Pago", ["Yape", "Plin", "Efectivo", "Tarjeta", "Transferencia"])
                operacion = co.text_input("N° Operación (Opcional)", placeholder="Ej: 123456")
                
                if st.button("💾 CONFIRMAR Y GENERAR TICKET", type="primary", use_container_width=True):
                    try:
                        # 1. Guardar Cliente
                        try:
                            supabase.table("clientes").insert({
                                "dni": data['dni'], "nombre": data['nombre'], "telefono": data['tel'], "direccion": data['dir']
                            }).execute()
                        except: pass 
                        
                        # 2. Guardar Ticket Final
                        ticket_final = {
                            "cliente_dni": data['dni'], "cliente_nombre": data['nombre'],
                            "marca": data['marca'], "modelo": data['modelo'],
                            "imei": data['imei'], "contrasena": data['pass'],
                            "motivo": data['motivo'], "descripcion": data['desc'],
                            "precio": data['precio'], "fecha_entrega": data['fecha'],
                            "acuenta": acuenta, "saldo": saldo, # <--- DATOS FINANCIEROS
                            "metodo_pago": metodo, "cod_operacion": operacion,
                            "estado": "Pendiente"
                        }
                        res_t = supabase.table("tickets").insert(ticket_final).execute()
                        
                        # 3. Generar PDF
                        if res_t.data:
                            t_id = res_t.data[0]['id']
                            # Agregamos datos extra para el PDF
                            ticket_final['id'] = t_id
                            ticket_final['telefono'] = data['tel']
                            
                            st.session_state.ultimo_pdf = generar_ticket_pdf(ticket_final)
                            st.session_state.ultimo_id = t_id
                            
                            st.session_state.recepcion_step = 3 # Éxito
                            st.rerun()
                            
                    except Exception as e: st.error(f"Error: {e}")
            
            if st.button("⬅️ Volver a editar datos"):
                st.session_state.recepcion_step = 1
                st.rerun()

        # === PASO 3: ÉXITO Y DESCARGA ===
        elif st.session_state.recepcion_step == 3:
            st.markdown("### 🎉 ¡Registro Exitoso!")
            st.balloons()
            
            st.success(f"Ticket #{st.session_state.ultimo_id} generado correctamente.")
            
            c_down, c_new = st.columns(2)
            
            with c_down:
                st.download_button(
                    label="📥 DESCARGAR TICKET PDF",
                    data=st.session_state.ultimo_pdf,
                    file_name=f"Ticket_{st.session_state.ultimo_id}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
            
            with c_new:
                if st.button("➕ NUEVO SERVICIO", use_container_width=True):
                    st.session_state.recepcion_step = 1
                    st.session_state.temp_data = {}
                    st.rerun()

    # --- COLUMNA DERECHA: LIVE FEED ---
    with col_der:
        st.markdown("### ⏱️ Hoy")
        # Filtro simple por tickets del día
        today = datetime.now().strftime('%Y-%m-%dT00:00:00')
        tickets = supabase.table("tickets").select("*").gte("created_at", today).order("created_at", desc=True).execute().data
        
        if tickets:
            for t in tickets:
                st.markdown(f"""
                <div class="ticket-item">
                    <b>#{t['id']} | {t['cliente_nombre']}</b><br>
                    <span style='font-size:0.9em'>{t['marca']} - {t['motivo']}</span><br>
                    <span style='color:green'>A cuenta: S/ {t['acuenta']}</span> | <span style='color:red'>Debe: S/ {t['saldo']}</span>
                </div>
                """, unsafe_allow_html=True)
        else: st.info("Sin ingresos hoy.")

elif selected == "Inventario":
    st.info("Módulo Inventario")

elif selected == "Caja":
    st.info("Módulo Caja")
