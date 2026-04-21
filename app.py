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

# ============================================================
# CONFIGURACIÓN INICIAL
# ============================================================
app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

os.makedirs('informes_generados', exist_ok=True)

# ============================================================
# CONFIGURACIÓN DE DEEPSEEK
# ============================================================
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

logger.info("=" * 60)
logger.info("🚀 ACADEMIC REPORT PRO")
logger.info(f"🔑 API Key configurada: {'SÍ ✅' if DEEPSEEK_API_KEY else 'NO ❌'}")
logger.info("=" * 60)

# ============================================================
# FUNCIÓN PARA LLAMAR A DEEPSEEK
# ============================================================
def llamar_deepseek(prompt):
    """Llama a la API de DeepSeek y devuelve el contenido generado"""
    
    if not DEEPSEEK_API_KEY:
        logger.error("❌ No hay API key configurada")
        return None
    
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
        "max_tokens": 4000,
        "temperature": 0.7
    }
    
    try:
        logger.info("📡 Enviando solicitud a DeepSeek...")
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=90)
        
        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado['choices'][0]['message']['content']
            logger.info(f"✅ Contenido recibido ({len(contenido)} caracteres)")
            return contenido
        else:
            logger.error(f"❌ Error HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return None

# ============================================================
# GENERAR PDF SIMPLE
# ============================================================
def generar_pdf_simple(tema, contenido, nombre):
    """Genera un PDF simple con el contenido"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    filename = f"informe_{timestamp}_{unique_id}.pdf"
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
        fontSize=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a365d')
    ))
    
    styles.add(ParagraphStyle(
        name='TextoCentrado',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=12
    ))
    
    doc = SimpleDocTemplate(filepath, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    story = []
    
    # Portada
    story.append(Spacer(1, 2.5*inch))
    story.append(Paragraph("INFORME ACADÉMICO", styles['TituloPortada']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(tema.upper(), styles['TextoCentrado']))
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph(f"<b>Presentado por:</b> {nombre}", styles['TextoCentrado']))
    story.append(Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')}", styles['TextoCentrado']))
    story.append(PageBreak())
    
    # Contenido
    story.append(Paragraph("INFORME GENERADO POR IA", styles['Titulo1']))
    story.append(Spacer(1, 0.2*inch))
    
    # Limpiar y agregar contenido
    contenido_limpio = contenido.replace('\n', '<br/>')
    story.append(Paragraph(contenido_limpio, styles['TextoJustificado']))
    
    doc.build(story)
    return filename, filepath

# ============================================================
# RUTAS DE LA API
# ============================================================
@app.route('/')
def index():
    return "✅ API funcionando. Usa POST /generar para generar informes."

@app.route('/generar', methods=['POST'])
def generar():
    try:
        data = request.json
        tema = data.get('tema', '').strip()
        info_extra = data.get('texto_usuario', '')
        nombre = data.get('nombre', 'Estudiante')
        
        if not tema:
            return jsonify({'success': False, 'error': 'El tema es requerido'}), 400
        
        logger.info(f"📨 Generando informe para: {nombre} - Tema: {tema[:50]}...")
        
        # Construir prompt
        prompt = f"""Genera un informe académico profesional sobre: "{tema}"

Información adicional: {info_extra if info_extra else 'No hay información adicional'}

Estructura sugerida:
1. INTRODUCCIÓN (contexto y justificación)
2. OBJETIVOS (1 general y 3 específicos)
3. DESARROLLO (análisis del tema)
4. CONCLUSIONES (3-5 puntos)
5. RECOMENDACIONES (2-3 sugerencias)

Escribe en español académico, con un tono profesional pero claro.
Extensión: aproximadamente 1000 palabras.
"""
        
        # Generar con IA
        contenido_ia = llamar_deepseek(prompt)
        
        if not contenido_ia:
            return jsonify({'success': False, 'error': 'No se pudo generar el contenido con la IA'}), 500
        
        # Generar PDF
        filename, filepath = generar_pdf_simple(tema, contenido_ia, nombre)
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Error en generar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'api_configured': bool(DEEPSEEK_API_KEY),
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
