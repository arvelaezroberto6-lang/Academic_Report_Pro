from flask import Flask, render_template, request, jsonify, send_file
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from docx import Document
from io import BytesIO
import os
import uuid
from datetime import datetime
import requests
import logging
import re

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.makedirs('informes_generados', exist_ok=True)

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

logger.info("=" * 60)
logger.info("🚀 ACADEMIC REPORT PRO - VERSIÓN DEFINITIVA")
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

def generar_pdf(datos_usuario, secciones):
    nombre = datos_usuario.get('nombre', 'Estudiante')
    tema = datos_usuario.get('tema', 'Tema')
    asignatura = datos_usuario.get('asignatura', '')
    profesor = datos_usuario.get('profesor', '')
    institucion = datos_usuario.get('institucion', '')
    fecha = datos_usuario.get('fecha', datetime.now().strftime('%d/%m/%Y'))
    norma = datos_usuario.get('norma', 'APA 7')
    
    filename = f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join('informes_generados', filename)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TextoJustificado', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=11, fontName='Times-Roman', spaceAfter=12, leading=16))
    styles.add(ParagraphStyle(name='Titulo1', parent=styles['Heading1'], fontSize=16, fontName='Helvetica-Bold', textColor=colors.HexColor('#1a365d'), spaceBefore=24, spaceAfter=12))
    styles.add(ParagraphStyle(name='TituloPortada', parent=styles['Title'], fontSize=24, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='TextoCentrado', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12))
    
    doc = SimpleDocTemplate(filepath, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    story = []
    
    story.append(Spacer(1, 2.0*inch))
    story.append(Paragraph("INFORME ACADÉMICO", styles['TituloPortada']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(tema.upper(), styles['TextoCentrado']))
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph(f"Presentado por: {nombre}", styles['TextoCentrado']))
    if asignatura: story.append(Paragraph(f"Asignatura: {asignatura}", styles['TextoCentrado']))
    if profesor: story.append(Paragraph(f"Docente: {profesor}", styles['TextoCentrado']))
    if institucion: story.append(Paragraph(f"Institución: {institucion}", styles['TextoCentrado']))
    story.append(Paragraph(f"Fecha: {fecha}", styles['TextoCentrado']))
    story.append(Paragraph(f"Norma: {norma}", styles['TextoCentrado']))
    story.append(PageBreak())
    
    for titulo, clave in [("1. INTRODUCCIÓN", 'introduccion'), ("2. OBJETIVOS", 'objetivos'), ("3. MARCO TEÓRICO", 'marco_teorico'), ("4. METODOLOGÍA", 'metodologia'), ("5. DESARROLLO", 'desarrollo'), ("6. CONCLUSIONES", 'conclusiones'), ("7. RECOMENDACIONES", 'recomendaciones'), ("8. REFERENCIAS", 'referencias')]:
        story.append(Paragraph(titulo, styles['Titulo1']))
        story.append(Spacer(1, 0.2*inch))
        contenido = secciones.get(clave, '')
        if contenido:
            story.append(Paragraph(contenido, styles['TextoJustificado']))
        else:
            story.append(Paragraph("No se pudo generar esta sección.", styles['TextoJustificado']))
        story.append(PageBreak())
    
    doc.build(story)
    return filename, filepath

def generar_word(datos_usuario, secciones):
    nombre = datos_usuario.get('nombre', 'Estudiante')
    tema = datos_usuario.get('tema', 'Tema')
    asignatura = datos_usuario.get('asignatura', '')
    profesor = datos_usuario.get('profesor', '')
    institucion = datos_usuario.get('institucion', '')
    fecha = datos_usuario.get('fecha', datetime.now().strftime('%d/%m/%Y'))
    norma = datos_usuario.get('norma', 'APA 7')
    
    doc = Document()
    doc.add_heading('INFORME ACADÉMICO', 0)
    doc.add_heading(tema, level=1)
    doc.add_paragraph(f"Presentado por: {nombre}")
    if asignatura: doc.add_paragraph(f"Asignatura: {asignatura}")
    if profesor: doc.add_paragraph(f"Docente: {profesor}")
    if institucion: doc.add_paragraph(f"Institución: {institucion}")
    doc.add_paragraph(f"Fecha: {fecha}")
    doc.add_paragraph(f"Norma: {norma}")
    doc.add_page_break()
    
    for titulo, clave in [("INTRODUCCIÓN", 'introduccion'), ("OBJETIVOS", 'objetivos'), ("MARCO TEÓRICO", 'marco_teorico'), ("METODOLOGÍA", 'metodologia'), ("DESARROLLO", 'desarrollo'), ("CONCLUSIONES", 'conclusiones'), ("RECOMENDACIONES", 'recomendaciones'), ("REFERENCIAS", 'referencias')]:
        doc.add_heading(titulo, level=2)
        contenido = secciones.get(clave, '')
        if contenido:
            doc.add_paragraph(contenido.replace('<br/>', '\n').replace('<b>', '').replace('</b>', ''))
        else:
            doc.add_paragraph("No se pudo generar esta sección.")
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
Nivel: {nivel}
Modo: {modo}

ESTRUCTURA OBLIGATORIA:
**INTRODUCCIÓN**
**OBJETIVOS** (1 general + 4 específicos)
**MARCO TEÓRICO**
**METODOLOGÍA**
**DESARROLLO**
**CONCLUSIONES** (5 puntos)
**RECOMENDACIONES** (4 sugerencias)
**REFERENCIAS** (6 fuentes en formato {norma})

Escribe en español académico profesional.
Usa **negritas** solo para los títulos.
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
    filename, filepath = generar_pdf(data['datos_usuario'], data['secciones'])
    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route('/exportar-word', methods=['POST'])
def exportar_word():
    data = request.json
    buffer = generar_word(data['datos_usuario'], data['secciones'])
    return send_file(buffer, as_attachment=True, download_name=f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx")

@app.route('/preview', methods=['POST'])
def preview():
    try:
        data = request.json
        tema = data.get('tema', '')
        prompt = f"Genera un breve resumen sobre: {tema}"
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
