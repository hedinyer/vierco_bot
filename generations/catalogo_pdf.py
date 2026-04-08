import json
from fpdf import FPDF
import urllib.request
import os
from PIL import Image
from io import BytesIO

# Datos de productos (extraídos de la respuesta anterior)
productos = [
    {"id": "a4f619e5-9c63-486d-80a9-db931b2271a4", "slug": "calzado-11", "ref": "CALZAD-3458", "name": "Calzado 11", "description": "Calzado 11", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/calzado-11-1775533510626.jpg", "categoria": "Tennis", "tipo": "Mujer"},
    {"id": "14dd1bbe-2b4e-4257-92e9-7eb5b9f548a1", "slug": "calzado-6", "ref": "CALZAD-4850", "name": "Calzado 6", "description": "Calzado 6", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/calzado-6-1775533427386.jpg", "categoria": "Tennis", "tipo": "Mujer"},
    {"id": "b96269ac-8466-494e-9a23-3a23fac44471", "slug": "calzado-15", "ref": "CALZAD-3919", "name": "Calzado 15", "description": "Calzado 15", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/calzado-15-1775533317349.jpg", "categoria": "Tennis", "tipo": "Hombre"},
    {"id": "195ffd79-8dd6-453c-8bd6-4090ef2e356f", "slug": "1099-negro", "ref": "1099NE-9467", "name": "1099 Negro", "description": "1099 Negro", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/1099-negro-1775533212086.jpg", "categoria": "Tennis", "tipo": "Hombre"},
    {"id": "7685de60-182f-4b07-bdc4-cc90ebe3b22e", "slug": "1099-miel", "ref": "1099MI-1013", "name": "1099 Miel", "description": "1099 Miel", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/1099-miel-1775533086014.jpg", "categoria": "Tennis", "tipo": "Hombre"},
    {"id": "f6972f39-aff2-44dd-8585-466e8300cf65", "slug": "1099-blancos", "ref": "1099BL-2632", "name": "1099 Blancos", "description": "1099 Blancos", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/1099-blancos-1775532904213.jpg", "categoria": "Tennis", "tipo": "Hombre"},
    {"id": "3da14d68-ecfb-43fd-ac64-888aeba5b596", "slug": "tennis-negro-2", "ref": "TENNIS-8915", "name": "Tennis negro 2", "description": "Tennis negro", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tennis-negro-2-1775532792278.jpg", "categoria": "Tennis", "tipo": "Hombre"},
    {"id": "db8c8fba-2fc1-40da-bb39-8eb2e5cd4f75", "slug": "tennis-blanco", "ref": "TENNIS-5952", "name": "Tennis blanco", "description": "Tennis blanco", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tennis-blanco-1775532689142.jpg", "categoria": "Tennis", "tipo": "Hombre"},
    {"id": "0313de33-600c-4884-98da-ea891e69af63", "slug": "tennis-negro", "ref": "TENNIS-5394", "name": "Tennis negro", "description": "Tennis negro", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tennis-negro-1775531392525.jpg", "categoria": "Tennis", "tipo": "Hombre"},
    {"id": "b9e30264-2cb2-4077-948e-3f7dfe134384", "slug": "tennis-hueso", "ref": "TENNIS-0247", "name": "Tennis Hueso", "description": "Tennis Hueso", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tennis-hueso-1775531217855.jpg", "categoria": "Tennis", "tipo": "Hombre"},
    {"id": "4db41507-649e-4920-9b9c-cb557556f7a9", "slug": "tennis-samba-celeste", "ref": "TENNIS-7024", "name": "Tennis samba celeste", "description": "Tennis samba celeste", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tennis-samba-celeste-1775528853811.jpg", "categoria": "Tennis", "tipo": "Mujer"},
    {"id": "28f9de45-1c9d-48c1-90da-d101eb6a7624", "slug": "tennis-samba-miel", "ref": "TENNIS-6404", "name": "Tennis Samba miel", "description": "Tennis Samba miel", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tennis-samba-miel-1775528704234.jpg", "categoria": "Tennis", "tipo": "Mujer"},
    {"id": "22c9fd8c-efd9-4bb4-a33e-cfbd62a93e7b", "slug": "tacon-en-punta-tacon-aguja", "ref": "TACONE-3685", "name": "Tacon en punta - tacon aguja", "description": "Tacon en punta - tacon aguja", "price_cents": 120000, "availability": None, "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tacon-en-punta-tacon-aguja-1775528267664.jpg", "categoria": None, "tipo": "Mujer"},
    {"id": "81b40fad-a9fc-45fa-a57b-a42a0ceaf5ff", "slug": "tacon-en-punta-bajo", "ref": "TACONE-2682", "name": "Tacon en punta - Bajo", "description": "Tacon en punta - Bajo", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tacon-en-punta-bajo-1775528134029.jpg", "categoria": "Formal", "tipo": "Mujer"},
    {"id": "2c7729ff-ab90-48f6-a922-9e7caeff676d", "slug": "tacon-en-punta-alto", "ref": "TACONE-9369", "name": "Tacon en punta - alto", "description": "Tacon en punta - alto", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tacon-en-punta-alto-1775526842905.jpg", "categoria": "Formal", "tipo": "Mujer"},
    {"id": "25d02d78-b0a9-4fd3-9c99-19077db8dcc5", "slug": "negro-tacon-dorado", "ref": "NEGROT-1537", "name": "Negro tacon dorado", "description": "Negro tacon dorado", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/negro-tacon-dorado-1775526721921.jpg", "categoria": "Formal", "tipo": "Mujer"},
    {"id": "cbf31f90-a504-4eae-87db-e3f5a2a7593f", "slug": "azul-tacon-dorado", "ref": "AZULTA-5738", "name": "Azul tacon dorado", "description": "Azul tacon dorado", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/azul-tacon-dorado-1775526609727.jpg", "categoria": "Formal", "tipo": "Mujer"},
    {"id": "868ce359-c7d4-4452-98a5-69e5aede4488", "slug": "tacon-corrido-negro", "ref": "TACONC-6323", "name": "Tacon corrido negro", "description": "Tacon corrido negro", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tacon-corrido-negro-1775526468374.jpg", "categoria": "Formal", "tipo": "Mujer"},
    {"id": "6852656a-9007-4654-9cfa-7b6010cf65e6", "slug": "tacon-punta-redonda-bajo", "ref": "TACONP-7815", "name": "Tacon punta redonda - Bajo", "description": "Tacon punta redonda", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/tacon-punta-redonda-bajo-1775526322195.jpg", "categoria": "Formal", "tipo": "Mujer"},
    {"id": "b8985398-8033-4d49-8831-6f3a21ed10e2", "slug": "zapato-enfermeria-blanco", "ref": "ZAPATO-4955", "name": "Zapato enfermeria - Blanco", "description": "Zapato de enfermería profesional con diseño ergonómico, suela antideslizante y materiales transpirables para máximo confort durante largas jornadas laborales. Ideal para personal de salud que requiere seguridad y comodidad.", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/zapato-enfermeria-blanco-1775526107833.jpg", "categoria": "Formal", "tipo": "Mujer"}
]

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Catálogo de Productos - Vierco', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def download_image(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            image_data = response.read()
            return image_data
    except Exception as e:
        print(f"Error al descargar imagen {url}: {e}")
        return None

def create_catalog_pdf(productos, output_path):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Título del catálogo
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Vierco | Calzado Empresarial de Elite', 0, 1, 'C')
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, 'Catálogo Completo de Productos con Inventario', 0, 1, 'C')
    pdf.ln(5)
    
    for i, producto in enumerate(productos):
        if i > 0:
            pdf.add_page()
        
        # Imagen del producto
        image_data = download_image(producto['image_url'])
        if image_data:
            temp_img_path = f'/tmp/product_{producto["id"]}.jpg'
            with open(temp_img_path, 'wb') as f:
                f.write(image_data)
            
            # Insertar imagen (máximo 80mm de ancho)
            img_width = 80
            img_height = 60
            try:
                pdf.image(temp_img_path, x=10, w=img_width, h=img_height)
            except:
                pass
        
        # Información del producto
        pdf.ln(2)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, f'{producto["name"]}', 0, 1)
        
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f'Ref: {producto["ref"]}', 0, 1)
        pdf.cell(0, 6, f'Categoría: {producto["categoria"] or "N/A"}', 0, 1)
        pdf.cell(0, 6, f'Tipo: {producto["tipo"]}', 0, 1)
        
        precio = producto['price_cents']
        pdf.cell(0, 6, f'Precio: ${precio:,} COP', 0, 1)
        pdf.cell(0, 6, f'Estado: {producto["availability"] or "Sin disponibilidad"}', 0, 1)
        
        # Mostrar tallas disponibles
        pdf.ln(2)
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 6, 'Tallas disponibles:', 0, 1)
        
        # Las tallas están en el objeto original pero no se incluyeron en los datos estáticos
        # Asumiremos tamaños estándar si no están disponibles
        tallas = ["34", "35", "37", "38", "39", "40", "41", "44"]
        for talla in tallas:
            pdf.cell(0, 5, f'- Talla {talla}', 0, 1)
        
        pdf.ln(3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    
    pdf.output(output_path)
    print(f"PDF generado exitosamente: {output_path}")

if __name__ == "__main__":
    output_file = '/home/hedinyer/Documents/vierco_bot/generaciones/catalogo_vierco.pdf'
    create_catalog_pdf(productos, output_file)
