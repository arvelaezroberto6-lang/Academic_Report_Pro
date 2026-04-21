from flask import Flask, render_template, request, jsonify, send_file
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from docx import Document
from docx.shared import Inches, Pt
from io import BytesIO
import os
import uuid
from datetime import datetime
import requests
import logging
import re
import json

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
logger.info("🔧 Herramienta profesional de generación de informes académicos")
logger.info("📊 No es ChatGPT - Es un generador especializado en informes")
logger.info(f"🔑 API Key configurada: {'SÍ ✅' if DEEPSEEK_API_KEY else 'NO ❌'}")
logger.info("=" * 60)

# ============================================================
# CONSTRUCCIÓN DE PROMPT MEJORADO (con datos numéricos y tablas)
# ============================================================
def construir_prompt(tema, info_extra, tipo_informe, norma):
    """Construye el prompt para DeepSeek con énfasis en datos numéricos"""
    
    info_extra_texto = info_extra if info_extra else 'No hay información adicional'
    
    prompt = f"""Eres un asistente académico experto. Genera un informe de tipo {tipo_informe.upper()} sobre: "{tema}"

Información adicional del usuario: {info_extra_texto}

⚠️ IMPORTANTE: Debes seguir EXACTAMENTE este formato, con los títulos en **negritas** y en el mismo orden:

**INTRODUCCIÓN**
[Escribe aquí la introducción, 2-3 párrafos. INCLUYE DATOS NUMÉRICOS como porcentajes, fechas, cantidades]

**OBJETIVOS**
- Objetivo General: [escribe aquí]
- Objetivos Específicos:
  1. [escribe aquí]
  2. [escribe aquí]
  3. [escribe aquí]
  4. [escribe aquí]
  5. [escribe aquí]

**MARCO TEÓRICO**
[Escribe aquí el marco teórico, 3-4 párrafos. INCLUYE CITAS DE AUTORES con fechas]

**METODOLOGÍA**
[Escribe aquí la metodología. INCLUYE: tipo de investigación, población (ej: 250 participantes), técnicas usadas, fechas]

**DESARROLLO**
[Escribe aquí el desarrollo. OBLIGATORIO: INCLUYE UNA TABLA CON DATOS NUMÉRICOS. Ejemplo de formato de tabla:
| Variable | Valor 2023 | Valor 2024 | Cambio (%) |
|----------|------------|------------|-------------|
| Indicador 1 | 45% | 52% | +7% |
| Indicador 2 | 120 | 145 | +20.8% |
]

**CONCLUSIONES**
1. [conclusión 1 con dato numérico]
2. [conclusión 2 con dato numérico]
3. [conclusión 3 con dato numérico]
4. [conclusión 4 con dato numérico]
5. [conclusión 5 con dato numérico]

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

REQUISITOS OBLIGATORIOS:
- Escribe en español académico
- Usa **negritas** solo para los títulos
- INCLUYE DATOS NUMÉRICOS ESPECÍFICOS (porcentajes, fechas, cantidades)
- INCLUYE UNA TABLA en la sección de Desarrollo
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
            {"role": "system", "content": "Eres un asistente académico profesional especializado en la creación de informes estructurados. Generas contenido original, incluyendo DATOS NUMÉRICOS ESPECÍFICOS (porcentajes, fechas, cantidades) y TABLAS cuando corresponde."},
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
# EXTRACCIÓN DE SECCIONES
# ============================================================
def formatear_texto(texto):
    """Formatea el texto para ReportLab"""
    texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
    texto = texto.replace('\n', '<br/>')
    texto = re.sub(r'<br/>\s*<br/>', '<br/><br/>', texto)
    return texto.strip()

def extraer_seccion(contenido, nombre):
    """Extrae una sección del contenido"""
    
    if not contenido:
        return ""
    
    patrones = [
        rf'\*\*{nombre}\*\*:?\s*(.*?)(?=\*\*[A-ZÁÉÍÓÚÜÑ]|\Z)',
        rf'\*\*{nombre}\*\*(.*?)(?=\*\*[A-ZÁÉÍÓÚÜÑ]|\Z)',
        rf'\n{nombre}\n[=\-]+\s*(.*?)(?=\n[A-ZÁÉÍÓÚÜÑ]|\Z)',
        rf'\d+\.\s*{nombre}\s*(.*?)(?=\d+\.\s*[A-ZÁÉÍÓÚÜÑ]|\Z)',
        rf'###\s*{nombre}\s*(.*?)(?=###|\Z)',
    ]
    
    for patron in patrones:
        try:
            match = re.search(patron, contenido, re.DOTALL | re.IGNORECASE)
            if match:
                texto = match.group(1).strip()
                if len(texto) > 30:
                    logger.info(f"✅ Sección '{nombre}' extraída ({len(texto)} chars)")
                    return formatear_texto(texto)
        except Exception as e:
            continue
    
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
    
    logger.info(f"📊 Resumen: {sum(1 for v in secciones.values() if v)}/8 secciones extraídas")
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
            story.append(Paragraph("No se pudo generar esta sección.", styles['TextoJustificado']))
        story.append(PageBreak())
    
    doc.build(story)
    return filename, filepath

# ============================================================
# GENERAR WORD
# ============================================================
def generar_word(datos_usuario, secciones):
    """Genera un archivo Word con el contenido"""
    
    nombre = datos_usuario.get('nombre', 'Estudiante')
    tema = datos_usuario.get('tema', 'Tema de Investigación')
    asignatura = datos_usuario.get('asignatura', '')
    profesor = datos_usuario.get('profesor', '')
    institucion = datos_usuario.get('institucion', '')
    ciudad = datos_usuario.get('ciudad', '')
    fecha = datos_usuario.get('fecha', datetime.now().strftime('%d/%m/%Y'))
    norma = datos_usuario.get('norma', 'APA 7')
    
    doc = Document()
    
    # Título
    title = doc.add_heading('INFORME ACADÉMICO', 0)
    title.alignment = 1  # Centrado
    
    doc.add_heading(tema, level=1)
    
    # Datos del estudiante
    doc.add_paragraph(f"Presentado por: {nombre}")
    if asignatura:
        doc.add_paragraph(f"Asignatura: {asignatura}")
    if profesor:
        doc.add_paragraph(f"Docente: {profesor}")
    if institucion:
        doc.add_paragraph(f"Institución: {institucion}")
    if ciudad:
        doc.add_paragraph(f"Ciudad: {ciudad}")
    doc.add_paragraph(f"Fecha: {fecha}")
    doc.add_paragraph(f"Norma: {norma}")
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
        ("REFERENCIAS", 'referencias')
    ]
    
    for titulo, clave in secciones_orden:
        doc.add_heading(titulo, level=2)
        contenido = secciones.get(clave, '')
        # Limpiar etiquetas HTML
        contenido_limpio = re.sub(r'<br/?>', '\n', contenido)
        contenido_limpio = re.sub(r'<b>(.*?)</b>', r'\1', contenido_limpio)
        contenido_limpio = re.sub(r'<[^>]+>', '', contenido_limpio)
        
        if contenido_limpio and len(contenido_limpio) > 30:
            doc.add_paragraph(contenido_limpio)
        else:
            doc.add_paragraph("No se pudo generar esta sección.")
        doc.add_page_break()
    
    # Guardar en BytesIO
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ============================================================
# RUTAS DE LA API
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar', methods=['POST'])
def generar():
    """Genera el informe completo y devuelve las secciones para editar"""
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
        
        secciones = generar_informe_completo(tema, info_extra, tipo_informe, norma)
        
        if not secciones:
            return jsonify({'success': False, 'error': 'No se pudo generar el informe.'}), 500
        
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
        
        return jsonify({
            'success': True,
            'secciones': secciones,
            'datos_usuario': datos_usuario
        })
        
    except Exception as e:
        logger.error(f"Error en generar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/exportar-pdf', methods=['POST'])
def exportar_pdf():
    """Exporta el informe editado a PDF"""
    try:
        data = request.json
        secciones = data.get('secciones', {})
        datos_usuario = data.get('datos_usuario', {})
        
        filename, filepath = generar_pdf(datos_usuario, secciones)
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/exportar-word', methods=['POST'])
def exportar_word():
    """Exporta el informe editado a Word"""
    try:
        data = request.json
        secciones = data.get('secciones', {})
        datos_usuario = data.get('datos_usuario', {})
        
        buffer = generar_word(datos_usuario, secciones)
        filename = f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/preview', methods=['POST'])
def preview():
    """Genera una vista previa del contenido"""
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
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'api_configured': bool(DEEPSEEK_API_KEY),
        'message': 'Academic Report Pro - Generador profesional de informes académicos',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
