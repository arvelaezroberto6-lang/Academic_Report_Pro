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
# CONFIGURACIÓN POR NIVEL EDUCATIVO
# ============================================================
def get_prompt_segun_nivel(tema, info_extra, nivel):
    """Genera el prompt según el nivel educativo seleccionado"""
    
    prompts = {
        "colegio": f"""Eres un asistente educativo. Genera un informe para estudiantes de colegio (14-17 años) sobre: "{tema}"

Información adicional: {info_extra if info_extra else 'No hay información adicional'}

ESTRUCTURA:
**INTRODUCCIÓN** (explica el tema con un ejemplo cotidiano)
**OBJETIVOS** (qué vamos a aprender)
**DESARROLLO** (explicación clara y sencilla)
**CONCLUSIONES** (lo más importante para recordar)
**RECOMENDACIONES** (cómo aplicar lo aprendido)

REQUISITOS:
- Usa lenguaje sencillo y claro
- Incluye ejemplos de la vida diaria
- Evita términos técnicos complicados
- Extensión: 2-3 páginas
- Escribe en español""",

        "tecnico": f"""Eres un instructor técnico. Genera un informe para estudiantes de nivel técnico o primeros años de universidad sobre: "{tema}"

Información adicional: {info_extra if info_extra else 'No hay información adicional'}

ESTRUCTURA:
**INTRODUCCIÓN** (contexto y aplicación práctica)
**OBJETIVOS** (1 general + 4 específicos)
**MARCO TEÓRICO** (conceptos clave explicados)
**METODOLOGÍA** (cómo se aborda el tema)
**DESARROLLO** (análisis con datos concretos)
**CONCLUSIONES** (4-5 puntos clave)
**RECOMENDACIONES** (3-4 sugerencias aplicables)
**REFERENCIAS** (4-5 fuentes)

REQUISITOS:
- Lenguaje profesional pero accesible
- Incluye términos técnicos con explicación
- Da ejemplos prácticos del campo
- Extensión: 4-6 páginas
- Escribe en español""",

        "universitario": f"""Eres un académico experto. Genera un informe para nivel universitario avanzado sobre: "{tema}"

Información adicional: {info_extra if info_extra else 'No hay información adicional'}

ESTRUCTURA:
**INTRODUCCIÓN** (contexto académico, estado del arte, justificación)
**OBJETIVOS** (1 general + 5 específicos detallados)
**MARCO TEÓRICO** (antecedentes, teorías, definiciones)
**METODOLOGÍA** (diseño, población, instrumentos, procedimiento)
**DESARROLLO** (análisis profundo, discusión de hallazgos)
**CONCLUSIONES** (5-6 conclusiones con implicaciones)
**RECOMENDACIONES** (4-5 sugerencias para investigadores)
**REFERENCIAS** (mínimo 8 fuentes académicas)

REQUISITOS:
- Lenguaje académico riguroso
- Profundidad analítica y crítica
- Citas a autores relevantes
- Extensión: 8-12 páginas
- Escribe en español"""
    }
    
    return prompts.get(nivel, prompts["universitario"])

# ============================================================
# FUNCIÓN PRINCIPAL DE GENERACIÓN CON IA
# ============================================================
def generar_informe_con_ia(tema, info_extra="", nivel="universitario"):
    """Genera informe usando DeepSeek API - Contenido 100% real generado por IA"""
    
    if not DEEPSEEK_API_KEY:
        logger.error("❌ No hay API key configurada")
        return None
    
    logger.info(f"🤖 Generando informe - Nivel: {nivel} - Tema: {tema[:50]}...")
    
    prompt = get_prompt_segun_nivel(tema, info_extra, nivel)
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Eres un asistente académico profesional. Generas contenido original, bien estructurado y adaptado al nivel educativo solicitado."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 6000 if nivel == "universitario" else (3500 if nivel == "tecnico" else 2000),
        "temperature": 0.7
    }
    
    try:
        logger.info("📡 Enviando solicitud a DeepSeek API...")
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

# ============================================================
# FUNCIÓN PARA MEJORAR REDACTAR (BOTONES DE MEJORA)
# ============================================================
def mejorar_redaccion(texto_original, accion="mejorar"):
    """Mejora, expande o simplifica el texto usando IA"""
    
    if not DEEPSEEK_API_KEY:
        return "Error: No hay API key configurada"
    
    acciones = {
        "mejorar": "Mejora la redacción del siguiente texto. Hazlo más claro, profesional y bien estructurado. No cambies el contenido principal:",
        "expandir": "Expande el siguiente texto. Añade más detalles, ejemplos y profundidad. Mantén la coherencia:",
        "simplificar": "Simplifica el siguiente texto. Hazlo más fácil de entender, usa lenguaje claro y ejemplos sencillos:"
    }
    
    prompt = f"""{acciones.get(accion, acciones['mejorar'])}

TEXTO ORIGINAL:
{texto_original}

TEXTO MEJORADO:"""
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Eres un asistente de edición de textos. Mejoras la redacción manteniendo el significado original."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 2000,
        "temperature": 0.5
    }
    
    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return texto_original
    except Exception as e:
        logger.error(f"Error en mejora: {e}")
        return texto_original

# ============================================================
# EXTRACCIÓN DE SECCIONES
# ============================================================
def extraer_secciones(contenido):
    """Extrae cada sección del contenido generado por IA"""
    
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
    
    # Patrones flexibles para diferentes formatos
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
            texto = texto.replace('\n', '<br/>')
            secciones[key] = texto
    
    return secciones

# ============================================================
# GENERADOR DE PDF
# ============================================================
def generar_pdf(datos_usuario, secciones):
    """Genera el PDF con el contenido generado por IA"""
    
    nombre = datos_usuario.get('nombre', 'Estudiante')
    tema = datos_usuario.get('tema', 'Tema de Investigación')
    nivel = datos_usuario.get('nivel', 'universitario')
    
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
    story.append(Paragraph(f"<b>Nivel:</b> {nivel}", styles['TextoCentrado']))
    story.append(Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')}", styles['TextoCentrado']))
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
        story.append(Spacer(1, 0.2*inch))
        contenido = secciones.get(clave, '')
        if contenido:
            story.append(Paragraph(contenido, styles['TextoJustificado']))
        else:
            story.append(Paragraph("Esta sección no fue generada automáticamente. Puedes agregar contenido manualmente si lo deseas.", styles['TextoJustificado']))
        story.append(PageBreak())
    
    doc.build(story)
    return filename, filepath

# ============================================================
# RUTAS DE LA API
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar', methods=['POST'])
def generar():
    try:
        data = request.json
        tema = data.get('tema', '').strip()
        info_extra = data.get('texto_completo', '')
        nombre = data.get('nombre', 'Estudiante')
        nivel = data.get('nivel', 'universitario')
        
        if not tema:
            return jsonify({'success': False, 'error': 'El tema es requerido'}), 400
        
        logger.info(f"📨 Generando - Nivel: {nivel} - Tema: {tema[:50]}")
        
        contenido_ia = generar_informe_con_ia(tema, info_extra, nivel)
        
        if contenido_ia:
            secciones = extraer_secciones(contenido_ia)
            logger.info("✅ Informe generado con IA")
        else:
            return jsonify({'success': False, 'error': 'No se pudo generar el informe. Verifica tu conexión y saldo de DeepSeek.'}), 500
        
        datos_usuario = {
            'nombre': nombre,
            'tema': tema,
            'nivel': nivel
        }
        
        filename, filepath = generar_pdf(datos_usuario, secciones)
        
        return jsonify({
            'success': True,
            'download_url': f'/descargar/{filename}'
        })
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/mejorar', methods=['POST'])
def mejorar():
    """Endpoint para mejorar/expandir/simplificar texto"""
    try:
        data = request.json
        texto = data.get('texto', '')
        accion = data.get('accion', 'mejorar')
        
        if not texto:
            return jsonify({'success': False, 'error': 'No hay texto para mejorar'}), 400
        
        texto_mejorado = mejorar_redaccion(texto, accion)
        
        return jsonify({
            'success': True,
            'texto_mejorado': texto_mejorado
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/descargar/<filename>')
def descargar(filename):
    filepath = os.path.join('informes_generados', filename)
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'Archivo no encontrado'}), 404
    return send_file(filepath, as_attachment=True, download_name=filename, mimetype='application/pdf')

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
