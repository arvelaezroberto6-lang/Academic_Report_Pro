from flask import Flask, render_template, request, jsonify, send_file
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from docx import Document
from io import BytesIO
import os
import uuid
from datetime import datetime
import requests
import logging
import re

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.makedirs('informes_generados', exist_ok=True)

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

logger.info("=" * 60)
logger.info("🚀 ACADEMIC REPORT PRO - VERSIÓN PROFESIONAL")
logger.info(f"🔑 API Key configurada: {'SÍ ✅' if DEEPSEEK_API_KEY else 'NO ❌'}")
logger.info("=" * 60)

def llamar_deepseek(prompt):
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": "Eres un asistente académico profesional. Generas informes estructurados en español."},
                     {"role": "user", "content": prompt}],
        "max_tokens": 8000,
        "temperature": 0.7
    }
    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=120)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            logger.error(f"Error HTTP {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

def extraer_seccion(contenido, nombre):
    patron = rf'\*\*{nombre}\*\*:?\s*(.*?)(?=\*\*[A-ZÁÉÍÓÚÜÑ]|\Z)'
    match = re.search(patron, contenido, re.DOTALL | re.IGNORECASE)
    if match:
        texto = match.group(1).strip()
        texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
        texto = texto.replace('\n', '<br/>')
        return texto
    return ""

def generar_pdf_profesional(datos_usuario, secciones):
    """Genera un PDF con formato profesional tipo Word"""
    
    nombre = datos_usuario.get('nombre', 'Estudiante')
    tema = datos_usuario.get('tema', 'Tema de Investigación')
    asignatura = datos_usuario.get('asignatura', '')
    profesor = datos_usuario.get('profesor', '')
    institucion = datos_usuario.get('institucion', '')
    fecha = datos_usuario.get('fecha', datetime.now().strftime('%d/%m/%Y'))
    norma = datos_usuario.get('norma', 'APA 7')
    
    filename = f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join('informes_generados', filename)
    
    # Estilos profesionales
    styles = getSampleStyleSheet()
    
    # Título principal de portada
    styles.add(ParagraphStyle(
        name='TituloPortada',
        parent=styles['Title'],
        fontSize=28,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=colors.HexColor('#1a3a5c')
    ))
    
    # Subtítulo de portada
    styles.add(ParagraphStyle(
        name='SubtituloPortada',
        parent=styles['Normal'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=40,
        textColor=colors.HexColor('#4a6a8a')
    ))
    
    # Títulos de sección (1, 2, 3...)
    styles.add(ParagraphStyle(
        name='TituloSeccion',
        parent=styles['Heading1'],
        fontSize=16,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2c5282'),
        spaceBefore=30,
        spaceAfter=15,
        borderPadding=5,
        borderWidth=0,
        borderRadius=0
    ))
    
    # Texto normal justificado
    styles.add(ParagraphStyle(
        name='TextoJustificado',
        parent=styles['Normal'],
        alignment=TA_JUSTIFY,
        fontSize=11,
        fontName='Times-Roman',
        spaceAfter=12,
        leading=16,
        leftIndent=0,
        rightIndent=0
    ))
    
    # Texto centrado para datos
    styles.add(ParagraphStyle(
        name='TextoCentrado',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=11,
        fontName='Times-Roman',
        spaceAfter=8
    ))
    
    # Crear documento con márgenes profesionales
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
        title=tema,
        author=nombre
    )
    
    story = []
    
    # ========== PORTADA PROFESIONAL ==========
    story.append(Spacer(1, 2.5*inch))
    story.append(Paragraph("INFORME ACADÉMICO", styles['TituloPortada']))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(tema.upper(), styles['SubtituloPortada']))
    story.append(Spacer(1, 1.5*inch))
    
    # Línea decorativa
    story.append(Paragraph("<hr width='50%' color='#c9a84c'/>", styles['TextoCentrado']))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph(f"<b>Presentado por:</b> {nombre}", styles['TextoCentrado']))
    if asignatura:
        story.append(Paragraph(f"<b>Asignatura:</b> {asignatura}", styles['TextoCentrado']))
    if profesor:
        story.append(Paragraph(f"<b>Docente:</b> {profesor}", styles['TextoCentrado']))
    if institucion:
        story.append(Paragraph(f"<b>Institución:</b> {institucion}", styles['TextoCentrado']))
    story.append(Paragraph(f"<b>Fecha de entrega:</b> {fecha}", styles['TextoCentrado']))
    story.append(Paragraph(f"<b>Norma de citación:</b> {norma}", styles['TextoCentrado']))
    
    story.append(PageBreak())
    
    # ========== ÍNDICE ==========
    story.append(Paragraph("ÍNDICE", styles['TituloSeccion']))
    story.append(Spacer(1, 0.2*inch))
    
    indices = [
        "1. INTRODUCCIÓN",
        "2. OBJETIVOS",
        "3. MARCO TEÓRICO",
        "4. METODOLOGÍA",
        "5. DESARROLLO",
        "6. CONCLUSIONES",
        "7. RECOMENDACIONES",
        "8. REFERENCIAS BIBLIOGRÁFICAS"
    ]
    
    for idx in indices:
        story.append(Paragraph(f"• {idx}", styles['TextoJustificado']))
        story.append(Spacer(1, 0.1*inch))
    
    story.append(PageBreak())
    
    # ========== SECCIONES ==========
    secciones_orden = [
        ("1. INTRODUCCIÓN", 'introduccion'),
        ("2. OBJETIVOS", 'objetivos'),
        ("3. MARCO TEÓRICO", 'marco_teorico'),
        ("4. METODOLOGÍA", 'metodologia'),
        ("5. DESARROLLO", 'desarrollo'),
        ("6. CONCLUSIONES", 'conclusiones'),
        ("7. RECOMENDACIONES", 'recomendaciones'),
        ("8. REFERENCIAS BIBLIOGRÁFICAS", 'referencias')
    ]
    
    for titulo, clave in secciones_orden:
        story.append(Paragraph(titulo, styles['TituloSeccion']))
        story.append(Spacer(1, 0.15*inch))
        contenido = secciones.get(clave, '')
        if contenido and len(contenido) > 30:
            # Dividir en párrafos si tiene saltos
            parrafos = contenido.split('<br/><br/>')
            for parrafo in parrafos:
                if parrafo.strip():
                    story.append(Paragraph(parrafo.strip(), styles['TextoJustificado']))
                    story.append(Spacer(1, 0.1*inch))
        else:
            story.append(Paragraph("Contenido no disponible para esta sección.", styles['TextoJustificado']))
        
        story.append(PageBreak())
    
    doc.build(story)
    return filename, filepath

def generar_word_profesional(datos_usuario, secciones):
    """Genera un Word con formato profesional"""
    
    nombre = datos_usuario.get('nombre', 'Estudiante')
    tema = datos_usuario.get('tema', 'Tema')
    asignatura = datos_usuario.get('asignatura', '')
    profesor = datos_usuario.get('profesor', '')
    institucion = datos_usuario.get('institucion', '')
    fecha = datos_usuario.get('fecha', datetime.now().strftime('%d/%m/%Y'))
    norma = datos_usuario.get('norma', 'APA 7')
    
    doc = Document()
    
    # Título principal
    title = doc.add_heading('INFORME ACADÉMICO', 0)
    title.alignment = 1
    
    doc.add_heading(tema, level=1)
    doc.add_paragraph()
    
    doc.add_paragraph(f"Presentado por: {nombre}")
    if asignatura:
        doc.add_paragraph(f"Asignatura: {asignatura}")
    if profesor:
        doc.add_paragraph(f"Docente: {profesor}")
    if institucion:
        doc.add_paragraph(f"Institución: {institucion}")
    doc.add_paragraph(f"Fecha de entrega: {fecha}")
    doc.add_paragraph(f"Norma de citación: {norma}")
    doc.add_page_break()
    
    # Índice
    doc.add_heading('ÍNDICE', level=2)
    for titulo in ['INTRODUCCIÓN', 'OBJETIVOS', 'MARCO TEÓRICO', 'METODOLOGÍA', 'DESARROLLO', 'CONCLUSIONES', 'RECOMENDACIONES', 'REFERENCIAS BIBLIOGRÁFICAS']:
        doc.add_paragraph(f"• {titulo}")
    doc.add_page_break()
    
    # Secciones
    secciones_orden = [
        ("INTRODUCCIÓN", 'introduccion'),
        ("OBJETIVOS", 'objetivos'),
        ("MARCO TEÓRICO", 'marco_teorico'),
        ("METODOLOGÍA", 'metodologia'),
        ("DESARROLLO", 'desarrollo'),
        ("CONCLUSIONES", 'conclusiones'),
        ("RECOMENDACIONES", 'recomendaciones'),
        ("REFERENCIAS BIBLIOGRÁFICAS", 'referencias')
    ]
    
    for titulo, clave in secciones_orden:
        doc.add_heading(titulo, level=2)
        contenido = secciones.get(clave, '')
        if contenido:
            texto_limpio = contenido.replace('<br/>', '\n').replace('<b>', '').replace('</b>', '')
            doc.add_paragraph(texto_limpio)
        else:
            doc.add_paragraph("Contenido no disponible para esta sección.")
        doc.add_page_break()
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar', methods=['POST'])
def generar():
    try:
        data = request.json
        tema = data.get('tema', '').strip()
        nivel = data.get('nivel', 'universitario')
        modo = data.get('modo', 'rapido')
        tipo_informe = data.get('tipo_informe', 'academico')
        norma = data.get('norma', 'APA 7')
        nombre = data.get('nombre', 'Estudiante')
        asignatura = data.get('asignatura', '')
        profesor = data.get('profesor', '')
        institucion = data.get('institucion', '')
        
        if not tema:
            return jsonify({'success': False, 'error': 'El tema es requerido'}), 400
        
        # Obtener autores
        autores = data.get('autores', [])
        if autores:
            nombre_principal = autores[0].get('nombre', nombre)
        else:
            nombre_principal = nombre
        
        prompt = f"""Genera un informe académico profesional de tipo {tipo_informe} sobre: "{tema}"
Nivel educativo: {nivel}
Modo de generación: {modo}

ESTRUCTURA OBLIGATORIA (usa **negritas** solo para los títulos):

**INTRODUCCIÓN** (contexto, problema, justificación, 2-3 párrafos)
**OBJETIVOS** (1 objetivo general + 4 objetivos específicos)
**MARCO TEÓRICO** (conceptos clave, antecedentes, 3-4 párrafos)
**METODOLOGÍA** (tipo de investigación, población, técnicas, procedimiento)
**DESARROLLO** (resultados, análisis, hallazgos con datos numéricos)
**CONCLUSIONES** (5 puntos numerados con datos específicos)
**RECOMENDACIONES** (4 sugerencias prácticas)
**REFERENCIAS** (6 fuentes en formato {norma})

REQUISITOS:
- Escribe en español académico profesional
- Incluye datos numéricos específicos (porcentajes, fechas, cantidades)
- Sé específico y evita texto genérico
- Extensión: 5-10 páginas
"""
        
        contenido = llamar_deepseek(prompt)
        if not contenido:
            return jsonify({'success': False, 'error': 'No se pudo generar el contenido'}), 500
        
        secciones = {
            'introduccion': extraer_seccion(contenido, 'INTRODUCCIÓN'),
            'objetivos': extraer_seccion(contenido, 'OBJETIVOS'),
            'marco_teorico': extraer_seccion(contenido, 'MARCO TEÓRICO'),
            'metodologia': extraer_seccion(contenido, 'METODOLOGÍA'),
            'desarrollo': extraer_seccion(contenido, 'DESARROLLO'),
            'conclusiones': extraer_seccion(contenido, 'CONCLUSIONES'),
            'recomendaciones': extraer_seccion(contenido, 'RECOMENDACIONES'),
            'referencias': extraer_seccion(contenido, 'REFERENCIAS')
        }
        
        datos_usuario = {
            'nombre': nombre_principal,
            'tema': tema,
            'asignatura': asignatura,
            'profesor': profesor,
            'institucion': institucion,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'norma': norma
        }
        
        return jsonify({'success': True, 'secciones': secciones, 'datos_usuario': datos_usuario})
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/exportar-pdf', methods=['POST'])
def exportar_pdf():
    data = request.json
    filename, filepath = generar_pdf_profesional(data['datos_usuario'], data['secciones'])
    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route('/exportar-word', methods=['POST'])
def exportar_word():
    data = request.json
    buffer = generar_word_profesional(data['datos_usuario'], data['secciones'])
    return send_file(buffer, as_attachment=True, download_name=f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx")

@app.route('/preview', methods=['POST'])
def preview():
    try:
        data = request.json
        tema = data.get('tema', '')
        prompt = f"Genera un breve resumen ejecutivo sobre: {tema} en 300 palabras máximo."
        contenido = llamar_deepseek(prompt)
        if contenido:
            return jsonify({'success': True, 'contenido': contenido[:1000]})
        return jsonify({'success': False, 'error': 'No se pudo generar'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'api_configured': bool(DEEPSEEK_API_KEY)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
