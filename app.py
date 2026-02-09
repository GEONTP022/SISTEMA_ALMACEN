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
import xlsxwriter
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="VillaFix ERP", page_icon="⚙️", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except: st.error("⚠️ Error Conexión DB"); st.stop()

# --- 3. ESTILOS PRO ---
st.markdown("""
<style>
    .stApp { background-color: #f1f5f9; }
    section[data-testid="stSidebar"] { background-color: #0f172a; }
    section[data-testid="stSidebar"] h1, h2, h3 { color: white !important; }
    
    /* INPUTS & BOTONES */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: white !important; border: 1px solid #cbd5e1; border-radius: 6px; color: #1e293b !important;
    }
    .stButton>button { border-radius: 6px; font-weight: 700; width: 100%; transition: 0.2s; }
    
    /* BOTÓN VERDE PERSONALIZADO (Para el + de agregar cliente) */
    .btn-green button { background-color: #10b981 !important; color: white !important; border: none; }
    .btn-green button:hover { background-color: #059669 !important; }

    /* TABLA REPARACIÓN */
    .rep-header { background-color: #475569; color: white; padding: 10px; border-radius: 6px 6px 0 0; font-weight: 700; font-size: 0.8em; display: flex; text-transform: uppercase; letter-spacing: 0.5px; }
    .rep-row { background-color: white; border: 1px solid #e2e8f0; border-top: none; padding: 12px; display: flex; align-items: center; transition: 0.2s; }
    .rep-row:hover { background-color: #f8fafc; border-left: 4px solid #2563EB; }
    .rep-col { flex: 1; font-size: 0.85em; color: #334155; padding: 0 8px; }
    .rep-col strong { color: #0f172a; font-weight: 800; display: block; }
    
    .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.7em; font-weight: 800; color: white; display: inline-block; text-align: center; width: 100px; }
    .bg-blue { background: #3b82f6; } .bg-green { background: #10b981; } .bg-red { background: #ef4444; } 
    
    .kpi-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #2563EB; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES ---
def buscar_dni_reniec(dni):
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd" # TOKEN REAL
    try:
        r = requests.get(f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}", headers={'Authorization': f'Bearer {token}'}, timeout=3)
        if r.status_code == 200: 
            d = r.json(); return f"{d.get('nombres','')} {d.get('apellidoPaterno','')} {d.get('apellidoMaterno','')}".strip()
    except: pass
    return None

def subir_evidencia(archivo):
    try:
        if archivo:
            nombre = f"evidencia_{datetime.now().strftime('%Y%m%d%H%M%S')}_{archivo.name}"
            supabase.storage.from_("evidencias").upload(nombre, archivo.getvalue(), {"content-type": archivo.type})
            return supabase.storage.from_("evidencias").get_public_url(nombre)
    except: return None

def generar_pdf_universal(tipo, id_doc, datos, items, montos):
    width = 80 * mm; height = 297 * mm 
    buffer = io.BytesIO(); c = canvas.Canvas(buffer, pagesize=(width, height))
    c.setFont("Helvetica-Bold", 12); c.drawCentredString(width/2, height-10*mm, "VILLAFIX S.A.C.")
    c.setFont("Helvetica", 8); c.drawCentredString(width/2, height-15*mm, "Servicio Técnico & Tecnología")
    c.line(5*mm, height-20*mm, width-5*mm, height-20*mm)
    titulo = "BOLETA VENTA" if tipo=="Venta" else ("COTIZACION" if tipo=="Cotizacion" else "ORDEN SERVICIO")
    c.setFont("Helvetica-Bold", 14); c.drawCentredString(width/2, height-30*mm, f"{titulo} #{id_doc}")
    y = height - 40*mm
    c.setFont("Helvetica", 9)
    c.drawString(5*mm, y, f"Cliente: {datos.get('nombre')}"); y-=5*mm
    c.drawString(5*mm, y, f"DNI: {datos.get('dni')}"); y-=8*mm
    c.setFont("Helvetica-Bold", 8); c.drawString(5*mm, y, "DETALLE"); c.drawRightString(width-5*mm, y, "TOTAL"); y-=5*mm
    c.setFont("Helvetica", 8)
    for item in items:
        desc = f"{item['cant']} x {item['desc']}"
        for line in textwrap.wrap(desc, 30): c.drawString(5*mm, y, line); y-=4*mm
        c.drawRightString(width-5*mm, y+4*mm, f"S/ {item['total']:.2f}"); y-=2*mm
    c.line(5*mm, y, width-5*mm, y); y-=5*mm
    c.setFont("Helvetica-Bold", 12); c.drawString(5*mm, y, "TOTAL:"); c.drawRightString(width-5*mm, y, f"S/ {montos['total']:.2f}"); y-=6*mm
    if tipo == "Reparacion":
        c.setFont("Helvetica", 10)
        c.drawString(5*mm, y, "A CUENTA:"); c.drawRightString(width-5*mm, y, f"S/ {montos['acuenta']:.2f}"); y-=5*mm
        c.drawString(5*mm, y, "SALDO:"); c.drawRightString(width-5*mm, y, f"S/ {montos['saldo']:.2f}"); y-=5*mm
    c.showPage(); c.save(); buffer.seek(0); return buffer

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

# --- 5. MODALES INTERACTIVOS ---

# A. MODAL GESTIÓN REPARACIÓN (Pagar, Anular)
@st.dialog("Gestión de Servicio")
def modal_servicio(t):
    st.markdown(f"### 🔧 Orden #{t['id']}")
    c1, c2 = st.columns(2)
    c1.info(f"Cliente: **{t['cliente_nombre']}**")
    c2.warning(f"Saldo: **S/ {t['saldo']:.2f}**")
    
    tab1, tab2, tab3, tab4 = st.tabs(["💵 Cobrar", "📸 Evidencias", "🖨️ PDF", "⚠️ Anular"])
    
    with tab1:
        if t['saldo'] <= 0: st.success("✅ Pagado")
        else:
            monto = st.number_input("Monto a Pagar", 0.0, float(t['saldo']), float(t['saldo']))
            metodo = st.selectbox("Método", ["Efectivo", "Yape", "Tarjeta"])
            if st.button("Confirmar Pago", use_container_width=True):
                n_acu = t['acuenta'] + monto; n_sal = t['precio'] - n_acu
                est = "Entregado" if n_sal == 0 else "Pendiente"
                supabase.table("tickets").update({"acuenta":n_acu, "saldo":n_sal, "estado":est, "metodo_pago":metodo}).eq("id", t['id']).execute()
                st.rerun()
    with tab2:
        c_ant, c_des = st.columns(2)
        with c_ant:
            st.caption("Antes"); 
            if t['foto_antes']: st.image(t['foto_antes'])
            else: st.info("Sin foto")
        with c_des:
            st.caption("Después"); 
            if t['foto_despues']: st.image(t['foto_despues'])
            else:
                f_up = st.file_uploader("Subir Final", key="f_up")
                if f_up and st.button("Guardar"):
                    url = subir_evidencia(f_up)
                    supabase.table("tickets").update({"foto_despues":url}).eq("id", t['id']).execute(); st.rerun()
    with tab3:
        pdf = generar_pdf_universal("Reparacion", t['id'], {"nombre":t['cliente_nombre'], "dni":t['cliente_dni']}, [{"desc":t['marca']+" "+t['modelo'], "cant":1, "total":t['precio']}], {"total":t['precio'], "acuenta":t['acuenta'], "saldo":t['saldo']})
        st.download_button("Descargar Ticket", pdf, f"Ticket_{t['id']}.pdf", "application/pdf", use_container_width=True)
    with tab4:
        if st.button("ANULAR ORDEN", type="primary"):
            supabase.table("tickets").update({"estado":"Anulado"}).eq("id", t['id']).execute(); st.rerun()

# B. MODAL AGREGAR CLIENTE (EL QUE PEDISTE)
@st.dialog("Agregar Cliente")
def modal_nuevo_cliente():
    st.markdown("### 👤 Nuevo Cliente")
    
    # Buscador DNI dentro del modal
    col_dni, col_btn = st.columns([3, 1])
    dni_val = col_dni.text_input("DNI (8 dígitos)", placeholder="Ingrese DNI")
    
    # Variables de estado temporal para este modal
    if 'temp_cli_nom' not in st.session_state: st.session_state.temp_cli_nom = ""
    
    if col_btn.button("🔍", help="Buscar en RENIEC"):
        if dni_val and len(dni_val)==8:
            nombre = buscar_dni_reniec(dni_val)
            if nombre:
                st.session_state.temp_cli_nom = nombre
                st.toast("¡Encontrado en RENIEC!")
                st.rerun() # Recarga el modal para mostrar el nombre
            else:
                st.error("No encontrado")

    # Formulario de datos
    nombre_val = st.text_input("Nombre Completo", value=st.session_state.temp_cli_nom)
    
    c1, c2 = st.columns(2)
    cel_val = c1.text_input("Celular")
    email_val = c2.text_input("Email")
    dir_val = st.text_input("Dirección")
    
    if st.button("Guardar Cliente", type="primary", use_container_width=True):
        if not dni_val or not nombre_val:
            st.error("DNI y Nombre son obligatorios")
        else:
            try:
                supabase.table("clientes").upsert({
                    "dni": dni_val, "nombre": nombre_val, "telefono": cel_val, "email": email_val, "direccion": dir_val
                }).execute()
                st.success("Cliente guardado")
                st.session_state.temp_cli_nom = "" # Limpiar
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

# --- 6. MENU LATERAL ---
with st.sidebar:
    if os.path.exists("Logo-Mockup.jpg"): st.image("Logo-Mockup.jpg", width=180)
    else: st.title("VillaFix ERP")
    
    try: users = [u['nombre'] for u in supabase.table("usuarios").select("nombre").execute().data]
    except: users = ["Admin"]
    st.session_state.user = st.selectbox("Usuario", users)
    
    menu = option_menu(None, ["Dashboard", "Recepción", "Ventas (POS)", "Cotizaciones", "Logística", "Clientes"], 
        icons=["speedometer2", "tools", "cart4", "file-text", "truck", "people"], default_index=1,
        styles={"nav-link-selected": {"background-color": "#2563EB"}})

# --- 7. MÓDULOS ---

# === DASHBOARD ===
if menu == "Dashboard":
    st.markdown("### 📊 Panel de Control")
    c1, c2, c3, c4 = st.columns(4)
    hoy = datetime.now().strftime('%Y-%m-%d')
    try:
        ventas = pd.DataFrame(supabase.table("ventas").select("*").execute().data)
        tickets = pd.DataFrame(supabase.table("tickets").select("*").execute().data)
    except: ventas = pd.DataFrame(); tickets = pd.DataFrame()
    
    pos_hoy = ventas[ventas['fecha_venta'].str.startswith(hoy)]['total'].sum() if not ventas.empty else 0
    taller_hoy = 0
    if not tickets.empty:
        t_hoy = tickets[tickets['created_at'].str.startswith(hoy)]
        for _, t in t_hoy.iterrows():
            if t['estado'] == 'Entregado': taller_hoy += t['precio']
            elif t['estado'] != 'Anulado': taller_hoy += t['acuenta']

    c1.markdown(f'<div class="kpi-card"><div class="kpi-val">S/ {pos_hoy:.2f}</div><div class="kpi-lbl">Ventas Hoy</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-val">S/ {taller_hoy:.2f}</div><div class="kpi-lbl">Taller Hoy</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-val">S/ {pos_hoy+taller_hoy:.2f}</div><div class="kpi-lbl">Caja Total</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card"><div class="kpi-val">{len(tickets[tickets["estado"]=="Pendiente"])}</div><div class="kpi-lbl">Pendientes</div></div>', unsafe_allow_html=True)
    st.divider()
    if not ventas.empty:
        st.subheader("🏆 Ventas por Vendedor")
        st.plotly_chart(px.bar(ventas.groupby('vendedor_nombre')['total'].sum().reset_index(), x='vendedor_nombre', y='total'), use_container_width=True)

# === RECEPCIÓN (CON EL BOTÓN + Y MODAL ARREGLADO) ===
elif menu == "Recepción":
    t_new, t_list = st.tabs(["✨ Nueva Recepción", "📋 Lista de Reparaciones"])
    
    with t_new:
        st.markdown("#### Datos del Cliente")
        
        # FILA DEL BUSCADOR Y EL BOTÓN VERDE +
        c_sel, c_add = st.columns([4, 0.5])
        
        with c_sel:
            try: clis = {f"{c['dni']} - {c['nombre']}": c for c in supabase.table("clientes").select("dni,nombre").execute().data}
            except: clis = {}
            sel = st.selectbox("Cliente Existente", ["Seleccionar..."] + list(clis.keys()), label_visibility="collapsed")
        
        with c_add:
            # BOTÓN VERDE QUE ABRE EL MODAL
            st.markdown('<div class="btn-green">', unsafe_allow_html=True)
            if st.button("➕", help="Agregar Nuevo Cliente"):
                modal_nuevo_cliente() # <--- LLAMADA AL MODAL
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Auto-rellenado si selecciona de la lista
        v_dni = clis[sel]['dni'] if sel != "Seleccionar..." else ""
        v_nom = clis[sel]['nombre'] if sel != "Seleccionar..." else ""

        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 1])
            dni = c1.text_input("DNI", value=v_dni, disabled=True if v_dni else False)
            nom = c2.text_input("Nombre", value=v_nom, disabled=True if v_nom else False)
            cel = c3.text_input("Celular")
            
            if dni: 
                bd = supabase.table("clientes").select("fecha_nacimiento").eq("dni", dni).execute().data
                if bd and bd[0]['fecha_nacimiento']:
                    if datetime.strptime(bd[0]['fecha_nacimiento'], '%Y-%m-%d').month == date.today().month:
                        st.success("🎂 ¡Cliente cumple años este mes!")

        st.markdown("#### Datos del Equipo & Evidencia")
        with st.container(border=True):
            r1, r2, r3 = st.columns(3)
            mar = r1.selectbox("Marca", ["Samsung", "Apple", "Xiaomi", "Motorola", "Otro"])
            mod = r2.text_input("Modelo")
            mot = r3.selectbox("Motivo", ["Reparación", "Garantía", "Mantenimiento"])
            r4, r5 = st.columns(2)
            falla = r4.text_area("Falla Reportada")
            foto = r5.file_uploader("📸 Foto Recepción", type=['png', 'jpg'])
            r6, r7, r8 = st.columns(3)
            costo = r6.number_input("Costo Total", 0.0)
            acuenta = r7.number_input("A Cuenta", 0.0)
            f_ent = r8.date_input("Entrega Estimada", date.today())

        if st.button("💾 GENERAR ORDEN", type="primary"):
            url_foto = subir_evidencia(foto) if foto else None
            # Asegurar cliente si es manual
            if not v_dni: supabase.table("clientes").upsert({"dni":dni, "nombre":nom, "telefono":cel}).execute()
            
            supabase.table("tickets").insert({
                "cliente_dni":dni, "cliente_nombre":nom, "vendedor_nombre":st.session_state.user,
                "marca":mar, "modelo":mod, "motivo":mot, "falla_reportada":falla,
                "precio":costo, "acuenta":acuenta, "saldo":costo-acuenta,
                "foto_antes":url_foto, "fecha_entrega":str(f_ent), "estado":"Pendiente"
            }).execute()
            st.success("Orden Creada"); st.rerun()

    with t_list:
        with st.container():
            c_s, c_e = st.columns([4, 1])
            search = c_s.text_input("🔍 Buscar...", placeholder="Cliente, Ticket, DNI")
            q = supabase.table("tickets").select("*").order("created_at", desc=True)
            if search: q = q.ilike("cliente_nombre", f"%{search}%")
            data = q.execute().data
            if data:
                exc = to_excel(pd.DataFrame(data))
                c_e.download_button("📗 Excel", exc, "data.xlsx", use_container_width=True)

        st.markdown('<div class="rep-header"><div style="width:50px">⚙️</div><div style="width:100px">Estado</div><div style="flex:1">Cliente</div><div style="flex:1">Información</div><div style="flex:1">Repuestos</div><div style="flex:1;text-align:right">Montos</div><div style="flex:1;text-align:right">Fechas</div></div>', unsafe_allow_html=True)
        
        if data:
            for t in data:
                if t['estado']=='Anulado': bg="bg-red"; stt="ANULADO"
                elif t['saldo']<=0: bg="bg-green"; stt="PAGADO"
                else: bg="bg-blue"; stt="TALLER"
                
                f_ing = datetime.fromisoformat(t['created_at']).strftime("%d-%m")
                nom_cli = t['cliente_nombre'] if t['cliente_nombre'] else "Desconocido"
                
                c_btn, c_info = st.columns([0.8, 11])
                with c_btn:
                    st.write("")
                    if st.button("⚙️", key=f"g_{t['id']}", help="Gestionar"): modal_servicio(t)
                
                with c_info:
                    st.markdown(f"""
                    <div class="rep-row">
                        <div style="width:100px"><span class="badge {bg}">{stt}</span></div>
                        <div class="rep-col"><strong>{nom_cli.split()[0]}</strong><small>{t['cliente_dni']}</small></div>
                        <div class="rep-col"><strong>{t['motivo']}</strong><small>{t['marca']} {t['modelo']}</small></div>
                        <div class="rep-col"><small>Sin repuestos</small></div>
                        <div class="rep-col" style="text-align:right"><strong style="color:{'#10b981' if t['saldo']<=0 else '#ef4444'}">Resta: {t['saldo']}</strong><small>Total: {t['precio']}</small></div>
                        <div class="rep-col" style="text-align:right"><strong>Ing: {f_ing}</strong><small>Ent: {t['fecha_entrega']}</small></div>
                    </div>
                    """, unsafe_allow_html=True)

# === VENTAS / POS ===
elif menu == "Ventas (POS)":
    st.markdown("### 🛒 Punto de Venta")
    if 'cart' not in st.session_state: st.session_state.cart = []
    c_cat, c_cart = st.columns([1.5, 1])
    with c_cat:
        prods = supabase.table("productos").select("*").gt("stock", 0).execute().data
        for p in prods:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{p['nombre']}**"); c1.caption(f"Stock: {p['stock']} | S/ {p['precio']}")
                if c2.button("➕", key=f"p_{p['id']}"): st.session_state.cart.append(p); st.toast("Agregado")
    with c_cart:
        if st.session_state.cart:
            df = pd.DataFrame(st.session_state.cart)
            res = df.groupby(['id', 'nombre', 'precio']).size().reset_index(name='cant')
            res['total'] = res['precio']*res['cant']
            st.dataframe(res[['nombre', 'cant', 'total']], hide_index=True)
            tot = res['total'].sum()
            st.markdown(f"### Total: S/ {tot:.2f}")
            if st.button("✅ COBRAR", type="primary"):
                vid = supabase.table("ventas").insert({"total":tot, "vendedor_nombre":st.session_state.user}).execute().data[0]['id']
                for _, r in res.iterrows():
                    curr = supabase.table("productos").select("stock").eq("id", r['id']).execute().data[0]['stock']
                    supabase.table("productos").update({"stock":curr-r['cant']}).eq("id", r['id']).execute()
                st.session_state.cart = []; st.success("Venta OK"); st.rerun()

# === COTIZACIONES ===
elif menu == "Cotizaciones":
    st.markdown("### 📄 Cotizador")
    c1, c2 = st.columns(2)
    cli = c1.text_input("Cliente"); ruc = c2.text_input("RUC/DNI")
    det = st.text_area("Detalles"); tot = st.number_input("Total Cotizado", 0.0)
    if st.button("Generar PDF"):
        pdf = generar_pdf_universal("Cotizacion", "TEMP", {"nombre":cli, "dni":ruc}, [{"desc":det, "cant":1, "total":tot}], {"total":tot})
        st.download_button("Descargar PDF", pdf, "Cotizacion.pdf")

# === LOGÍSTICA ===
elif menu == "Logística":
    st.markdown("### 🚚 Logística")
    t1, t2 = st.tabs(["Movimientos", "Nueva Guía"])
    with t1: st.dataframe(pd.DataFrame(supabase.table("movimientos_logistica").select("*").execute().data))
    with t2:
        dest = st.text_input("Destino"); mot = st.selectbox("Motivo", ["Traslado", "Exportación"])
        if st.button("Generar Guía"):
            supabase.table("movimientos_logistica").insert({"tipo":"Salida", "destino":dest, "detalle":mot}).execute()
            st.success("Registrado")

# === CLIENTES ===
elif menu == "Clientes":
    st.markdown("### 👥 CRM Clientes")
    c1, c2 = st.columns(2)
    d = c1.text_input("DNI"); n = c2.text_input("Nombre"); f = c1.date_input("Cumpleaños")
    if st.button("Guardar Cliente"):
        supabase.table("clientes").upsert({"dni":d, "nombre":n, "fecha_nacimiento":str(f)}).execute()
        st.success("Guardado")
    st.divider()
    b = st.text_input("Buscar DNI Historial")
    if b: st.dataframe(supabase.table("tickets").select("*").eq("cliente_dni", b).execute().data)




