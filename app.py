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
# CONSTRUCCIÓN DE PROMPT SEGÚN TIPO DE INFORME
# ============================================================
def construir_prompt(tema, info_extra, tipo_informe, norma, modo):
    """Construye el prompt según el tipo de informe y modo seleccionado"""
    
    info_extra_texto = info_extra if info_extra else 'No hay información adicional'
    
    # Estructuras según tipo de informe
    estructuras = {
        "academico": """
**INTRODUCCIÓN** (contexto, problema, justificación, 2-3 párrafos)
**OBJETIVOS** (1 general + 4-5 específicos)
**MARCO TEÓRICO** (conceptos clave, antecedentes, definiciones)
**METODOLOGÍA** (tipo de investigación, población, técnicas, procedimiento)
**DESARROLLO** (resultados, análisis, discusión de hallazgos)
**CONCLUSIONES** (5-6 puntos numerados)
**RECOMENDACIONES** (3-4 sugerencias prácticas)
**REFERENCIAS** (6-8 fuentes en formato {norma})""",
        
        "laboratorio": """
**INTRODUCCIÓN** (objetivo del experimento, fundamento teórico, hipótesis)
**MATERIALES Y MÉTODOS** (equipos, reactivos, procedimiento paso a paso)
**RESULTADOS** (datos obtenidos, tablas, observaciones)
**DISCUSIÓN** (análisis de resultados, comparación con teoría, errores)
**CONCLUSIONES** (5 conclusiones específicas)
**RECOMENDACIONES** (mejoras para futuros experimentos)
**REFERENCIAS** (5-6 fuentes en formato {norma})""",
        
        "ejecutivo": """
**RESUMEN EJECUTIVO** (hallazgos clave en 1 página)
**INTRODUCCIÓN** (contexto empresarial, propósito, alcance)
**ANÁLISIS DE SITUACIÓN** (FODA, mercado, competencia, KPIs)
**HALLAZGOS CLAVE** (oportunidades, amenazas, tendencias)
**RECOMENDACIONES** (estrategias corto, mediano y largo plazo)
**CONCLUSIONES** (5 puntos principales)
**REFERENCIAS** (fuentes consultadas en formato {norma})""",
        
        "tesis": """
**RESUMEN** (abstract en español, 250 palabras, palabras clave)
**INTRODUCCIÓN** (contexto, problema, justificación, antecedentes)
**OBJETIVOS** (1 general + 5 específicos)
**MARCO TEÓRICO** (bases teóricas, estado del arte, definiciones)
**METODOLOGÍA** (diseño, población, instrumentos, procedimiento)
**RESULTADOS ESPERADOS** (hallazgos anticipados, limitaciones)
**CONCLUSIONES PRELIMINARES** (5-6 conclusiones)
**REFERENCIAS** (mínimo 12 fuentes en formato {norma})"""
    }
    
    estructura = estructuras.get(tipo_informe, estructuras["academico"])
    
    prompt = f"""Eres un asistente académico experto. Genera un informe de tipo {tipo_informe.upper()} sobre: "{tema}"

Información adicional del usuario: {info_extra_texto}

ESTRUCTURA OBLIGATORIA:
{estructura}

REQUISITOS:
- Escribe en español académico profesional
- Usa **negritas** SOLO para los títulos de sección
- Sé específico, incluye datos concretos, fechas, nombres
- Extensión: 5-10 páginas según el tipo de informe
- Mantén coherencia entre todas las secciones

¡Genera un informe completo y de alta calidad!"""
    
    return prompt

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
            {"role": "system", "content": "Eres un asistente académico profesional. Generas contenido original, bien estructurado y de alta calidad en español."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 6000,
        "temperature": 0.7
    }
    
    try:
        logger.info("📡 Enviando solicitud a DeepSeek API...")
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=120)
        
        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado['choices'][0]['message']['content']
            logger.info(f"✅ Contenido generado ({len(contenido)} caracteres)")
            return contenido
        else:
            logger.error(f"❌ Error HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return None

# ============================================================
# GENERAR INFORME COMPLETO
# ============================================================
def generar_informe_con_ia(tema, info_extra, tipo_informe, norma, modo):
    """Genera el informe completo usando DeepSeek"""
    
    prompt = construir_prompt(tema, info_extra, tipo_informe, norma, modo)
    contenido = llamar_deepseek(prompt)
    
    if not contenido:
        return None
    
    # Extraer secciones básicas
    secciones = {
        'introduccion': extraer_seccion(contenido, 'INTRODUCCIÓN'),
        'objetivos': extraer_seccion(contenido, 'OBJETIVOS'),
        'marco_teorico': extraer_seccion(contenido, 'MARCO TEÓRICO'),
        'metodologia': extraer_seccion(contenido, 'METODOLOGÍA'),
        'desarrollo': extraer_seccion(contenido, 'DESARROLLO') or extraer_seccion(contenido, 'RESULTADOS'),
        'conclusiones': extraer_seccion(contenido, 'CONCLUSIONES'),
        'recomendaciones': extraer_seccion(contenido, 'RECOMENDACIONES'),
        'referencias': extraer_seccion(contenido, 'REFERENCIAS')
    }
    
    return secciones

def extraer_seccion(contenido, nombre):
    """Extrae una sección del contenido generado"""
    patron = rf'\*\*{nombre}\*\*:?(.*?)(?=\*\*[A-Z]|REFERENCIAS|CONCLUSIONES|RECOMENDACIONES|$)'
    match = re.search(patron, contenido, re.DOTALL | re.IGNORECASE)
    if match:
        texto = match.group(1).strip()
        texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
        texto = texto.replace('\n', '<br/>')
        return texto
    return ""

# ============================================================
# GENERAR PDF
# ============================================================
def generar_pdf(datos_usuario, secciones):
    """Genera el PDF profesional"""
    
    nombre = datos_usuario.get('nombre', 'Estudiante')
    tema = datos_usuario.get('tema', 'Tema de Investigación')
    asignatura = datos_usuario.get('asignatura', '')
    profesor = datos_usuario.get('profesor', '')
    institucion = datos_usuario.get('institucion', '')
    ciudad = datos_usuario.get('ciudad', '')
    fecha = datos_usuario.get('fecha', datetime.now().strftime('%d/%m/%Y'))
    norma = datos_usuario.get('norma', 'APA 7')
    tipo_informe = datos_usuario.get('tipo_informe', 'academico')
    
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
    if asignatura:
        story.append(Paragraph(f"<b>Asignatura:</b> {asignatura}", styles['TextoCentrado']))
    if profesor:
        story.append(Paragraph(f"<b>Docente:</b> {profesor}", styles['TextoCentrado']))
    if institucion:
        story.append(Paragraph(f"<b>Institución:</b> {institucion}", styles['TextoCentrado']))
    if ciudad:
        story.append(Paragraph(f"<b>Ciudad:</b> {ciudad}", styles['TextoCentrado']))
    story.append(Paragraph(f"<b>Fecha:</b> {fecha}", styles['TextoCentrado']))
    story.append(Paragraph(f"<b>Norma:</b> {norma}", styles['TextoCentrado']))
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
            story.append(Paragraph("Esta sección será generada por IA al completar el informe.", styles['TextoJustificado']))
        story.append(PageBreak())
    
    doc.build(story)
    return filename, filepath

# ============================================================
# RUTAS DE LA API
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/preview', methods=['POST'])
def preview():
    """Genera una vista previa del contenido sin crear el PDF"""
    try:
        data = request.json
        tema = data.get('tema', '')
        info_extra = data.get('texto_usuario', '')
        tipo_informe = data.get('tipo_informe', 'academico')
        norma = data.get('norma', 'APA 7')
        modo = data.get('modo', 'rapido')
        
        if not tema:
            return jsonify({'success': False, 'error': 'El tema es requerido'}), 400
        
        prompt = construir_prompt(tema, info_extra, tipo_informe, norma, modo)
        contenido = llamar_deepseek(prompt)
        
        if contenido:
            return jsonify({'success': True, 'contenido': contenido[:3000] + '...'})
        else:
            return jsonify({'success': False, 'error': 'No se pudo generar el contenido'}), 500
            
    except Exception as e:
        logger.error(f"Error en preview: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/generar', methods=['POST'])
def generar():
    """Genera el informe completo y devuelve el PDF"""
    try:
        data = request.json
        
        # Obtener datos del formulario
        tema = data.get('tema', '').strip()
        info_extra = data.get('texto_usuario', '')
        tipo_informe = data.get('tipo_informe', 'academico')
        norma = data.get('norma', 'APA 7')
        modo = data.get('modo', 'rapido')
        
        # Datos de autores
        autores = data.get('autores', [])
        nombre_principal = autores[0].get('nombre', 'Estudiante') if autores else 'Estudiante'
        
        # Datos académicos
        asignatura = data.get('asignatura', '')
        profesor = data.get('profesor', '')
        institucion = data.get('institucion', '')
        ciudad = data.get('ciudad', '')
        fecha = data.get('fecha', datetime.now().strftime('%d/%m/%Y'))
        
        if not tema:
            return jsonify({'success': False, 'error': 'El tema es requerido'}), 400
        
        if not autores:
            return jsonify({'success': False, 'error': 'Agrega al menos un autor'}), 400
        
        logger.info(f"📨 Generando informe - Tipo: {tipo_informe} - Tema: {tema[:50]}...")
        
        # Generar con IA
        secciones = generar_informe_con_ia(tema, info_extra, tipo_informe, norma, modo)
        
        if not secciones:
            return jsonify({'success': False, 'error': 'No se pudo generar el informe. Verifica tu conexión y saldo de DeepSeek.'}), 500
        
        # Preparar datos para el PDF
        datos_usuario = {
            'nombre': nombre_principal,
            'tema': tema,
            'asignatura': asignatura,
            'profesor': profesor,
            'institucion': institucion,
            'ciudad': ciudad,
            'fecha': fecha,
            'norma': norma,
            'tipo_informe': tipo_informe
        }
        
        filename, filepath = generar_pdf(datos_usuario, secciones)
        
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
