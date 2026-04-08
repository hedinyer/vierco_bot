from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor, black, white
import json
import os

# Datos de productos (extraídos de la respuesta anterior)
productos = [
    {"id": "a4f619e5-9c63-486d-80a9-db931b2271a4", "slug": "calzado-11", "ref": "CALZAD-3458", "name": "Calzado 11", "description": "Calzado 11", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/calzado-11-1775533510626.jpg", "alt_text": "X", "categoria": "Tennis", "tipo": "Mujer", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "14dd1bbe-2b4e-4257-92e9-7eb5b9f548a1", "slug": "calzado-6", "ref": "CALZAD-4850", "name": "Calzado 6", "description": "Calzado 6", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/calzado-6-1775533427386.jpg", "alt_text": "X", "categoria": "Tennis", "tipo": "Mujer", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "b96269ac-8466-494e-9a23-3a23fac44471", "slug": "calzado-15", "ref": "CALZAD-3919", "name": "Calzado 15", "description": "Calzado 15", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/calzado-15-1775533317349.jpg", "alt_text": "X", "categoria": "Tennis", "tipo": "Hombre", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "195ffd79-8dd6-453c-8bd6-4090ef2e356f", "slug": "1099-negro", "ref": "1099NE-9467", "name": "1099 Negro", "description": "1099 Negro", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/1099-negro-1775533212086.jpg", "alt_text": "X", "categoria": "Tennis", "tipo": "Hombre", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "7685de60-182f-4b07-bdc4-cc90ebe3b22e", "slug": "1099-miel", "ref": "1099MI-1013", "name": "1099 Miel", "description": "1099 Miel", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/1099-miel-1775533086014.jpg", "alt_text": "X", "categoria": "Tennis", "tipo": "Hombre", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "f6972f39-aff2-44dd-8585-466e8300cf65", "slug": "1099-blancos", "ref": "1099BL-2632", "name": "1099 Blancos", "description": "1099 Blancos", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/1099-blancos-1775532904213.jpg", "alt_text": "X", "categoria": "Tennis", "tipo": "Hombre", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "3da14d68-ecfb-43fd-ac64-888aeba5b596", "slug": "tennis-negro-2", "ref": "TENNIS-8915", "name": "Tennis negro 2", "description": "Tennis negro", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tennis-negro-2-1775532792278.jpg", "alt_text": "X", "categoria": "Tennis", "tipo": "Hombre", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "db8c8fba-2fc1-40da-bb39-8eb2e5cd4f75", "slug": "tennis-blanco", "ref": "TENNIS-5952", "name": "Tennis blanco", "description": "Tennis blanco", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tennis-blanco-1775532689142.jpg", "alt_text": "X", "categoria": "Tennis", "tipo": "Hombre", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "0313de33-600c-4884-98da-ea891e69af63", "slug": "tennis-negro", "ref": "TENNIS-5394", "name": "Tennis negro", "description": "Tennis negro", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tennis-negro-1775531392525.jpg", "alt_text": "X", "categoria": "Tennis", "tipo": "Hombre", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "b9e30264-2cb2-4077-948e-3f7dfe134384", "slug": "tennis-hueso", "ref": "TENNIS-0247", "name": "Tennis Hueso", "description": "Tennis Hueso", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tennis-hueso-1775531217855.jpg", "alt_text": "X", "categoria": "Tennis", "tipo": "Hombre", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "4db41507-649e-4920-9b9c-cb557556f7a9", "slug": "tennis-samba-celeste", "ref": "TENNIS-7024", "name": "Tennis samba celeste", "description": "Tennis samba celeste", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tennis-samba-celeste-1775528853811.jpg", "alt_text": "X", "categoria": "Tennis", "tipo": "Mujer", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "28f9de45-1c9d-48c1-90da-d101eb6a7624", "slug": "tennis-samba-miel", "ref": "TENNIS-6404", "name": "Tennis Samba miel", "description": "Tennis Samba miel", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tennis-samba-miel-1775528704234.jpg", "alt_text": "X", "categoria": "Tennis", "tipo": "Mujer", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "22c9fd8c-efd9-4bb4-a33e-cfbd62a93e7b", "slug": "tacon-en-punta-tacon-aguja", "ref": "TACONE-3685", "name": "Tacon en punta - tacon aguja", "description": "Tacon en punta - tacon aguja", "price_cents": 120000, "availability": None, "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tacon-en-punta-tacon-aguja-1775528267664.jpg", "alt_text": "X", "categoria": None, "tipo": "Mujer", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "81b40fad-a9fc-45fa-a57b-a42a0ceaf5ff", "slug": "tacon-en-punta-bajo", "ref": "TACONE-2682", "name": "Tacon en punta - Bajo", "description": "Tacon en punta - Bajo", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tacon-en-punta-bajo-1775528134029.jpg", "alt_text": "X", "categoria": "Formal", "tipo": "Mujer", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "2c7729ff-ab90-48f6-a922-9e7caeff676d", "slug": "tacon-en-punta-alto", "ref": "TACONE-9369", "name": "Tacon en punta - alto", "description": "Tacon en punta - alto", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tacon-en-punta-alto-1775526842905.jpg", "alt_text": "X", "categoria": "Formal", "tipo": "Mujer", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "25d02d78-b0a9-4fd3-9c99-19077db8dcc5", "slug": "negro-tacon-dorado", "ref": "NEGROT-1537", "name": "Negro tacon dorado", "description": "Negro tacon dorado", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/negro-tacon-dorado-1775526721921.jpg", "alt_text": "X", "categoria": "Formal", "tipo": "Mujer", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "cbf31f90-a504-4eae-87db-e3f5a2a7593f", "slug": "azul-tacon-dorado", "ref": "AZULTA-5738", "name": "Azul tacon dorado", "description": "Azul tacon dorado", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/azul-tacon-dorado-1775526609727.jpg", "alt_text": "X", "categoria": "Formal", "tipo": "Mujer", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "868ce359-c7d4-4452-98a5-69e5aede4488", "slug": "tacon-corrido-negro", "ref": "TACONC-6323", "name": "Tacon corrido negro", "description": "Tacon corrido negro", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tacon-corrido-negro-1775526468374.jpg", "alt_text": "X", "categoria": "Formal", "tipo": "Mujer", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "6852656a-9007-4654-9cfa-7b6010cf65e6", "slug": "tacon-punta-redonda-bajo", "ref": "TACONP-7815", "name": "Tacon punta redonda - Bajo", "description": "Tacon punta redonda", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tacon-punta-redonda-bajo-1775526322195.jpg", "alt_text": "X", "categoria": "Formal", "tipo": "Mujer", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 1}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]},
    {"id": "b8985398-8033-4d49-8831-6f3a21ed10e2", "slug": "zapato-enfermeria-blanco", "ref": "ZAPATO-4955", "name": "Zapato enfermeria - Blanco", "description": "Zapato de enfermería profesional con diseño ergonómico, suela antideslizante y materiales transpirables para máximo confort durante largas jornadas laborales. Ideal para personal de salud que requiere seguridad y comodidad.", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/zapato-enfermeria-blanco-1775526107833.jpg", "alt_text": "X", "categoria": "Formal", "tipo": "Mujer", "sizes": [{"size": "34", "stock": 1}, {"size": "35", "stock": 0}, {"size": "36", "stock": 0}, {"size": "37", "stock": 0}, {"size": "38", "stock": 0}, {"size": "39", "stock": 0}, {"size": "40", "stock": 0}, {"size": "41", "stock": 0}, {"size": "42", "stock": 0}, {"size": "43", "stock": 0}, {"size": "44", "stock": 0}]}
]

def format_price(price_cents):
    """Convierte centavos a COP formateado"""
    return f"${price_cents:,.0f} COP"

def create_pdf(output_path):
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Título principal
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#000000'),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    # Subtítulo
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#333333'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    # Texto normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=black,
        alignment=TA_LEFT
    )
    
    # Encabezado de página
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width/2, height - 30, "VIERCO | Calzado Empresarial de Elite")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, height - 50, "Catálogo Completo de Productos con Inventario")
    
    page_num = 1
    
    for i, producto in enumerate(productos):
        # Verificar si necesitamos nueva página
        if i > 0 and i % 2 == 0:
            c.showPage()
            page_num += 1
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(width/2, height - 30, "VIERCO | Calzado Empresarial de Elite")
            c.setFont("Helvetica", 10)
            c.drawCentredString(width/2, height - 50, "Catálogo Completo de Productos con Inventario")
        
        x = 50
        y = height - 100
        
        # Nombre del producto
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x, y, f"{producto['name']}")
        y -= 20
        
        # Referencia y Categoría
        c.setFont("Helvetica", 10)
        ref_text = f"Ref: {producto['ref']}"
        cat_text = f"Categoría: {producto['categoria'] or 'N/A'} | Tipo: {producto['tipo'] or 'N/A'}"
        c.drawString(x, y, ref_text)
        y -= 15
        c.drawString(x, y, cat_text)
        y -= 20
        
        # Descripción
        c.setFont("Helvetica", 9)
        desc_lines = producto['description'].split('.')
        for line in desc_lines[:2]:  # Máximo 2 líneas de descripción
            if line.strip():
                c.drawString(x, y, line.strip())
                y -= 12
        y -= 10
        
        # Precio
        c.setFont("Helvetica-Bold", 12)
        price_text = f"Precio: {format_price(producto['price_cents'])}"
        availability_text = f"Estado: {producto['availability'] or 'Sin disponibilidad'}"
        c.drawString(x, y, price_text)
        y -= 15
        c.drawString(x, y, availability_text)
        y -= 25
        
        # Tabla de inventario
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, y, "Inventario por Talla:")
        y -= 15
        
        # Crear tabla de tallas
        table_data = [["Talla", "Stock"]]
        for talla_info in producto['sizes']:
            stock_str = str(talla_info['stock']) if talla_info['stock'] > 0 else "Agotado"
            table_data.append([talla_info['size'], stock_str])
        
        table = Table(table_data, colWidths=[3*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, black),
        ]))
        
        try:
            table.wrapOn(c, width - 100, height - 100)
            table.drawOn(c, x, y - 10)
        except:
            pass
        
        y -= 70
        
        # Imagen del producto
        try:
            img = Image(producto['image_url'], width=5*cm, height=5*cm)
            img.drawOn(c, x + 8*cm, y)
        except:
            c.setFont("Helvetica", 8)
            c.drawString(x + 8*cm, y, "[Imagen no disponible]")
        
        y -= 80
        
        # Línea separadora
        c.line(50, y, width - 50, y)
        y -= 20
    
    c.save()
    print(f"PDF generado exitosamente en: {output_path}")

if __name__ == "__main__":
    output_path = "/home/hedinyer/Documents/vierco_bot/generations/catalogo_vierco.pdf"
    create_pdf(output_path)
