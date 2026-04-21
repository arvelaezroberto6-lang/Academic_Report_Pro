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

# Configuración
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear directorios
os.makedirs('informes_generados', exist_ok=True)

# ========== CONFIGURACIÓN DE DEEPSEEK ==========
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

logger.info("=" * 60)
logger.info("🚀 ACADEMIC REPORT PRO - VERSIÓN CON DEEPSEEK")
logger.info(f"🔑 DeepSeek API Key configurada: {'SÍ ✅' if DEEPSEEK_API_KEY else 'NO ❌'}")
logger.info("=" * 60)

# ========== GENERAR INFORME CON DEEPSEEK ==========
def generar_informe_con_ia(tema, info_extra=""):
    """Genera informe usando DeepSeek API"""
    
    if not DEEPSEEK_API_KEY:
        logger.error("❌ No hay API key de DeepSeek")
        return None
    
    logger.info(f"🤖 Generando informe con DeepSeek sobre: {tema[:50]}...")
    
    prompt = f"""Genera un informe académico profesional sobre: "{tema}"

Información adicional: {info_extra if info_extra else 'Sin información adicional'}

ESTRUCTURA OBLIGATORIA:

**INTRODUCCIÓN** (2-3 párrafos: contexto, problema, justificación)

**OBJETIVOS**
- Objetivo general (1)
- Objetivos específicos (4-5)

**MARCO TEÓRICO** (conceptos clave, antecedentes)

**METODOLOGÍA** (tipo de investigación, población, técnicas)

**DESARROLLO** (resultados, análisis, hallazgos)

**CONCLUSIONES** (5 puntos numerados)

**RECOMENDACIONES** (3-4 sugerencias)

**REFERENCIAS** (5-6 fuentes en formato APA)

REQUISITOS:
- Escribe en español, tono académico pero natural
- Usa **negritas** solo para los títulos de sección
- Sé específico y evita texto genérico
- Extensión: 1500-2000 palabras"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Eres un asistente académico profesional. Generas informes en español con estructura clara y contenido de alta calidad."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4000,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=120)
        
        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado['choices'][0]['message']['content']
            logger.info(f"✅ Informe generado ({len(contenido)} caracteres)")
            return contenido
        else:
            logger.error(f"❌ Error HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return None

# ========== EXTRAER SECCIONES ==========
def extraer_secciones(contenido):
    """Extrae las secciones del contenido generado por IA"""
    import re
    
    secciones = {
        'introduccion': '',
        'objetivos': '',
        'marco_teorico': '',
        'metodologia': '',
        'desarrollo': '',
        'conclusiones': '',
        'recomendaciones': '',
        'referencias': ''
    }
    
    patrones = {
        'introduccion': r'\*\*INTRODUCCIÓN\*\*:?(.*?)(?=\*\*OBJETIVOS|\*\*MARCO|\*\*METODOLOGÍA|\*\*DESARROLLO|\*\*CONCLUSIONES|$)',
        'objetivos': r'\*\*OBJETIVOS\*\*:?(.*?)(?=\*\*MARCO|\*\*METODOLOGÍA|\*\*DESARROLLO|\*\*CONCLUSIONES|$)',
        'marco_teorico': r'\*\*MARCO TEÓRICO\*\*:?(.*?)(?=\*\*METODOLOGÍA|\*\*DESARROLLO|\*\*CONCLUSIONES|$)',
        'metodologia': r'\*\*METODOLOGÍA\*\*:?(.*?)(?=\*\*DESARROLLO|\*\*CONCLUSIONES|$)',
        'desarrollo': r'\*\*DESARROLLO\*\*:?(.*?)(?=\*\*CONCLUSIONES|$)',
        'conclusiones': r'\*\*CONCLUSIONES\*\*:?(.*?)(?=\*\*RECOMENDACIONES|$)',
        'recomendaciones': r'\*\*RECOMENDACIONES\*\*:?(.*?)(?=\*\*REFERENCIAS|$)',
        'referencias': r'\*\*REFERENCIAS\*\*:?(.*?)$'
    }
    
    for key, patron in patrones.items():
        match = re.search(patron, contenido, re.DOTALL | re.IGNORECASE)
        if match:
            texto = match.group(1).strip()
            texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
            secciones[key] = texto
    
    return secciones

# ========== CONTENIDO DE RESPALDO (si la IA falla) ==========
def contenido_respaldo(tema):
    """Contenido genérico de respaldo (solo si la IA falla)"""
    return {
        'introduccion': f"Este es un informe sobre {tema}. La IA no está disponible en este momento.",
        'objetivos': "1. Objetivo no disponible\n2. Objetivo no disponible",
        'marco_teorico': "Contenido no disponible. Por favor, verifica la conexión con la IA.",
        'metodologia': "Contenido no disponible.",
        'desarrollo': "Contenido no disponible.",
        'conclusiones': "Contenido no disponible.",
        'recomendaciones': "Contenido no disponible.",
        'referencias': "No hay referencias disponibles."
    }

# ========== GENERAR PDF ==========
def generar_pdf(datos_usuario, secciones):
    """Genera el PDF con el contenido"""
    
    filename = f"informe_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join('informes_generados', filename)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='TextoJustificado',
        parent=styles['Normal'],
        alignment=TA_JUSTIFY,
        fontSize=11,
        fontName='Times-Roman',
        spaceAfter=12,
        leading=16
    ))
    styles.add(ParagraphStyle(
        name='Titulo1',
        parent=styles['Heading1'],
        fontSize=16,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a365d'),
        spaceBefore=24,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='TituloPortada',
        parent=styles['Title'],
        fontSize=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a365d')
    ))
    
    doc = SimpleDocTemplate(filepath, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    story = []
    
    # Portada
    story.append(Spacer(1, 2.5*inch))
    story.append(Paragraph("INFORME ACADÉMICO", styles['TituloPortada']))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(datos_usuario.get('tema', 'Tema').upper(), styles['TextoJustificado']))
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph(f"<b>Presentado por:</b> {datos_usuario.get('nombre', 'Estudiante')}", styles['TextoJustificado']))
    story.append(Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')}", styles['TextoJustificado']))
    story.append(PageBreak())
    
    # Secciones
    secciones_orden = [
        ("1. INTRODUCCIÓN", 'introduccion'),
        ("2. OBJETIVOS", 'objetivos'),
        ("3. MARCO TEÓRICO", 'marco_teorico'),
        ("4. METODOLOGÍA", 'metodologia'),
        ("5. DESARROLLO", 'desarrollo'),
        ("6. CONCLUSIONES", 'conclusiones'),
        ("7. RECOMENDACIONES", 'recomendaciones'),
        ("8. REFERENCIAS", 'referencias')
    ]
    
    for titulo, clave in secciones_orden:
        story.append(Paragraph(titulo, styles['Titulo1']))
        contenido = secciones.get(clave, '')
        if contenido:
            story.append(Paragraph(contenido, styles['TextoJustificado']))
        else:
            story.append(Paragraph("Contenido no disponible", styles['TextoJustificado']))
        story.append(PageBreak())
    
    doc.build(story)
    return filename, filepath

# ========== RUTAS ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar', methods=['POST'])
def generar():
    try:
        data = request.json
        tema = data.get('tema', 'Tema general')
        info_extra = data.get('texto_completo', '')
        nombre = data.get('nombre', 'Estudiante')
        
        logger.info(f"📨 Generando informe para: {nombre} - Tema: {tema[:50]}")
        
        # Intentar generar con IA
        contenido_ia = generar_informe_con_ia(tema, info_extra)
        
        if contenido_ia:
            secciones = extraer_secciones(contenido_ia)
            logger.info("✅ Informe generado con IA")
        else:
            secciones = contenido_respaldo(tema)
            logger.warning("⚠️ Usando contenido de respaldo (IA falló)")
        
        datos_usuario = {
            'nombre': nombre,
            'tema': tema
        }
        
        filename, filepath = generar_pdf(datos_usuario, secciones)
        
        return jsonify({
            'success': True,
            'download_url': f'/descargar/{filename}'
        })
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/descargar/<filename>')
def descargar(filename):
    return send_file(
        os.path.join('informes_generados', filename),
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
