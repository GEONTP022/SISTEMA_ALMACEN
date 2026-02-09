import streamlit as st
import pandas as pd
import plotly.express as px
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

# --- 3. ESTILOS PRO (DISEÑO VIDEO + TABLA AVANZADA) ---
st.markdown("""
<style>
    .stApp { background-color: #f1f5f9; }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] { background-color: #0f172a; }
    section[data-testid="stSidebar"] h1, h2, h3 { color: white !important; }
    
    /* --- TABLA REPARACIÓN ESTILO "VILLAFIX PRO" --- */
    .rep-header {
        background-color: #475569; color: white; padding: 10px; border-radius: 6px 6px 0 0;
        font-weight: 700; font-size: 0.8em; display: flex; text-transform: uppercase; letter-spacing: 0.5px;
    }
    
    .rep-row {
        background-color: white; border: 1px solid #e2e8f0; border-top: none;
        padding: 12px; display: flex; align-items: center; transition: 0.2s;
    }
    .rep-row:hover { background-color: #f8fafc; border-left: 4px solid #2563EB; }
    
    .rep-col { flex: 1; font-size: 0.85em; color: #334155; padding: 0 8px; }
    .rep-col strong { color: #0f172a; font-weight: 800; display: block; }
    .rep-col small { color: #64748b; font-size: 0.9em; display: block; margin-top: 2px; }
    
    /* BADGES */
    .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.7em; font-weight: 800; color: white; display: inline-block; text-align: center; width: 100px; }
    .bg-blue { background: #3b82f6; } .bg-green { background: #10b981; } 
    .bg-red { background: #ef4444; } .bg-orange { background: #f59e0b; }

    /* BOTONES Y TARJETAS */
    .kpi-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #2563EB; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
    .stButton>button { border-radius: 6px; font-weight: 700; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES ---
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
    c.drawString(5*mm, y, f"DNI: {datos.get('dni')}"); y-=5*mm
    c.drawString(5*mm, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}"); y-=8*mm
    
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

def buscar_dni(dni):
    token = "sk_13243.XjdL5hswUxab5zQwW5mcWr2OW3VDfNkd"
    try:
        r = requests.get(f"https://api.apis.net.pe/v2/reniec/dni?numero={dni}", headers={'Authorization': f'Bearer {token}'}, timeout=3)
        if r.status_code == 200: 
            d = r.json(); return f"{d.get('nombres','')} {d.get('apellidoPaterno','')} {d.get('apellidoMaterno','')}".strip()
    except: pass
    return None

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

# --- 5. MODALES DE GESTIÓN (TIPO IMAGEN) ---
@st.dialog("Gestión de Reparación")
def modal_gestion(t):
    st.markdown(f"### ⚙️ Orden #{t['id']}")
    
    # Resumen Superior
    c1, c2, c3 = st.columns(3)
    c1.info(f"Cliente: {t['cliente_nombre']}")
    c2.write(f"📱 **{t['marca']} {t['modelo']}**")
    if t['saldo']>0: c3.error(f"Debe: S/ {t['saldo']}")
    else: c3.success("Pagado")

    # Pestañas de Acción
    tab1, tab2, tab3, tab4 = st.tabs(["💰 Pagar", "📸 Evidencias", "📄 Ticket", "🚫 Anular"])

    with tab1: # PAGAR
        if t['saldo'] <= 0: st.success("✅ Orden cancelada en su totalidad.")
        else:
            monto = st.number_input("Monto a Pagar", 0.0, float(t['saldo']), float(t['saldo']))
            metodo = st.selectbox("Método", ["Efectivo", "Yape", "Tarjeta"])
            if st.button("Confirmar Pago", use_container_width=True):
                n_acu = t['acuenta'] + monto; n_sal = t['precio'] - n_acu
                est = "Entregado" if n_sal == 0 else "Pendiente"
                supabase.table("tickets").update({"acuenta":n_acu, "saldo":n_sal, "estado":est, "metodo_pago":metodo}).eq("id", t['id']).execute()
                st.rerun()

    with tab2: # EVIDENCIAS (FOTOS)
        c_a, c_d = st.columns(2)
        with c_a:
            st.caption("Antes (Ingreso)")
            if t['foto_antes']: st.image(t['foto_antes'])
            else: st.info("Sin foto")
        with c_d:
            st.caption("Después (Salida)")
            if t['foto_despues']: st.image(t['foto_despues'])
            else:
                up = st.file_uploader("Subir foto final", key="f_up")
                if up and st.button("Guardar Foto"):
                    url = subir_evidencia(up)
                    supabase.table("tickets").update({"foto_despues":url}).eq("id", t['id']).execute()
                    st.rerun()

    with tab3: # PDF
        pdf = generar_pdf_universal("Reparacion", t['id'], {"nombre":t['cliente_nombre'], "dni":t['cliente_dni']}, [{"desc":t['marca'], "cant":1, "total":t['precio']}], {"total":t['precio'], "acuenta":t['acuenta'], "saldo":t['saldo']})
        st.download_button("Descargar PDF", pdf, f"Ticket_{t['id']}.pdf", "application/pdf", use_container_width=True)

    with tab4: # ANULAR
        st.warning("¿Seguro de anular? El dinero se restará de la caja.")
        if st.button("CONFIRMAR ANULACIÓN", type="primary"):
            supabase.table("tickets").update({"estado":"Anulado", "saldo":0}).eq("id", t['id']).execute()
            st.rerun()

# --- 6. BARRA LATERAL ---
with st.sidebar:
    # LOGO (Si existe el archivo, lo muestra)
    if os.path.exists("Logo-Mockup.jpg"):
        st.image("Logo-Mockup.jpg", width=180)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/900/900782.png", width=60)
        st.markdown("### VillaFix OS")

    # SELECCIÓN DE USUARIO (REQ #6)
    try: users = [u['nombre'] for u in supabase.table("usuarios").select("nombre").execute().data]
    except: users = ["Admin"]
    st.session_state.user = st.selectbox("Usuario Activo", users)

    menu = option_menu(None, ["Dashboard", "Recepción", "Ventas (POS)", "Cotizaciones", "Logística", "Clientes"], 
        icons=["speedometer2", "tools", "cart4", "file-text", "truck", "people"], default_index=1,
        styles={"nav-link-selected": {"background-color": "#2563EB"}})

# --- 7. MÓDULOS ---

# === DASHBOARD ===
if menu == "Dashboard":
    st.markdown("### 📊 Tablero de Comando")
    c1, c2, c3, c4 = st.columns(4)
    
    # Datos Reales
    hoy = datetime.now().strftime('%Y-%m-%d')
    try:
        ventas = pd.DataFrame(supabase.table("ventas").select("*").execute().data)
        tickets = pd.DataFrame(supabase.table("tickets").select("*").execute().data)
    except: ventas = pd.DataFrame(); tickets = pd.DataFrame()
    
    # Cálculos
    pos_hoy = ventas[ventas['fecha_venta'].str.startswith(hoy)]['total'].sum() if not ventas.empty else 0
    taller_hoy = 0
    if not tickets.empty:
        # Sumar adelantos de pendientes + total de entregados HOY
        t_hoy = tickets[tickets['created_at'].str.startswith(hoy)]
        for _, t in t_hoy.iterrows():
            if t['estado'] == 'Entregado': taller_hoy += t['precio']
            elif t['estado'] != 'Anulado': taller_hoy += t['acuenta']

    c1.markdown(f'<div class="kpi-card"><div class="kpi-val">S/ {pos_hoy:.2f}</div><div class="kpi-lbl">Ventas Hoy</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-val">S/ {taller_hoy:.2f}</div><div class="kpi-lbl">Taller Hoy</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-val">S/ {pos_hoy+taller_hoy:.2f}</div><div class="kpi-lbl">Caja Total</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card"><div class="kpi-val">{len(tickets[tickets["estado"]=="Pendiente"])}</div><div class="kpi-lbl">Pendientes</div></div>', unsafe_allow_html=True)

    st.divider()
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("🏆 Ventas por Vendedor")
        if not ventas.empty:
            fig = px.bar(ventas.groupby('vendedor_nombre')['total'].sum().reset_index(), x='vendedor_nombre', y='total')
            st.plotly_chart(fig, use_container_width=True)

# === RECEPCIÓN (EL NÚCLEO) ===
elif menu == "Recepción":
    t_new, t_list = st.tabs(["✨ Nueva Recepción", "📋 Lista de Reparaciones"])
    
    with t_new:
        st.markdown("#### Datos del Cliente")
        c_sel, x = st.columns([3, 1])
        try: clis = {f"{c['dni']} - {c['nombre']}": c for c in supabase.table("clientes").select("dni,nombre").execute().data}
        except: clis = {}
        sel = c_sel.selectbox("Cliente", ["Nuevo"] + list(clis.keys()))
        
        v_dni = clis[sel]['dni'] if sel != "Nuevo" else ""
        v_nom = clis[sel]['nombre'] if sel != "Nuevo" else ""

        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 1])
            dni = c1.text_input("DNI", value=v_dni)
            if dni and len(dni)==8 and not v_nom: 
                if n := buscar_dni(dni): v_nom = n; st.rerun()
            nom = c2.text_input("Nombre", value=v_nom)
            cel = c3.text_input("Celular")
            
            # REQ #8: Cumpleaños
            if dni:
                c = supabase.table("clientes").select("fecha_nacimiento").eq("dni", dni).execute().data
                if c and c[0]['fecha_nacimiento']:
                    if datetime.strptime(c[0]['fecha_nacimiento'], '%Y-%m-%d').month == date.today().month:
                        st.success("🎂 ¡Cliente cumple años este mes! Ofertar descuento.")

        st.markdown("#### Datos del Equipo & Evidencia")
        with st.container(border=True):
            r1, r2, r3 = st.columns(3)
            mar = r1.selectbox("Marca", ["Samsung", "Apple", "Xiaomi", "Motorola", "Otro"])
            mod = r2.text_input("Modelo")
            mot = r3.selectbox("Motivo", ["Reparación", "Garantía", "Mantenimiento"])
            
            r4, r5 = st.columns(2)
            falla = r4.text_area("Falla Reportada")
            # REQ #12: Evidencia Inicial
            foto = r5.file_uploader("📸 Foto Estado Inicial", type=['png', 'jpg'])
            
            r6, r7, r8 = st.columns(3)
            costo = r6.number_input("Costo Total", 0.0)
            acuenta = r7.number_input("A Cuenta", 0.0)
            f_ent = r8.date_input("Entrega Estimada", date.today())

        if st.button("💾 GENERAR ORDEN", type="primary"):
            url_foto = subir_evidencia(foto) if foto else None
            supabase.table("clientes").upsert({"dni":dni, "nombre":nom, "telefono":cel}).execute()
            supabase.table("tickets").insert({
                "cliente_dni":dni, "cliente_nombre":nom, "vendedor_nombre":st.session_state.user,
                "marca":mar, "modelo":mod, "motivo":mot, "falla_reportada":falla,
                "precio":costo, "acuenta":acuenta, "saldo":costo-acuenta,
                "foto_antes":url_foto, "fecha_entrega":str(f_ent), "estado":"Pendiente"
            }).execute()
            st.success("Orden Creada"); st.rerun()

    with t_list:
        # BARRA HERRAMIENTAS
        with st.container():
            c_s, c_e = st.columns([4, 1])
            search = c_s.text_input("🔍 Buscar...", placeholder="Cliente, Ticket, DNI")
            q = supabase.table("tickets").select("*").order("created_at", desc=True)
            if search: q = q.ilike("cliente_nombre", f"%{search}%")
            data = q.execute().data
            if data:
                exc = to_excel(pd.DataFrame(data))
                c_e.download_button("📗 Excel", exc, "data.xlsx", use_container_width=True)

        # TABLA ESTILO VILLAFIX PRO
        st.markdown('<div class="rep-header"><div style="width:50px">⚙️</div><div style="width:100px">Estado</div><div style="flex:1">Cliente</div><div style="flex:1">Información</div><div style="flex:1">Repuestos</div><div style="flex:1;text-align:right">Montos</div><div style="flex:1;text-align:right">Fechas</div></div>', unsafe_allow_html=True)
        
        if data:
            for t in data:
                if t['estado']=='Anulado': bg="bg-red"; stt="ANULADO"
                elif t['saldo']<=0: bg="bg-green"; stt="PAGADO"
                else: bg="bg-blue"; stt="TALLER"
                
                f_ing = datetime.fromisoformat(t['created_at']).strftime("%d-%m")
                
                c_btn, c_info = st.columns([0.8, 11])
                with c_btn:
                    st.write("")
                    if st.button("⚙️", key=f"g_{t['id']}", help="Gestionar"): modal_gestion(t)
                
                with c_info:
                    st.markdown(f"""
                    <div class="rep-row">
                        <div style="width:100px"><span class="badge {bg}">{stt}</span></div>
                        <div class="rep-col">
                            <strong>{t['cliente_nombre'].split()[0]}</strong>
                            <small>{t['cliente_dni']}</small>
                        </div>
                        <div class="rep-col">
                            <strong>{t['motivo']}</strong>
                            <small>{t['marca']} {t['modelo']}</small>
                        </div>
                        <div class="rep-col"><small>Sin repuestos</small></div>
                        <div class="rep-col" style="text-align:right">
                            <strong style="color:{'#10b981' if t['saldo']<=0 else '#ef4444'}">Resta: {t['saldo']}</strong>
                            <small>Total: {t['precio']}</small>
                        </div>
                        <div class="rep-col" style="text-align:right">
                            <strong>Ing: {f_ing}</strong>
                            <small>Ent: {t['fecha_entrega']}</small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# === VENTAS / POS ===
elif menu == "Ventas (POS)":
    st.markdown("### 🛒 Punto de Venta")
    if 'cart' not in st.session_state: st.session_state.cart = []
    
    c_cat, c_cart = st.columns([1.5, 1])
    with c_cat:
        st.markdown("#### Catálogo")
        prods = supabase.table("productos").select("*").gt("stock", 0).execute().data
        for p in prods:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{p['nombre']}**"); c1.caption(f"Stock: {p['stock']} | S/ {p['precio']}")
                if c2.button("➕", key=f"p_{p['id']}"): st.session_state.cart.append(p); st.toast("Agregado")
    
    with c_cart:
        st.markdown("#### Ticket Actual")
        if st.session_state.cart:
            df = pd.DataFrame(st.session_state.cart)
            res = df.groupby(['id', 'nombre', 'precio']).size().reset_index(name='cant')
            res['total'] = res['precio']*res['cant']
            st.dataframe(res[['nombre', 'cant', 'total']], hide_index=True)
            tot = res['total'].sum()
            st.markdown(f"### Total: S/ {tot:.2f}")
            if st.button("✅ COBRAR", type="primary"):
                vid = supabase.table("ventas").insert({"total":tot, "vendedor_nombre":st.session_state.user}).execute().data[0]['id']
                for _, r in res.iterrows(): # Mover stock
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
        st.download_button("Descargar", pdf, "Cotizacion.pdf")

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
    st.markdown("#### Historial de Reparaciones")
    b = st.text_input("Buscar DNI Historial")
    if b: st.dataframe(supabase.table("tickets").select("*").eq("cliente_dni", b).execute().data)
