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
# CONSTRUCCIÓN DE PROMPT
# ============================================================
def construir_prompt(tema, info_extra, tipo_informe, norma):
    """Construye el prompt para DeepSeek"""
    
    info_extra_texto = info_extra if info_extra else 'No hay información adicional'
    
    prompt = f"""Eres un asistente académico experto. Genera un informe de tipo {tipo_informe.upper()} sobre: "{tema}"

Información adicional del usuario: {info_extra_texto}

⚠️ IMPORTANTE: Debes seguir EXACTAMENTE este formato, con los títulos en **negritas** y en el mismo orden:

**INTRODUCCIÓN**
[Escribe aquí la introducción, 2-3 párrafos]

**OBJETIVOS**
- Objetivo General: [escribe aquí]
- Objetivos Específicos:
  1. [escribe aquí]
  2. [escribe aquí]
  3. [escribe aquí]
  4. [escribe aquí]
  5. [escribe aquí]

**MARCO TEÓRICO**
[Escribe aquí el marco teórico, 3-4 párrafos]

**METODOLOGÍA**
[Escribe aquí la metodología, 2-3 párrafos]

**DESARROLLO**
[Escribe aquí el desarrollo, 3-4 párrafos]

**CONCLUSIONES**
1. [conclusión 1]
2. [conclusión 2]
3. [conclusión 3]
4. [conclusión 4]
5. [conclusión 5]

**RECOMENDACIONES**
1. [recomendación 1]
2. [recomendación 2]
3. [recomendación 3]
4. [recomendación 4]

**REFERENCIAS**
- [Referencia 1 en formato {norma}]
- [Referencia 2 en formato {norma}]
- [Referencia 3 en formato {norma}]
- [Referencia 4 en formato {norma}]
- [Referencia 5 en formato {norma}]
- [Referencia 6 en formato {norma}]

REQUISITOS:
- Escribe en español académico
- Usa **negritas** para los títulos
- Sé específico y detallado
- No omitas ninguna sección"""
    
    return prompt

# ============================================================
# FUNCIÓN PARA LLAMAR A DEEPSEEK
# ============================================================
def llamar_deepseek(prompt):
    """Llama a la API de DeepSeek"""
    
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
        "max_tokens": 6000,
        "temperature": 0.7
    }
    
    try:
        logger.info("📡 Enviando solicitud a DeepSeek...")
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=120)
        
        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado['choices'][0]['message']['content']
            logger.info(f"✅ Contenido recibido ({len(contenido)} caracteres)")
            return contenido
        else:
            logger.error(f"❌ Error HTTP {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return None

# ============================================================
# EXTRACCIÓN DE SECCIONES - VERSIÓN CORREGIDA
# ============================================================
def formatear_texto(texto):
    """Formatea el texto para ReportLab"""
    texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
    texto = texto.replace('\n', '<br/>')
    texto = re.sub(r'<br/>\s*<br/>', '<br/><br/>', texto)
    return texto.strip()

def extraer_seccion(contenido, nombre):
    """Extrae una sección del contenido - VERSIÓN CORREGIDA para RECOMENDACIONES"""
    
    if not contenido:
        return ""
    
    # Lista de patrones MUY amplia para capturar cualquier formato
    patrones = [
        # Patrón 1: **INTRODUCCIÓN** texto (con o sin espacio después)
        rf'\*\*{nombre}\*\*:?\s*(.*?)(?=\*\*[A-ZÁÉÍÓÚÜÑ]|\Z)',
        
        # Patrón 2: **INTRODUCCIÓN** sin espacio ni nada
        rf'\*\*{nombre}\*\*(.*?)(?=\*\*[A-ZÁÉÍÓÚÜÑ]|\Z)',
        
        # Patrón 3: INTRODUCCIÓN (sin asteriscos) con línea de guiones
        rf'\n{nombre}\n[=\-]+\s*(.*?)(?=\n[A-ZÁÉÍÓÚÜÑ]|\Z)',
        
        # Patrón 4: 1. INTRODUCCIÓN texto hasta 2.
        rf'\d+\.\s*{nombre}\s*(.*?)(?=\d+\.\s*[A-ZÁÉÍÓÚÜÑ]|\Z)',
        
        # Patrón 5: ### INTRODUCCIÓN
        rf'###\s*{nombre}\s*(.*?)(?=###|\Z)',
        
        # Patrón 6: RECOMENDACIONES en mayúsculas o minúsculas (más flexible)
        rf'(?i)\*\*RECOMENDACIONES?\*\*:?\s*(.*?)(?=\*\*[A-ZÁÉÍÓÚÜÑ]|\Z)',
        
        # Patrón 7: RECOMENDACIONES sin ** pero con guiones
        rf'(?i)\nRECOMENDACIONES?\n[=\-]+\s*(.*?)(?=\n[A-ZÁÉÍÓÚÜÑ]|\Z)',
        
        # Patrón 8: RECOMENDACIONES (búsqueda directa hasta REFERENCIAS)
        rf'(?i)\*\*RECOMENDACIONES?\*\*:?\s*(.*?)(?=\*\*REFERENCIAS|REFERENCIAS|\Z)',
    ]
    
    for i, patron in enumerate(patrones):
        try:
            match = re.search(patron, contenido, re.DOTALL | re.IGNORECASE)
            if match:
                texto = match.group(1).strip()
                if len(texto) > 30:  # Umbral más bajo para recomendaciones
                    logger.info(f"✅ Sección '{nombre}' extraída con patrón {i+1} ({len(texto)} chars)")
                    return formatear_texto(texto)
        except Exception as e:
            logger.warning(f"Error con patrón {i+1} para '{nombre}': {e}")
            continue
    
    logger.warning(f"⚠️ No se pudo extraer '{nombre}'")
    return ""

# ============================================================
# GENERAR INFORME COMPLETO
# ============================================================
def generar_informe_completo(tema, info_extra, tipo_informe, norma):
    """Genera el informe y extrae todas las secciones"""
    
    prompt = construir_prompt(tema, info_extra, tipo_informe, norma)
    contenido = llamar_deepseek(prompt)
    
    if not contenido:
        return None
    
    # Extraer cada sección
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
    
    # Guardar el contenido original para depuración
    logger.info(f"📊 Resumen de extracción:")
    for key, value in secciones.items():
        status = "✅" if value and len(value) > 30 else "❌"
        logger.info(f"   {status} {key}: {len(value)} caracteres")
    
    return secciones

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
        if contenido and len(contenido) > 30:
            story.append(Paragraph(contenido, styles['TextoJustificado']))
        else:
            story.append(Paragraph("No se pudo generar esta sección. Por favor, intenta nuevamente.", styles['TextoJustificado']))
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
    """Genera el informe completo y devuelve el PDF"""
    try:
        data = request.json
        
        tema = data.get('tema', '').strip()
        info_extra = data.get('texto_usuario', '')
        tipo_informe = data.get('tipo_informe', 'academico')
        norma = data.get('norma', 'APA 7')
        
        autores = data.get('autores', [])
        nombre_principal = autores[0].get('nombre', 'Estudiante') if autores else 'Estudiante'
        
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
        secciones = generar_informe_completo(tema, info_extra, tipo_informe, norma)
        
        if not secciones:
            return jsonify({'success': False, 'error': 'No se pudo generar el informe. Verifica tu saldo de DeepSeek.'}), 500
        
        # Verificar si al menos algunas secciones se generaron
        secciones_llenas = sum(1 for v in secciones.values() if v and len(v) > 30)
        logger.info(f"📊 Secciones con contenido: {secciones_llenas}/8")
        
        if secciones_llenas < 3:
            logger.warning("⚠️ Pocas secciones generadas, puede haber problemas con el formato")
        
        datos_usuario = {
            'nombre': nombre_principal,
            'tema': tema,
            'asignatura': asignatura,
            'profesor': profesor,
            'institucion': institucion,
            'ciudad': ciudad,
            'fecha': fecha,
            'norma': norma
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

@app.route('/preview', methods=['POST'])
def preview():
    """Genera una vista previa del contenido sin crear el PDF"""
    try:
        data = request.json
        tema = data.get('tema', '')
        info_extra = data.get('texto_usuario', '')
        tipo_informe = data.get('tipo_informe', 'academico')
        norma = data.get('norma', 'APA 7')
        
        if not tema:
            return jsonify({'success': False, 'error': 'El tema es requerido'}), 400
        
        prompt = construir_prompt(tema, info_extra, tipo_informe, norma)
        contenido = llamar_deepseek(prompt)
        
        if contenido:
            return jsonify({'success': True, 'contenido': contenido[:3000] + '...'})
        else:
            return jsonify({'success': False, 'error': 'No se pudo generar el contenido'}), 500
            
    except Exception as e:
        logger.error(f"Error en preview: {e}")
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
