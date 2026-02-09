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

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="VillaFix ERP", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")

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
    
    /* SIDEBAR PRO */
    section[data-testid="stSidebar"] { background-color: #0f172a; }
    section[data-testid="stSidebar"] h1, h2, h3 { color: white !important; }
    
    /* TARJETAS KPI */
    .kpi-card {
        background: white; padding: 20px; border-radius: 12px;
        border-left: 5px solid #2563EB; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center;
    }
    .kpi-val { font-size: 24px; font-weight: 800; color: #1e293b; }
    .kpi-lbl { font-size: 12px; font-weight: 700; color: #64748b; text-transform: uppercase; }

    /* TABLA REPARACIÓN PRO */
    .rep-header {
        background-color: #334155; color: white; padding: 12px; border-radius: 8px 8px 0 0;
        font-weight: 700; font-size: 0.85em; display: flex; text-transform: uppercase;
    }
    .rep-row {
        background-color: white; border: 1px solid #e2e8f0; border-top: none;
        padding: 12px; display: flex; align-items: center; transition: 0.2s;
    }
    .rep-row:hover { background-color: #f8fafc; border-left: 4px solid #2563EB; }
    
    .badge { padding: 3px 10px; border-radius: 12px; font-size: 0.7em; font-weight: 800; color: white; min-width: 80px; text-align: center; }
    .bg-blue { background: #3b82f6; } .bg-green { background: #10b981; } .bg-red { background: #ef4444; } .bg-orange { background: #f59e0b; }

    .stButton>button { border-radius: 6px; font-weight: 700; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES ---
def subir_archivo(archivo, bucket="evidencias"):
    try:
        if archivo:
            f_name = f"img_{datetime.now().strftime('%Y%m%d%H%M%S')}_{archivo.name}"
            supabase.storage.from_(bucket).upload(f_name, archivo.getvalue(), {"content-type": archivo.type})
            return supabase.storage.from_(bucket).get_public_url(f_name)
    except: return None

def generar_pdf_universal(tipo, id_doc, datos, items, montos):
    width = 80 * mm; height = 297 * mm 
    buffer = io.BytesIO(); c = canvas.Canvas(buffer, pagesize=(width, height))
    
    # Encabezado
    c.setFont("Helvetica-Bold", 12); c.drawCentredString(width/2, height-10*mm, "VILLAFIX IMPORT S.A.C.")
    c.setFont("Helvetica", 8); c.drawCentredString(width/2, height-15*mm, "RUC: 20601234567 - Lima, Perú")
    c.line(5*mm, height-20*mm, width-5*mm, height-20*mm)
    
    # Datos Doc
    titulo = "BOLETA" if tipo=="Venta" else ("COTIZACION" if tipo=="Cotizacion" else "ORDEN SERVICIO")
    c.setFont("Helvetica-Bold", 14); c.drawCentredString(width/2, height-30*mm, f"{titulo} #{id_doc}")
    
    y = height - 40*mm
    c.setFont("Helvetica", 9)
    c.drawString(5*mm, y, f"Cliente: {datos.get('nombre')}"); y-=5*mm
    c.drawString(5*mm, y, f"DNI/RUC: {datos.get('dni')}"); y-=5*mm
    c.drawString(5*mm, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}"); y-=8*mm
    
    # Detalle
    c.setFont("Helvetica-Bold", 9); c.drawString(5*mm, y, "DETALLE"); c.drawRightString(width-5*mm, y, "TOTAL"); y-=5*mm
    c.setFont("Helvetica", 9)
    for item in items:
        # item: {desc, cant, total}
        c.drawString(5*mm, y, f"{item['cant']} x {item['desc'][:25]}"); 
        c.drawRightString(width-5*mm, y, f"S/ {item['total']:.2f}"); y-=5*mm
    
    c.line(5*mm, y, width-5*mm, y); y-=5*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(5*mm, y, "TOTAL:"); c.drawRightString(width-5*mm, y, f"S/ {montos['total']:.2f}"); y-=6*mm
    
    if tipo == "Reparacion":
        c.setFont("Helvetica", 10)
        c.drawString(5*mm, y, "A CUENTA:"); c.drawRightString(width-5*mm, y, f"S/ {montos['acuenta']:.2f}"); y-=5*mm
        c.drawString(5*mm, y, "SALDO:"); c.drawRightString(width-5*mm, y, f"S/ {montos['saldo']:.2f}"); y-=5*mm
        
    c.showPage(); c.save(); buffer.seek(0); return buffer

def buscar_dni(dni):
    # Simulación API
    return None 

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- 5. MODALES INTERACTIVOS (EVIDENCIAS Y GESTIÓN) ---
@st.dialog("Gestión de Servicio")
def modal_servicio(t):
    st.markdown(f"### 🔧 Orden #{t['id']}")
    c1, c2 = st.columns(2)
    c1.info(f"Cliente: **{t['cliente_nombre']}**")
    c2.warning(f"Saldo: **S/ {t['saldo']:.2f}**")
    
    tab1, tab2, tab3, tab4 = st.tabs(["💵 Cobrar", "📸 Evidencias", "🖨️ PDF", "⚠️ Anular"])
    
    with tab1: # COBRAR
        if t['saldo'] <= 0: st.success("✅ Pagado")
        else:
            monto = st.number_input("Monto a Pagar", 0.0, float(t['saldo']), float(t['saldo']))
            metodo = st.selectbox("Método", ["Efectivo", "Yape", "Tarjeta"])
            if st.button("Confirmar Pago", use_container_width=True):
                # Calcular nuevo saldo y estado
                n_acu = t['acuenta'] + monto
                n_sal = t['precio'] - n_acu
                est = "Entregado" if n_sal == 0 else "Pendiente"
                supabase.table("tickets").update({"acuenta":n_acu, "saldo":n_sal, "estado":est, "metodo_pago":metodo}).eq("id", t['id']).execute()
                st.rerun()

    with tab2: # EVIDENCIAS (REQ #12)
        c_ant, c_des = st.columns(2)
        with c_ant:
            st.caption("Antes (Recepción)")
            if t['foto_antes']: st.image(t['foto_antes'], use_container_width=True)
            else: st.info("No hay foto")
        with c_des:
            st.caption("Después (Entrega)")
            if t['foto_despues']: st.image(t['foto_despues'], use_container_width=True)
            else:
                f_up = st.file_uploader("Subir Foto Final", key="f_up")
                if f_up and st.button("Guardar Evidencia"):
                    url = subir_archivo(f_up)
                    supabase.table("tickets").update({"foto_despues":url}).eq("id", t['id']).execute()
                    st.rerun()

    with tab3: # PDF
        pdf = generar_pdf_universal("Reparacion", t['id'], {"nombre":t['cliente_nombre'], "dni":t['cliente_dni']}, [{"desc":t['marca']+" "+t['modelo'], "cant":1, "total":t['precio']}], {"total":t['precio'], "acuenta":t['acuenta'], "saldo":t['saldo']})
        st.download_button("Descargar Ticket", pdf, f"Ticket_{t['id']}.pdf", "application/pdf", use_container_width=True)

    with tab4: # ANULAR
        if st.button("ANULAR ORDEN", type="primary"):
            supabase.table("tickets").update({"estado":"Anulado"}).eq("id", t['id']).execute()
            st.rerun()

# --- 6. MENU LATERAL ---
with st.sidebar:
    st.title("VillaFix ERP")
    # REQ #6: USUARIOS
    try: users = [u['nombre'] for u in supabase.table("usuarios").select("nombre").execute().data]
    except: users = ["Admin"]
    st.session_state.user = st.selectbox("Usuario", users)
    
    menu = option_menu(None, ["Dashboard", "Recepción", "Ventas (POS)", "Cotizaciones", "Logística", "Clientes"], 
        icons=["speedometer2", "tools", "cart4", "file-text", "truck", "people"], default_index=1,
        styles={"nav-link-selected": {"background-color": "#2563EB"}})

# --- 7. MÓDULOS ---

# ==========================================
# 1. DASHBOARD (REQ #3, #4)
# ==========================================
if menu == "Dashboard":
    st.markdown("### 📊 Panel de Control")
    c1, c2, c3, c4 = st.columns(4)
    # Filtros de fecha para REQ #3 (Detalle diario/semanal)
    periodo = st.selectbox("Periodo", ["Hoy", "Semana", "Mes"])
    
    # Lógica simplificada de fechas...
    f_ini = date.today() # Placeholder
    
    try:
        ventas = pd.DataFrame(supabase.table("ventas").select("*").execute().data)
        tickets = pd.DataFrame(supabase.table("tickets").select("*").execute().data)
    except: ventas = pd.DataFrame(); tickets = pd.DataFrame()
    
    total_pos = ventas['total'].sum() if not ventas.empty else 0
    total_taller = tickets['acuenta'].sum() if not tickets.empty else 0 # Suma lo cobrado real
    
    c1.markdown(f'<div class="kpi-card"><div class="kpi-val">S/ {total_pos:.2f}</div><div class="kpi-lbl">Ventas</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-val">S/ {total_taller:.2f}</div><div class="kpi-lbl">Taller</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-val">{len(tickets)}</div><div class="kpi-lbl">Servicios</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card"><div class="kpi-val">S/ {total_pos+total_taller:.2f}</div><div class="kpi-lbl">Total Caja</div></div>', unsafe_allow_html=True)

    st.divider()
    g1, g2 = st.columns(2)
    with g1:
        st.caption("🏆 Rendimiento por Vendedor (REQ #4)")
        if not ventas.empty:
            fig = px.bar(ventas.groupby('vendedor_nombre')['total'].sum().reset_index(), x='vendedor_nombre', y='total')
            st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 2. RECEPCIÓN (REQ #9, #10, #12)
# ==========================================
elif menu == "Recepción":
    t_form, t_list = st.tabs(["✨ Nueva Recepción", "📋 Listado de Reparaciones"])
    
    with t_form:
        st.markdown("#### Datos Cliente & Equipo")
        c_sel, x = st.columns([3, 1])
        try: clis = {f"{c['dni']} - {c['nombre']}": c for c in supabase.table("clientes").select("dni,nombre").execute().data}
        except: clis = {}
        sel = c_sel.selectbox("Cliente Existente", ["Nuevo"] + list(clis.keys()))
        
        v_dni = clis[sel]['dni'] if sel != "Nuevo" else ""
        v_nom = clis[sel]['nombre'] if sel != "Nuevo" else ""

        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 1])
            dni = c1.text_input("DNI", value=v_dni)
            if dni and len(dni)==8 and not v_nom: 
                if n := buscar_dni_reniec(dni): v_nom = n; st.rerun()
            nom = c2.text_input("Nombre", value=v_nom)
            cel = c3.text_input("Celular")
            
            # Alerta Cumpleaños (REQ #8)
            if dni: 
                bd = supabase.table("clientes").select("fecha_nacimiento").eq("dni", dni).execute().data
                if bd and bd[0]['fecha_nacimiento']:
                    if datetime.strptime(bd[0]['fecha_nacimiento'], '%Y-%m-%d').month == date.today().month:
                        st.success("🎂 ¡Cliente cumple años este mes!")

        with st.container(border=True):
            r1, r2, r3 = st.columns(3)
            mar = r1.selectbox("Marca", ["Samsung", "Apple", "Xiaomi", "Motorola", "Otro"])
            mod = r2.text_input("Modelo")
            mot = r3.selectbox("Motivo", ["Reparación", "Garantía", "Mantenimiento"])
            
            r4, r5 = st.columns(2)
            falla = r4.text_area("Falla Reportada")
            foto = r5.file_uploader("📸 Foto Recepción (Evidencia)", type=['png', 'jpg'])
            
            r6, r7, r8 = st.columns(3)
            costo = r6.number_input("Costo Total", 0.0)
            acuenta = r7.number_input("A Cuenta", 0.0)
            f_ent = r8.date_input("Entrega Estimada", date.today())

        if st.button("💾 GENERAR ORDEN", type="primary"):
            url_foto = subir_archivo(foto) if foto else None
            # Guardar Cliente
            supabase.table("clientes").upsert({"dni":dni, "nombre":nom, "telefono":cel}).execute()
            # Guardar Ticket
            res = supabase.table("tickets").insert({
                "cliente_dni":dni, "cliente_nombre":nom, "vendedor_nombre":st.session_state.user,
                "marca":mar, "modelo":mod, "motivo":mot, "falla_reportada":falla,
                "precio":costo, "acuenta":acuenta, "saldo":costo-acuenta,
                "foto_antes":url_foto, "fecha_entrega":str(f_ent), "estado":"Pendiente"
            }).execute()
            st.success("Orden Creada"); st.rerun()

    with t_list:
        # Barra Herramientas
        with st.container():
            c_s, c_e = st.columns([4, 1])
            search = c_s.text_input("🔍 Buscar...", placeholder="Cliente, Ticket, DNI")
            q = supabase.table("tickets").select("*").order("created_at", desc=True)
            if search: q = q.ilike("cliente_nombre", f"%{search}%")
            data = q.execute().data
            
            if data:
                exc = to_excel(pd.DataFrame(data))
                c_e.download_button("📗 Excel", exc, "data.xlsx", use_container_width=True)

        # Encabezado
        st.markdown('<div class="rep-header"><div style="width:50px">⚙️</div><div style="width:100px">Estado</div><div style="flex:1">Cliente</div><div style="flex:1">Equipo</div><div style="flex:1;text-align:right">Montos</div></div>', unsafe_allow_html=True)
        
        # Filas
        if data:
            for t in data:
                if t['estado']=='Anulado': bg="bg-red"; stt="ANULADO"
                elif t['saldo']<=0: bg="bg-green"; stt="PAGADO"
                else: bg="bg-blue"; stt="TALLER"
                
                c_btn, c_info = st.columns([0.8, 11])
                with c_btn:
                    st.write("")
                    if st.button("⚙️", key=f"g_{t['id']}"): gestion_modal(t)
                
                with c_info:
                    st.markdown(f"""
                    <div class="rep-row">
                        <div style="width:100px"><span class="badge {bg}">{stt}</span></div>
                        <div style="flex:1"><strong>{t['cliente_nombre'].split()[0]}</strong><br><small>{t['cliente_dni']}</small></div>
                        <div style="flex:1"><strong>{t['modelo']}</strong><br><small>{t['marca']}</small></div>
                        <div style="flex:1;text-align:right"><strong>S/ {t['precio']:.2f}</strong><br><small style="color:red">Deb: {t['saldo']:.2f}</small></div>
                    </div>
                    """, unsafe_allow_html=True)

# ==========================================
# 3. VENTAS (POS) (REQ #10)
# ==========================================
elif menu == "Ventas (POS)":
    st.markdown("### 🛒 Punto de Venta")
    if 'cart' not in st.session_state: st.session_state.cart = []
    
    c_cat, c_cart = st.columns([1.5, 1])
    
    with c_cat:
        st.caption("Catálogo")
        prods = supabase.table("productos").select("*").gt("stock", 0).execute().data
        for p in prods:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{p['nombre']}** (Stock: {p['stock']})"); c1.caption(f"S/ {p['precio']}")
                if c2.button("➕", key=f"p_{p['id']}"): 
                    st.session_state.cart.append(p); st.toast("Agregado")
    
    with c_cart:
        st.caption("Ticket Actual")
        if st.session_state.cart:
            df = pd.DataFrame(st.session_state.cart)
            res = df.groupby(['id', 'nombre', 'precio']).size().reset_index(name='cant')
            res['total'] = res['precio'] * res['cant']
            st.dataframe(res[['nombre', 'cant', 'total']], hide_index=True)
            
            total = res['total'].sum()
            st.markdown(f"### Total: S/ {total:.2f}")
            
            if st.button("✅ COBRAR", type="primary"):
                # Registrar Venta y Detalle (Lógica resumida)
                vid = supabase.table("ventas").insert({"total":total, "vendedor_nombre":st.session_state.user}).execute().data[0]['id']
                # Generar PDF
                pdf = generar_pdf_universal("Venta", vid, {"nombre":"Mostrador"}, [], {"total":total})
                st.session_state.last_pdf = pdf
                st.session_state.cart = []; st.rerun()
                
            if 'last_pdf' in st.session_state:
                st.download_button("Descargar Boleta", st.session_state.last_pdf, "Boleta.pdf")

# ==========================================
# 4. COTIZACIONES (REQ #11)
# ==========================================
elif menu == "Cotizaciones":
    st.markdown("### 📄 Cotizador")
    c1, c2 = st.columns(2)
    cli = c1.text_input("Cliente"); ruc = c2.text_input("RUC/DNI")
    det = st.text_area("Detalles")
    tot = st.number_input("Total Cotizado", 0.0)
    
    if st.button("Generar PDF Cotización"):
        pdf = generar_pdf_universal("Cotizacion", "TEMP", {"nombre":cli, "dni":ruc}, [{"desc":det, "cant":1, "total":tot}], {"total":tot})
        st.download_button("Descargar PDF", pdf, "Cotizacion.pdf")

# ==========================================
# 5. LOGÍSTICA (REQ #2, #5)
# ==========================================
elif menu == "Logística":
    st.markdown("### 🚚 Logística y Transporte")
    t1, t2 = st.tabs(["Movimientos", "Guía Remisión"])
    with t1:
        st.dataframe(pd.DataFrame(supabase.table("movimientos_logistica").select("*").execute().data))
    with t2:
        dest = st.text_input("Dirección Destino")
        mot = st.selectbox("Motivo", ["Venta", "Traslado", "Exportación"])
        if st.button("Generar Guía"):
            supabase.table("movimientos_logistica").insert({"tipo":"Salida", "destino":dest, "detalle":mot}).execute()
            st.success("Guía registrada")

# ==========================================
# 6. CLIENTES (REQ #7, #8, #9)
# ==========================================
elif menu == "Clientes":
    st.markdown("### 👥 CRM Clientes")
    c1, c2 = st.columns(2)
    dni_c = c1.text_input("DNI"); nom_c = c2.text_input("Nombre")
    fn = c1.date_input("Fecha Nacimiento (Para Cumpleaños)")
    
    if st.button("Guardar Cliente"):
        supabase.table("clientes").upsert({"dni":dni_c, "nombre":nom_c, "fecha_nacimiento":str(fn)}).execute()
        st.success("Guardado")
    
    st.divider()
    st.markdown("#### 📜 Historial de Reparaciones (REQ #9)")
    b_dni = st.text_input("Buscar DNI para Historial")
    if b_dni:
        h = supabase.table("tickets").select("*").eq("cliente_dni", b_dni).execute().data
        st.dataframe(h)
