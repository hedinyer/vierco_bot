#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Catálogo Profesional Vierco - Diseño Corporativo de Talla Mundial
Versión 4.0 - Presentación Ejecutiva Optimizada
"""

from fpdf import FPDF
import urllib.request
import os
from PIL import Image
from io import BytesIO

class PDFProfesional(FPDF):
    """Clase PDF con diseño corporativo profesional"""
    
    def __init__(self):
        super().__init__()
        self.set_margins(15, 20, 15)
        self.set_auto_page_break(auto=True, margin=20)
        
        # Colores corporativos Vierco
        self.color_primary = (44, 62, 80)      # Azul oscuro corporativo
        self.color_secondary = (192, 57, 43)   # Rojo vino elegante
        self.color_accent = (241, 196, 15)     # Dorado sutil
        self.color_text = (52, 73, 94)         # Gris oscuro texto
        self.color_light = (236, 240, 241)     # Fondo claro
        
    def header(self):
        """Encabezado corporativo"""
        # Línea decorativa superior
        self.set_draw_color(*self.color_primary)
        self.set_line_width(0.5)
        self.line(15, 20, 195, 20)
        
        # Logo y título
        self.set_font('Arial', 'B', 14)
        self.set_text_color(*self.color_primary)
        self.cell(0, 8, 'VIERCO', 0, 0, 'L')
        self.set_font('Arial', '', 10)
        self.set_text_color(*self.color_text)
        self.cell(0, 8, '| Calzado Empresarial de Elite', 0, 1, 'L')
        
        # Línea separadora
        self.set_draw_color(*self.color_secondary)
        self.line(15, 28, 195, 28)
        
        # Información del catálogo
        self.set_y(32)
        self.set_font('Arial', 'I', 9)
        self.set_text_color(*self.color_text)
        self.cell(0, 5, 'Catálogo Mayorista | Edición Ejecutiva', 0, 1, 'C')
        self.set_font('Arial', '', 8)
        self.cell(0, 5, 'Presentación Profesional para Clientes Estratégicos', 0, 1, 'C')
        
        # Línea inferior
        self.set_draw_color(*self.color_primary)
        self.line(15, 38, 195, 38)
        
        self.ln(5)
    
    def footer(self):
        """Pie de página profesional"""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(*self.color_text)
        
        # Número de página
        page_info = f'Pagina {self.page_no()} de {{nb}}'
        self.cell(0, 6, page_info, 0, 0, 'R')
        
        # Línea superior al pie
        self.set_draw_color(*self.color_light)
        self.line(15, self.get_y() + 5, 195, self.get_y() + 5)
    
    def draw_product_header(self, producto):
        """Diseño de cabecera de producto"""
        self.set_fill_color(*self.color_primary)
        self.rect(15, self.get_y(), 180, 8, 'F')
        
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 10)
        self.cell(0, 8, producto['name'], 0, 1, 'L')
        
        self.set_y(self.get_y() + 2)
        self.set_font('Arial', '', 8)
        self.set_text_color(255, 255, 255)
        self.cell(0, 5, f'Referencia: {producto["ref"]} | Categoria: {producto["categoria"] or "N/A"}', 0, 1, 'L')
        
        self.set_y(self.get_y() + 2)
        self.set_font('Arial', '', 8)
        self.cell(0, 5, f'Tipo: {producto["tipo"]} | Disponibilidad: {producto["availability"] or "Sin stock"}', 0, 1, 'L')
        
        # Linea separadora
        self.set_draw_color(*self.color_secondary)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(2)
    
    def download_image(self, url, max_width=70, max_height=70):
        """Descarga imagen con manejo de errores"""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                image_data = response.read()
                
                # Procesar imagen con Pillow
                img = Image.open(BytesIO(image_data))
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                temp_path = f'/tmp/vierco_img_{hash(url)}.jpg'
                img.save(temp_path, 'JPEG', quality=85)
                return temp_path
        except Exception as e:
            print(f"Warning descargando imagen: {url[:50]}...")
            return None
    
    def create_cover_page(self):
        """Pagina de portada ejecutiva"""
        self.add_page()
        
        # Fondo degradado simulado
        self.set_fill_color(*self.color_primary)
        self.rect(0, 0, 210, 297, 'F')
        
        # Contenido centrado
        self.set_y(80)
        self.set_text_color(255, 255, 255)
        
        # Titulo principal
        self.set_font('Arial', 'B', 28)
        self.cell(0, 10, 'VIERCO', 0, 1, 'C')
        
        self.set_font('Arial', '', 14)
        self.cell(0, 8, 'Calzado Empresarial de Elite', 0, 1, 'C')
        
        self.ln(15)
        
        # Subtitulo
        self.set_font('Arial', 'I', 12)
        self.cell(0, 8, 'Catalogo Mayorista Ejecutivo', 0, 1, 'C')
        
        self.ln(10)
        
        # Linea decorativa
        self.set_draw_color(255, 255, 255)
        self.line(60, self.get_y(), 150, self.get_y())
        
        self.ln(15)
        
        # Detalles
        self.set_font('Arial', '', 10)
        self.cell(0, 6, 'Edicion Especial para Clientes Estrategicos', 0, 1, 'C')
        self.cell(0, 6, 'Inventario Completo | Precios Mayoristas', 0, 1, 'C')
        
        self.ln(20)
        
        # Pie de portada
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, 'Generado: 2026-04-07', 0, 1, 'C')
        
        self.ln(30)
        
        # Contador de productos
        self.set_font('Arial', 'B', 16)
        self.cell(0, 8, f'{len(self.productos)} Productos Disponibles', 0, 1, 'C')
        
        self.set_font('Arial', '', 10)
        self.cell(0, 6, 'Categorias: Tennis, Formal, Especializada', 0, 1, 'C')
    
    def create_index_page(self):
        """Pagina de indice organizado por categorias"""
        self.add_page()
        
        # Titulo
        self.set_fill_color(*self.color_primary)
        self.rect(15, 20, 180, 10, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'INDICE DE PRODUCTOS', 0, 1, 'C')
        self.line(15, 30, 195, 30)
        
        self.ln(5)
        
        # Agrupar por categoria
        categorias = {}
        for p in self.productos:
            cat = p['categoria'] or 'General'
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append(p)
        
        self.set_font('Arial', 'B', 10)
        self.set_text_color(*self.color_primary)
        
        pagina_actual = 2
        for i, (cat, productos_cat) in enumerate(categorias.items()):
            if i > 0 and self.get_y() > 250:
                self.add_page()
                self.set_y(20)
            
            self.cell(0, 6, f'* {cat}', 0, 1)
            
            self.set_font('Arial', '', 9)
            self.set_text_color(*self.color_text)
            
            for prod in productos_cat:
                # Usar espacios en lugar de indent
                self.cell(10, 4, '', 0, 0)
                self.cell(0, 4, f'- {prod["name"]}', 0, 1)
            
            self.ln(2)
        
        self.ln(10)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(*self.color_text)
        self.cell(0, 5, 'Para mas informacion, contacte a su ejecutivo de cuenta', 0, 1, 'C')
    
    def create_product_page(self, producto, index):
        """Pagina individual de producto con diseno premium"""
        if index > 0:
            self.add_page()
        
        # Cabecera de producto
        self.draw_product_header(producto)
        
        # Imagen del producto
        img_path = self.download_image(producto['image_url'])
        
        if img_path and os.path.exists(img_path):
            try:
                # Insertar imagen centrada
                img_width = 80
                img_height = 60
                
                x_pos = (210 - img_width) / 2
                y_pos = self.get_y()
                
                self.image(img_path, x=x_pos, w=img_width, h=img_height)
                
                # Leyenda de imagen
                self.set_y(y_pos + img_height + 5)
                self.set_font('Arial', 'I', 8)
                self.set_text_color(*self.color_text)
                self.cell(0, 5, f'Imagen referencial del modelo {producto["name"]}', 0, 1, 'C')
                
                self.ln(3)
            except:
                pass
        else:
            # Placeholder si no hay imagen
            self.set_y(self.get_y() + 10)
            self.set_font('Arial', 'I', 9)
            self.set_text_color(*self.color_text)
            self.cell(0, 5, '[Imagen no disponible]', 0, 1, 'C')
            self.ln(5)
        
        # Detalles tecnicos
        self.set_font('Arial', 'B', 10)
        self.set_text_color(*self.color_primary)
        self.cell(0, 6, 'DETALLES TECNICOS', 0, 1)
        self.line(15, self.get_y() - 2, 195, self.get_y() - 2)
        
        self.ln(2)
        
        self.set_font('Arial', '', 9)
        self.set_text_color(*self.color_text)
        
        # Precio
        precio = producto['price_cents']
        self.cell(0, 5, f'Precio Unitario: ${precio:,} COP', 0, 1)
        
        # Descripcion
        self.cell(0, 5, f'Descripcion: {producto["description"]}', 0, 1)
        
        # Inventario
        self.ln(3)
        self.set_font('Arial', 'B', 9)
        self.set_text_color(*self.color_secondary)
        self.cell(0, 5, 'INVENTARIO DISPONIBLE', 0, 1)
        self.line(15, self.get_y() - 2, 195, self.get_y() - 2)
        
        self.ln(2)
        self.set_font('Arial', '', 8)
        self.set_text_color(*self.color_text)
        
        tallas_estandar = ["34", "35", "37", "38", "39", "40", "41", "44"]
        
        # Mostrar disponibilidad por talla
        self.multi_cell(0, 4, 'Tallas disponibles en stock:\n' + ', '.join(tallas_estandar))
        
        # CTA para compra mayorista
        self.ln(5)
        self.set_fill_color(*self.color_light)
        self.set_text_color(*self.color_primary)
        self.set_font('Arial', 'B', 9)
        self.cell(0, 6, 'TELEFONO: Para pedidos mayoristas: Contacte a su ejecutivo de ventas', 0, 1, 'C', fill=True)
        
        self.ln(2)
        
        # Linea divisoria final
        self.set_draw_color(*self.color_primary)
        self.line(15, self.get_y(), 195, self.get_y())
    
    def create_summary_page(self):
        """Pagina de resumen estadistico"""
        self.add_page()
        
        # Titulo
        self.set_fill_color(*self.color_primary)
        self.rect(15, 20, 180, 10, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'RESUMEN EJECUTIVO', 0, 1, 'C')
        self.line(15, 30, 195, 30)
        
        self.ln(5)
        
        self.set_font('Arial', 'B', 10)
        self.set_text_color(*self.color_primary)
        
        # Estadisticas
        total_productos = len(self.productos)
        categoria_counts = {}
        tipo_counts = {}
        total_stock = 0
        
        for p in self.productos:
            cat = p['categoria'] or 'General'
            tipo = p['tipo']
            
            categoria_counts[cat] = categoria_counts.get(cat, 0) + 1
            tipo_counts[tipo] = tipo_counts.get(tipo, 0) + 1
            total_stock += 1  # Asumiendo 1 unidad por talla disponible
        
        # Tabla de categorias
        self.set_font('Arial', 'B', 9)
        self.set_text_color(*self.color_text)
        self.cell(0, 6, 'Distribucion por Categoria:', 0, 1)
        
        self.set_font('Arial', '', 8)
        for cat, count in sorted(categoria_counts.items()):
            porcentaje = (count / total_productos) * 100
            self.cell(0, 4, f'  * {cat}: {count} productos ({porcentaje:.1f}%)', 0, 1)
        
        self.ln(3)
        
        # Distribucion por tipo
        self.set_font('Arial', 'B', 9)
        self.cell(0, 6, 'Distribucion por Tipo:', 0, 1)
        
        self.set_font('Arial', '', 8)
        for tipo, count in sorted(tipo_counts.items()):
            porcentaje = (count / total_productos) * 100
            self.cell(0, 4, f'  * {tipo}: {count} productos ({porcentaje:.1f}%)', 0, 1)
        
        self.ln(5)
        
        # Total inversion
        total_inversion = sum(p['price_cents'] for p in self.productos)
        self.set_font('Arial', 'B', 9)
        self.set_text_color(*self.color_secondary)
        self.cell(0, 6, f'Valor Total del Catalogo: ${total_inversion:,} COP', 0, 1)
        
        self.ln(5)
        
        # Mensaje final
        self.set_font('Arial', 'I', 9)
        self.set_text_color(*self.color_text)
        self.cell(0, 6, 'Gracias por considerar Vierco como su aliado estrategico en calzado empresarial', 0, 1, 'C')
        
        self.ln(10)
        self.cell(0, 5, 'VIERCO | Excelencia en Calzado Empresarial', 0, 1, 'C')


def main():
    # Datos de productos (misma lista que antes)
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
        {"id": "b8985398-8033-4d49-8831-6f3a21ed10e2", "slug": "zapato-enfermeria-blanco", "ref": "ZAPATO-4955", "name": "Zapato enfermeria - Blanco", "description": "Zapato de enfermeria profesional con diseno ergonomico, suela antideslizante y materiales transpirables para maximo confort durante largas jornadas laborales. Ideal para personal de salud que requiere seguridad y comodidad.", "price_cents": 120000, "availability": "En stock", "image_url": "https://uufwfagmbuncwbhtqseb.supabase.co/storage/v1/object/public/images/products/zapato-enfermeria-blanco-1775526107833.jpg", "categoria": "Formal", "tipo": "Mujer"}
    ]
    
    # Crear instancia del PDF profesional
    pdf = PDFProfesional()
    pdf.productos = productos  # Guardar referencia a productos
    
    # Configurar metadatos
    pdf.set_title('Catalogo Mayorista Vierco')
    pdf.set_author('Vierco | Calzado Empresarial de Elite')
    pdf.set_subject('Catalogo de Productos - Presentacion Ejecutiva')
    
    # Generar paginas
    print("Generando portada ejecutiva...")
    pdf.create_cover_page()
    
    print("Generando indice...")
    pdf.create_index_page()
    
    print("Generando paginas de productos...")
    for i, producto in enumerate(productos):
        pdf.create_product_page(producto, i)
    
    print("Generando resumen ejecutivo...")
    pdf.create_summary_page()
    
    # Guardar archivo
    output_path = '/home/hedinyer/Documents/vierco_bot/generaciones/catalogo_vierco_profesional.pdf'
    pdf.output(output_path)
    
    print(f"\nCatálogo profesional generado exitosamente!")
    print(f"Archivo: {output_path}")
    print(f"Páginas totales: {pdf.page_no()}")


if __name__ == "__main__":
    main()
