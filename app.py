from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth

def generar_ticket_pdf(t):
    """
    Genera un Ticket Térmico Profesional (80mm ancho)
    Ideal para impresoras POS (Xprinter, Epson, etc.)
    """
    # 1. Configuración de la "Tira de Papel"
    width = 80 * mm   # Ancho estándar de ticket (80mm)
    height = 250 * mm # Alto variable (le damos espacio de sobra)
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height))
    
    # Márgenes y posiciones
    margin_left = 5 * mm
    y = height - 10 * mm # Empezamos desde arriba
    printable_width = width - (2 * margin_left)
    
    # --- A. CABECERA (LOGO Y EMPRESA) ---
    c.setFillColor(colors.black)
    
    # Nombre Empresa (Centrado)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, y, "VILLAFIX OS")
    y -= 5 * mm
    
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, y, "Servicio Técnico Especializado")
    y -= 4 * mm
    c.drawCentredString(width / 2, y, "Av. Revolución 123, Villa el Salvador")
    y -= 4 * mm
    c.drawCentredString(width / 2, y, "WhatsApp: 999-999-999")
    y -= 8 * mm
    
    # Línea divisoria
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(margin_left, y, width - margin_left, y)
    y -= 5 * mm
    
    # N° TICKET
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, f"ORDEN #{t['id']}")
    y -= 5 * mm
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 8 * mm

    # --- B. DATOS CLIENTE ---
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin_left, y, "CLIENTE:")
    y -= 4 * mm
    c.setFont("Helvetica", 9)
    # Ajuste automático de texto largo (Nombre)
    nombre = t['cliente_nombre']
    if len(nombre) > 25: nombre = nombre[:25] + "..."
    c.drawString(margin_left, y, f"- {nombre}")
    y -= 4 * mm
    c.drawString(margin_left, y, f"- DNI: {t['cliente_dni']}")
    y -= 6 * mm

    # --- C. EQUIPO Y FALLA ---
    c.line(margin_left, y, width - margin_left, y) # Línea
    y -= 5 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin_left, y, "EQUIPO / MODELO:")
    y -= 4 * mm
    c.setFont("Helvetica", 10)
    c.drawString(margin_left, y, f"{t['marca']} {t['modelo']}")
    y -= 5 * mm
    
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin_left, y, "IMEI / SERIE:")
    c.drawRightString(width - margin_left, y, t['imei'] if t['imei'] else "N/A")
    y -= 5 * mm

    c.drawString(margin_left, y, "CONTRASEÑA:")
    c.drawRightString(width - margin_left, y, t['contrasena'])
    y -= 6 * mm
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin_left, y, "FALLA REPORTADA:")
    y -= 4 * mm
    c.setFont("Helvetica", 9)
    # Texto multilinea básico para descripción
    text_object = c.beginText(margin_left, y)
    text_object.setFont("Helvetica", 9)
    # Cortamos texto cada 30 caracteres para que no se salga
    desc = t['descripcion']
    import textwrap
    lines = textwrap.wrap(desc, width=30)
    for line in lines:
        text_object.textLine(line)
        y -= 4 * mm
    c.drawText(text_object)
    y -= 4 * mm

    # --- D. ZONA FINANCIERA (CAJA) ---
    c.setDash(1, 2) # Línea punteada
    c.line(margin_left, y, width - margin_left, y)
    c.setDash([]) # Reset línea
    y -= 6 * mm
    
    c.setFont("Helvetica", 10)
    c.drawString(margin_left, y, "TOTAL:")
    c.drawRightString(width - margin_left, y, f"S/ {t['precio']:.2f}")
    y -= 5 * mm
    
    c.drawString(margin_left, y, "A CUENTA:")
    c.drawRightString(width - margin_left, y, f"S/ {t['acuenta']:.2f}")
    y -= 6 * mm
    
    # SALDO (Negrita y Grande)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_left, y, "SALDO:")
    c.drawRightString(width - margin_left, y, f"S/ {t['saldo']:.2f}")
    y -= 10 * mm

    # --- E. QR Y LEGALES ---
    # Generar QR
    qr_data = f"TICKET-{t['id']}|SALDO:{t['saldo']}"
    qr = qrcode.make(qr_data)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        qr.save(tmp.name)
        # Dibujar QR centrado
        qr_size = 35 * mm
        c.drawImage(tmp.name, (width - qr_size)/2, y - qr_size, width=qr_size, height=qr_size)
        os.unlink(tmp.name)
    
    y -= (35 * mm) + (5 * mm)
    
    c.setFont("Helvetica", 7)
    c.drawCentredString(width / 2, y, "Escanee para ver estado")
    y -= 5 * mm
    
    # Términos legales (Letra chica)
    terms = [
        "--------------------------------",
        "1. Pasados 30 días se considera abandono.",
        "2. Garantía solo cubre mano de obra.",
        "3. No hay garantía por equipos mojados.",
        "   GRACIAS POR SU PREFERENCIA"
    ]
    for line in terms:
        c.drawCentredString(width / 2, y, line)
        y -= 3 * mm

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
