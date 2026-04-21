from flask import Flask, render_template, request, jsonify, send_file
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
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
logger.info("🚀 ACADEMIC REPORT PRO - VERSIÓN FUNCIONANDO")
logger.info(f"🔑 API Key configurada: {'SÍ ✅' if DEEPSEEK_API_KEY else 'NO ❌'}")
logger.info("=" * 60)

def llamar_deepseek(prompt):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Eres un asistente académico profesional. Generas contenido original y bien estructurado en español."},
            {"role": "user", "content": prompt}
        ],
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

def generar_pdf(tema, nombre, secciones):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"informe_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join('informes_generados', filename)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TextoJustificado', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=11, fontName='Times-Roman', spaceAfter=12, leading=16))
    styles.add(ParagraphStyle(name='Titulo1', parent=styles['Heading1'], fontSize=16, fontName='Helvetica-Bold', textColor=colors.HexColor('#1a365d'), spaceBefore=24, spaceAfter=12))
    styles.add(ParagraphStyle(name='TituloPortada', parent=styles['Title'], fontSize=24, alignment=TA_CENTER, textColor=colors.HexColor('#1a365d')))
    styles.add(ParagraphStyle(name='TextoCentrado', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12))
    
    doc = SimpleDocTemplate(filepath, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    story = []
    
    # Portada
    story.append(Spacer(1, 2.0*inch))
    story.append(Paragraph("INFORME ACADÉMICO", styles['TituloPortada']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(tema.upper(), styles['TextoCentrado']))
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph(f"<b>Presentado por:</b> {nombre}", styles['TextoCentrado']))
    story.append(Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')}", styles['TextoCentrado']))
    story.append(PageBreak())
    
    # Secciones
    secciones_lista = [
        ("1. INTRODUCCIÓN", 'introduccion'),
        ("2. OBJETIVOS", 'objetivos'),
        ("3. MARCO TEÓRICO", 'marco_teorico'),
        ("4. METODOLOGÍA", 'metodologia'),
        ("5. DESARROLLO", 'desarrollo'),
        ("6. CONCLUSIONES", 'conclusiones'),
        ("7. RECOMENDACIONES", 'recomendaciones'),
        ("8. REFERENCIAS", 'referencias')
    ]
    
    for titulo, clave in secciones_lista:
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar', methods=['POST'])
def generar():
    try:
        data = request.json
        tema = data.get('tema', '').strip()
        info_extra = data.get('texto_usuario', '')
        nombre = data.get('nombre', 'Estudiante')
        
        if not tema:
            return jsonify({'success': False, 'error': 'El tema es requerido'}), 400
        
        logger.info(f"📨 Generando informe - Tema: {tema[:50]}...")
        
        prompt = f"""Genera un informe académico profesional sobre: "{tema}"

Información adicional: {info_extra if info_extra else 'No hay información adicional'}

ESTRUCTURA OBLIGATORIA:

**INTRODUCCIÓN** (contexto, problema, justificación)
**OBJETIVOS** (1 general + 4 específicos)
**MARCO TEÓRICO** (conceptos clave, antecedentes)
**METODOLOGÍA** (tipo de investigación, población, técnicas)
**DESARROLLO** (resultados, análisis, hallazgos)
**CONCLUSIONES** (5 puntos numerados)
**RECOMENDACIONES** (3-4 sugerencias)
**REFERENCIAS** (5-6 fuentes en formato APA)

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
        
        filename, filepath = generar_pdf(tema, nombre, secciones)
        
        return send_file(filepath, as_attachment=True, download_name=filename, mimetype='application/pdf')
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'api_configured': bool(DEEPSEEK_API_KEY)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
