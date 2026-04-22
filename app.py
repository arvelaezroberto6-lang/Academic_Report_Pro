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
import json
import re
from datetime import datetime
import requests
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.makedirs('informes_generados', exist_ok=True)

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

logger.info("=" * 60)
logger.info("ACADEMIC REPORT PRO - VERSIÓN JSON ROBUSTA")
logger.info(f"API Key configurada: {'SI' if DEEPSEEK_API_KEY else 'NO'}")
logger.info("=" * 60)

# ============================================================
# FUNCIÓN PARA LLAMAR A DEEPSEEK
# ============================================================
def llamar_deepseek(prompt, system_prompt=None, max_tokens=8000):
    if not system_prompt:
        system_prompt = "Eres un asistente académico profesional. Generas informes estructurados en español."

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=180)
        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado['choices'][0]['message']['content']
            contenido = contenido.encode('utf-8', 'ignore').decode('utf-8')
            logger.info(f"Contenido recibido: {len(contenido)} caracteres")
            return contenido
        else:
            logger.error(f"Error HTTP {response.status_code}: {response.text[:300]}")
            return None
    except Exception as e:
        logger.error(f"Error llamando DeepSeek: {e}")
        return None

# ============================================================
# GENERAR INFORME - RESPUESTA EN JSON DIRECTO
# ============================================================
def generar_informe_completo(tema, info_extra, tipo_informe, norma, nivel):
    """
    Le pedimos a DeepSeek que responda ÚNICAMENTE en JSON.
    Esto elimina por completo el problema de parsear texto con regex.
    """

    prompt = f"""Genera un informe académico profesional de tipo "{tipo_informe}" sobre el siguiente tema:
TEMA: "{tema}"
NIVEL EDUCATIVO: {nivel}
INFORMACIÓN ADICIONAL: {info_extra if info_extra else 'Ninguna'}
NORMA DE CITACIÓN: {norma}

INSTRUCCIÓN CRÍTICA: Responde ÚNICAMENTE con un objeto JSON válido, sin ningún texto antes ni después, sin bloques de código markdown, sin backticks. Solo el JSON puro.

El JSON debe tener exactamente esta estructura:
{{
  "introduccion": "Aquí escribe 4 párrafos completos sobre el contexto, problema y justificación del tema. Cada párrafo separado por doble salto de línea.",
  "objetivos": "Objetivo General: [escribe aquí].\\n\\nObjetivos Específicos:\\n1. [objetivo 1]\\n2. [objetivo 2]\\n3. [objetivo 3]\\n4. [objetivo 4]\\n5. [objetivo 5]",
  "marco_teorico": "Aquí escribe 4 párrafos completos con conceptos clave, antecedentes teóricos y definiciones relevantes.",
  "metodologia": "Aquí escribe 4 párrafos completos describiendo el tipo de investigación, población, técnicas de recolección de datos y procedimiento.",
  "desarrollo": "Aquí escribe 4 párrafos completos con resultados, análisis detallado y hallazgos principales.",
  "conclusiones": "1. [conclusión detallada 1]\\n2. [conclusión detallada 2]\\n3. [conclusión detallada 3]\\n4. [conclusión detallada 4]\\n5. [conclusión detallada 5]",
  "recomendaciones": "1. [recomendación detallada 1]\\n2. [recomendación detallada 2]\\n3. [recomendación detallada 3]\\n4. [recomendación detallada 4]",
  "referencias": "- [Referencia 1 en formato {norma}]\\n- [Referencia 2 en formato {norma}]\\n- [Referencia 3 en formato {norma}]\\n- [Referencia 4 en formato {norma}]\\n- [Referencia 5 en formato {norma}]\\n- [Referencia 6 en formato {norma}]"
}}

Cada sección debe tener contenido sustancial y académico. No uses caracteres especiales problemáticos."""

    system_prompt = (
        "Eres un asistente académico profesional experto en redacción de informes. "
        "DEBES responder ÚNICAMENTE con JSON válido, sin texto adicional, sin markdown, sin backticks. "
        "Solo el objeto JSON puro y válido."
    )

    contenido = llamar_deepseek(prompt, system_prompt=system_prompt, max_tokens=8000)

    if not contenido:
        logger.error("DeepSeek no devolvió contenido")
        return None

    # Limpiar posibles backticks o etiquetas markdown que DeepSeek añada
    contenido_limpio = contenido.strip()
    contenido_limpio = re.sub(r'^```(?:json)?\s*', '', contenido_limpio)
    contenido_limpio = re.sub(r'\s*```$', '', contenido_limpio)
    contenido_limpio = contenido_limpio.strip()

    # Intentar parsear el JSON
    try:
        secciones = json.loads(contenido_limpio)
        logger.info("JSON parseado correctamente")
    except json.JSONDecodeError as e:
        logger.warning(f"Error parseando JSON: {e}. Intentando extracción parcial...")
        # Plan B: buscar el JSON dentro del texto
        match = re.search(r'\{[\s\S]*\}', contenido_limpio)
        if match:
            try:
                secciones = json.loads(match.group(0))
                logger.info("JSON extraído con regex y parseado correctamente")
            except Exception as e2:
                logger.error(f"Plan B también falló: {e2}")
                logger.error(f"Contenido recibido (primeros 500 chars): {contenido_limpio[:500]}")
                return None
        else:
            logger.error("No se encontró JSON en la respuesta")
            return None

    # Validar que tenga las claves esperadas
    claves_esperadas = ['introduccion', 'objetivos', 'marco_teorico', 'metodologia',
                        'desarrollo', 'conclusiones', 'recomendaciones', 'referencias']

    for clave in claves_esperadas:
        if clave not in secciones:
            secciones[clave] = ""
            logger.warning(f"Clave faltante en JSON: {clave}")

    # Log de estado de cada sección
    for clave in claves_esperadas:
        valor = secciones.get(clave, "")
        status = "OK" if valor and len(valor) > 50 else "VACIO"
        logger.info(f"[{status}] {clave}: {len(valor) if valor else 0} caracteres")

    # Convertir saltos de línea a <br/> para PDF/HTML
    for clave in claves_esperadas:
        if secciones.get(clave):
            secciones[clave] = secciones[clave].replace('\n', '<br/>')

    return secciones

# ============================================================
# GENERAR PDF
# ============================================================
def generar_pdf(datos_usuario, secciones):
    nombre = datos_usuario.get('nombre', 'Estudiante')
    tema = datos_usuario.get('tema', 'Tema')
    asignatura = datos_usuario.get('asignatura', '')
    profesor = datos_usuario.get('profesor', '')
    institucion = datos_usuario.get('institucion', '')
    ciudad = datos_usuario.get('ciudad', '')
    fecha = datos_usuario.get('fecha', datetime.now().strftime('%d/%m/%Y'))
    norma = datos_usuario.get('norma', 'APA 7')

    filename = f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.pdf"
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

    doc = SimpleDocTemplate(
        filepath,
        rightMargin=72, leftMargin=72,
        topMargin=72, bottomMargin=72
    )
    story = []

    # Portada
    story.append(Spacer(1, 2.0 * inch))
    story.append(Paragraph("INFORME ACADÉMICO", styles['TituloPortada']))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(tema.upper(), styles['TextoCentrado']))
    story.append(Spacer(1, 1.5 * inch))
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

    # Índice
    story.append(Paragraph("ÍNDICE", styles['Titulo1']))
    story.append(Spacer(1, 0.2 * inch))
    for idx in [
        "1. INTRODUCCIÓN", "2. OBJETIVOS", "3. MARCO TEÓRICO",
        "4. METODOLOGÍA", "5. DESARROLLO", "6. CONCLUSIONES",
        "7. RECOMENDACIONES", "8. REFERENCIAS"
    ]:
        story.append(Paragraph(f"• {idx}", styles['TextoJustificado']))
        story.append(Spacer(1, 0.1 * inch))
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
        story.append(Spacer(1, 0.2 * inch))
        contenido = secciones.get(clave, '')
        if contenido and len(contenido) > 20:
            # Limpiar etiquetas HTML problemáticas para ReportLab
            contenido_limpio = contenido.replace('<br/>', '<br/>').replace('&', '&amp;')
            try:
                story.append(Paragraph(contenido_limpio, styles['TextoJustificado']))
            except Exception as e:
                logger.warning(f"Error renderizando sección {clave}: {e}")
                contenido_texto = re.sub(r'<[^>]+>', ' ', contenido)
                story.append(Paragraph(contenido_texto, styles['TextoJustificado']))
        else:
            story.append(Paragraph("Sección no disponible.", styles['TextoJustificado']))
        story.append(PageBreak())

    doc.build(story)
    return filename, filepath

# ============================================================
# GENERAR WORD
# ============================================================
def generar_word(datos_usuario, secciones):
    nombre = datos_usuario.get('nombre', 'Estudiante')
    tema = datos_usuario.get('tema', 'Tema')
    asignatura = datos_usuario.get('asignatura', '')
    profesor = datos_usuario.get('profesor', '')
    institucion = datos_usuario.get('institucion', '')
    ciudad = datos_usuario.get('ciudad', '')
    fecha = datos_usuario.get('fecha', datetime.now().strftime('%d/%m/%Y'))
    norma = datos_usuario.get('norma', 'APA 7')

    doc = Document()
    doc.add_heading('INFORME ACADÉMICO', 0)
    doc.add_heading(tema, level=1)
    doc.add_paragraph(f"Presentado por: {nombre}")
    if asignatura: doc.add_paragraph(f"Asignatura: {asignatura}")
    if profesor: doc.add_paragraph(f"Docente: {profesor}")
    if institucion: doc.add_paragraph(f"Institución: {institucion}")
    if ciudad: doc.add_paragraph(f"Ciudad: {ciudad}")
    doc.add_paragraph(f"Fecha: {fecha}")
    doc.add_paragraph(f"Norma: {norma}")
    doc.add_page_break()

    doc.add_heading('ÍNDICE', level=2)
    for titulo in ['INTRODUCCIÓN', 'OBJETIVOS', 'MARCO TEÓRICO', 'METODOLOGÍA',
                   'DESARROLLO', 'CONCLUSIONES', 'RECOMENDACIONES', 'REFERENCIAS']:
        doc.add_paragraph(f"• {titulo}")
    doc.add_page_break()

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
        if contenido:
            # Limpiar etiquetas HTML para el Word
            contenido_limpio = contenido.replace('<br/>', '\n').replace('<b>', '').replace('</b>', '')
            contenido_limpio = re.sub(r'<[^>]+>', '', contenido_limpio)
            doc.add_paragraph(contenido_limpio)
        else:
            doc.add_paragraph("Sección no disponible.")
        doc.add_page_break()

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
    try:
        data = request.json
        tema = data.get('tema', '').strip()
        nivel = data.get('nivel', 'universitario')
        tipo_informe = data.get('tipo_informe', 'academico')
        norma = data.get('norma', 'APA 7')
        nombre = data.get('nombre', 'Estudiante')
        asignatura = data.get('asignatura', '')
        profesor = data.get('profesor', '')
        institucion = data.get('institucion', '')
        ciudad = data.get('ciudad', '')
        texto_usuario = data.get('texto_usuario', '')

        autores = data.get('autores', [])
        if autores:
            nombre_principal = autores[0].get('nombre', nombre)
        else:
            nombre_principal = nombre

        if not tema:
            return jsonify({'success': False, 'error': 'El tema es requerido'}), 400

        logger.info(f"Generando informe - Tema: {tema[:50]}...")

        secciones = generar_informe_completo(tema, texto_usuario, tipo_informe, norma, nivel)

        if not secciones:
            return jsonify({'success': False, 'error': 'No se pudo generar el informe. Verifica la API key de DeepSeek.'}), 500

        datos_usuario = {
            'nombre': nombre_principal,
            'tema': tema,
            'asignatura': asignatura,
            'profesor': profesor,
            'institucion': institucion,
            'ciudad': ciudad,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'norma': norma
        }

        return jsonify({'success': True, 'secciones': secciones, 'datos_usuario': datos_usuario})

    except Exception as e:
        logger.error(f"Error en /generar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/exportar-pdf', methods=['POST'])
def exportar_pdf():
    try:
        data = request.json
        filename, filepath = generar_pdf(data['datos_usuario'], data['secciones'])
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"Error exportando PDF: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/exportar-word', methods=['POST'])
def exportar_word():
    try:
        data = request.json
        buffer = generar_word(data['datos_usuario'], data['secciones'])
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        logger.error(f"Error exportando Word: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/preview', methods=['POST'])
def preview():
    try:
        data = request.json
        tema = data.get('tema', '')
        prompt = f"Genera un breve resumen académico sobre: {tema} en 300 palabras."
        contenido = llamar_deepseek(prompt)
        if contenido:
            return jsonify({'success': True, 'contenido': contenido[:1000]})
        return jsonify({'success': False, 'error': 'No se pudo generar'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'api_configured': bool(DEEPSEEK_API_KEY)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
