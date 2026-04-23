from flask import Flask, render_template, request, jsonify, send_file
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import os
import uuid
from datetime import datetime
import requests
import logging
import re
import html

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.makedirs('informes_generados', exist_ok=True)

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

logger.info("=" * 60)
logger.info("🚀 ACADEMIC REPORT PRO - VERSIÓN 3.1")
logger.info(f"🔑 API Key configurada: {'SÍ ✅' if DEEPSEEK_API_KEY else 'NO ❌'}")
logger.info("=" * 60)

# ============================================================
# INSTRUCCIONES ESPECÍFICAS POR NORMA DE CITACIÓN
# ============================================================
NORMAS_INSTRUCCIONES = {
    'APA 7': """
NORMA APA 7ª EDICIÓN — Aplica estas reglas ESTRICTAMENTE:
- En texto: (Apellido, año) o Apellido (año) señaló que...
- Hasta 2 autores: cita ambos siempre. 3 o más: primer apellido + et al.
- Referencias al final: Apellido, I. (año). Título en cursiva. Editorial. DOI.
- Artículos: Apellido, I. (año). Título del artículo. Revista, volumen(número), páginas. DOI.
""",
    'APA 6': """
NORMA APA 6ª EDICIÓN — Aplica estas reglas ESTRICTAMENTE:
- En texto: (Apellido, año, p. XX) para citas directas.
- 3-5 autores: primera vez todos; luego et al.
- Referencias: Apellido, I. (año). Título del libro. Ciudad: Editorial.
""",
    'ICONTEC': """
NORMA ICONTEC — Aplica estas reglas ESTRICTAMENTE:
- En texto: notas al pie numeradas o autor-año.
- Referencias en ORDEN DE APARICIÓN.
- Libro: APELLIDO, Nombre. Título. Edición. Ciudad: Editorial, año.
- APELLIDO en MAYÚSCULAS.
""",
    'IEEE': """
NORMA IEEE — Aplica estas reglas ESTRICTAMENTE:
- En texto: números entre corchetes [1] en orden de aparición.
- Referencias numeradas en orden de aparición.
- Artículos: [1] I. Apellido, "Título," Revista, vol. X, no. X, pp. XX-XX, año.
""",
    'Vancouver': """
NORMA VANCOUVER — Aplica estas reglas ESTRICTAMENTE:
- En texto: números superíndice en orden de aparición.
- Referencias numeradas consecutivamente.
- Artículos: Apellido AB. Título. Revista. año;volumen(número):páginas.
""",
    'Chicago': """
NORMA CHICAGO — Aplica estas reglas ESTRICTAMENTE:
- En texto: (Apellido año, página).
- Bibliografía en orden ALFABÉTICO.
- Libros: Apellido, Nombre. Año. Título. Ciudad: Editorial.
""",
    'MLA': """
NORMA MLA — Aplica estas reglas ESTRICTAMENTE:
- En texto: (Apellido página).
- Works Cited en orden ALFABÉTICO.
- Libros: Apellido, Nombre. Título. Editorial, año.
""",
    'Harvard': """
NORMA HARVARD — Aplica estas reglas ESTRICTAMENTE:
- En texto: (Apellido año) o (Apellido año, p. XX).
- Referencias alfabéticas.
- Libros: Apellido, I. (año) Título. Ciudad: Editorial.
"""
}

TIPOS_INSTRUCCIONES = {
    'academico': "Informe académico estándar con rigor teórico y análisis crítico.",
    'laboratorio': "Informe de laboratorio: hipótesis, materiales, procedimiento, resultados, discusión.",
    'ejecutivo': "Informe ejecutivo: KPIs, análisis estratégico, recomendaciones.",
    'tesis': "Tesis académica: argumentación profunda, revisión de literatura, metodología robusta.",
    'pasantia': "Informe de pasantía: descripción de actividades, competencias, aprendizajes.",
    'proyecto': "Informe de proyecto: cronograma, recursos, entregables, riesgos."
}

# ============================================================
# FUNCIÓN PARA LLAMAR A DEEPSEEK
# ============================================================
def llamar_deepseek(prompt, system_prompt=None, max_tokens=3000):
    if not DEEPSEEK_API_KEY:
        return None
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=120)
        if response.status_code == 200:
            contenido = response.json()['choices'][0]['message']['content']
            contenido = contenido.encode('utf-8', 'ignore').decode('utf-8')
            return contenido
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

# ============================================================
# LIMPIEZA DE TEXTO
# ============================================================
def limpiar_para_pdf(texto):
    if not texto:
        return ""
    texto = texto.replace('<br/>', '\n').replace('<br>', '\n')
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = html.unescape(texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()

def limpiar_para_word(texto):
    if not texto:
        return ""
    texto = texto.replace('<br/>', '\n').replace('<br>', '\n')
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = html.unescape(texto)
    return texto.strip()

# ============================================================
# PROMPTS POR SECCIÓN
# ============================================================
def build_prompt(seccion, tema, info, tipo, norma, nivel, refs_manuales=''):
    instruccion_norma = NORMAS_INSTRUCCIONES.get(norma, NORMAS_INSTRUCCIONES['APA 7'])
    instruccion_tipo = TIPOS_INSTRUCCIONES.get(tipo, TIPOS_INSTRUCCIONES['academico'])
    
    base = f"""Tipo: {instruccion_tipo}
Nivel: {nivel}
Norma: {norma}
{instruccion_norma}
"""
    if seccion == 'introduccion':
        return base + f"""Escribe la INTRODUCCIÓN para: "{tema}".
Información adicional: {info or 'Ninguna'}
Mínimo 4 párrafos. Incluye contexto, justificación, problema y estructura.
Incluye al menos 2 citas en formato {norma}.
NO incluyas el título."""
    
    elif seccion == 'objetivos':
        return base + f"""Escribe los OBJETIVOS para: "{tema}".
Formato:
OBJETIVO GENERAL:
[Un objetivo general]

OBJETIVOS ESPECÍFICOS:
1. [objetivo 1]
2. [objetivo 2]
3. [objetivo 3]
4. [objetivo 4]
5. [objetivo 5]"""
    
    elif seccion == 'marco_teorico':
        return base + f"""Escribe el MARCO TEÓRICO para: "{tema}".
Información: {info or 'Ninguna'}
Mínimo 5 párrafos. Incluye antecedentes, definiciones, teorías.
Incluye al menos 4 citas en formato {norma}."""
    
    elif seccion == 'metodologia':
        return base + f"""Escribe la METODOLOGÍA para informe tipo "{tipo}" sobre: "{tema}".
Mínimo 4 párrafos. Incluye tipo de investigación, población, técnicas, procedimiento."""
    
    elif seccion == 'desarrollo':
        return base + f"""Escribe el DESARROLLO para: "{tema}".
Información: {info or 'Ninguna'}
Mínimo 6 párrafos. Incluye resultados, análisis, discusión.
Incluye al menos 3 citas en formato {norma}."""
    
    elif seccion == 'conclusiones':
        return base + f"""Escribe las CONCLUSIONES para: "{tema}".
Formato:
1. [conclusión 1]
2. [conclusión 2]
3. [conclusión 3]
4. [conclusión 4]
5. [conclusión 5]"""
    
    elif seccion == 'recomendaciones':
        return base + f"""Escribe las RECOMENDACIONES para informe tipo "{tipo}" sobre: "{tema}".
Formato:
1. [recomendación 1]
2. [recomendación 2]
3. [recomendación 3]
4. [recomendación 4]
5. [recomendación 5]"""
    
    elif seccion == 'referencias':
        refs_extra = f"\nReferencias del autor:\n{refs_manuales}" if refs_manuales else ""
        return base + f"""Genera 8-10 referencias para: "{tema}".
Norma: {norma}
{refs_extra}
Formato estricto {norma}. Solo la lista, sin título."""
    return ""

# ============================================================
# GENERAR SECCIÓN
# ============================================================
def generar_seccion(seccion, tema, info_extra, tipo_informe, norma, nivel, refs_manuales=''):
    prompt = build_prompt(seccion, tema, info_extra, tipo_informe, norma, nivel, refs_manuales)
    if not prompt:
        return None
    system_prompt = f"Experto en redacción académica en español. Especialista en norma {norma}. Responde SOLO con el contenido solicitado, sin títulos ni comentarios."
    contenido = llamar_deepseek(prompt, system_prompt=system_prompt, max_tokens=3000)
    if contenido:
        contenido = contenido.strip()
        logger.info(f"Sección '{seccion}' generada: {len(contenido)} caracteres")
    return contenido

# ============================================================
# GENERAR INFORME COMPLETO
# ============================================================
def generar_informe_completo(tema, info_extra, tipo_informe, norma, nivel):
    secciones = {}
    claves = ['introduccion', 'objetivos', 'marco_teorico', 'metodologia',
              'desarrollo', 'conclusiones', 'recomendaciones', 'referencias']
    for clave in claves:
        resultado = generar_seccion(clave, tema, info_extra, tipo_informe, norma, nivel)
        secciones[clave] = resultado or ''
    return secciones

# ============================================================
# GENERAR PDF
# ============================================================
def generar_pdf(datos_usuario, secciones):
    nombre = datos_usuario.get('nombre', 'Estudiante')
    autores_extra = datos_usuario.get('autores_extra', [])
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
    styles.add(ParagraphStyle(name='TextoJustificado', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=11, fontName='Times-Roman', spaceAfter=10, leading=18, firstLineIndent=18))
    styles.add(ParagraphStyle(name='Titulo1', parent=styles['Heading1'], fontSize=15, fontName='Helvetica-Bold', textColor=colors.HexColor('#1a365d'), spaceBefore=20, spaceAfter=10))
    styles.add(ParagraphStyle(name='TituloPortada', parent=styles['Title'], fontSize=22, alignment=TA_CENTER, textColor=colors.HexColor('#1a365d'), fontName='Helvetica-Bold', spaceAfter=12))
    styles.add(ParagraphStyle(name='SubtituloPortada', parent=styles['Normal'], fontSize=14, alignment=TA_CENTER, textColor=colors.HexColor('#2d4a7a'), fontName='Helvetica-Bold', spaceAfter=8))
    styles.add(ParagraphStyle(name='TextoCentrado', parent=styles['Normal'], alignment=TA_CENTER, fontSize=11, fontName='Helvetica', spaceAfter=6))
    styles.add(ParagraphStyle(name='TextoLista', parent=styles['Normal'], alignment=TA_LEFT, fontSize=11, fontName='Times-Roman', spaceAfter=6, leftIndent=20, leading=16))

    doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=2.5*cm, leftMargin=2.5*cm, topMargin=2.5*cm, bottomMargin=2.5*cm)
    story = []

    # Portada
    story.append(Spacer(1, 2.0*inch))
    story.append(Paragraph("INFORME ACADÉMICO", styles['TituloPortada']))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a365d'), spaceAfter=12))
    story.append(Paragraph(tema.upper(), styles['SubtituloPortada']))
    story.append(Spacer(1, 1.2*inch))
    story.append(Paragraph(f"<b>Presentado por:</b> {nombre}", styles['TextoCentrado']))
    for autor in autores_extra:
        if autor.get('nombre'):
            linea = autor['nombre']
            if autor.get('cargo'):
                linea += f" — {autor['cargo']}"
            story.append(Paragraph(linea, styles['TextoCentrado']))
    if asignatura:
        story.append(Paragraph(f"<b>Asignatura:</b> {asignatura}", styles['TextoCentrado']))
    if profesor:
        story.append(Paragraph(f"<b>Docente:</b> {profesor}", styles['TextoCentrado']))
    if institucion:
        story.append(Paragraph(f"<b>Institución:</b> {institucion}", styles['TextoCentrado']))
    if ciudad:
        story.append(Paragraph(f"<b>Ciudad:</b> {ciudad}", styles['TextoCentrado']))
    story.append(Paragraph(f"<b>Fecha:</b> {fecha}", styles['TextoCentrado']))
    story.append(Paragraph(f"<b>Norma bibliográfica:</b> {norma}", styles['TextoCentrado']))
    story.append(PageBreak())

    # Índice
    story.append(Paragraph("ÍNDICE", styles['Titulo1']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=8))
    for idx in ["1. Introducción", "2. Objetivos", "3. Marco Teórico", "4. Metodología", "5. Desarrollo", "6. Conclusiones", "7. Recomendaciones", "8. Referencias"]:
        story.append(Paragraph(f"{'&nbsp;' * 4}{idx}", styles['TextoLista']))
    story.append(PageBreak())

    # Secciones
    secciones_orden = [
        ("1. INTRODUCCIÓN", 'introduccion'), ("2. OBJETIVOS", 'objetivos'),
        ("3. MARCO TEÓRICO", 'marco_teorico'), ("4. METODOLOGÍA", 'metodologia'),
        ("5. DESARROLLO", 'desarrollo'), ("6. CONCLUSIONES", 'conclusiones'),
        ("7. RECOMENDACIONES", 'recomendaciones'), ("8. REFERENCIAS", 'referencias')
    ]
    for titulo, clave in secciones_orden:
        story.append(Paragraph(titulo, styles['Titulo1']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0'), spaceAfter=8))
        contenido_raw = secciones.get(clave, '')
        contenido = limpiar_para_pdf(contenido_raw)
        if contenido and len(contenido) > 50:
            parrafos = re.split(r'\n{2,}', contenido)
            if len(parrafos) == 1:
                parrafos = contenido.split('\n')
            for parrafo in parrafos:
                parrafo = parrafo.strip()
                if parrafo:
                    if re.match(r'^(\d+\.|•|-|\*)\s', parrafo):
                        story.append(Paragraph(parrafo, styles['TextoLista']))
                    else:
                        story.append(Paragraph(parrafo, styles['TextoJustificado']))
        else:
            story.append(Paragraph("Esta sección no pudo generarse correctamente.", styles['TextoJustificado']))
        story.append(PageBreak())

    doc.build(story)
    return filename, filepath

# ============================================================
# GENERAR WORD
# ============================================================
def generar_word(datos_usuario, secciones):
    nombre = datos_usuario.get('nombre', 'Estudiante')
    autores_extra = datos_usuario.get('autores_extra', [])
    tema = datos_usuario.get('tema', 'Tema')
    asignatura = datos_usuario.get('asignatura', '')
    profesor = datos_usuario.get('profesor', '')
    institucion = datos_usuario.get('institucion', '')
    ciudad = datos_usuario.get('ciudad', '')
    fecha = datos_usuario.get('fecha', datetime.now().strftime('%d/%m/%Y'))
    norma = datos_usuario.get('norma', 'APA 7')

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.5)

    # Portada
    portada = doc.add_paragraph()
    portada.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = portada.add_run('\n\n\nINFORME ACADÉMICO')
    run.bold = True
    run.font.size = Pt(22)
    run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)
    doc.add_paragraph()
    p_tema = doc.add_paragraph()
    p_tema.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_tema.add_run(tema.upper())
    r.bold = True
    r.font.size = Pt(14)
    r.font.color.rgb = RGBColor(0x2d, 0x4a, 0x7a)
    doc.add_paragraph()
    doc.add_paragraph()

    def agregar_dato(label, valor):
        if valor:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r1 = p.add_run(f"{label}: ")
            r1.bold = True
            r1.font.size = Pt(11)
            p.add_run(valor).font.size = Pt(11)

    agregar_dato("Presentado por", nombre)
    for autor in autores_extra:
        if autor.get('nombre'):
            linea = autor['nombre']
            if autor.get('cargo'):
                linea += f" — {autor['cargo']}"
            agregar_dato("Autor", linea)
    agregar_dato("Asignatura", asignatura)
    agregar_dato("Docente", profesor)
    agregar_dato("Institución", institucion)
    agregar_dato("Ciudad", ciudad)
    agregar_dato("Fecha", fecha)
    agregar_dato("Norma bibliográfica", norma)
    doc.add_page_break()

    # Índice
    h_idx = doc.add_heading('ÍNDICE', level=1)
    h_idx.runs[0].font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)
    for item in ['1. Introducción', '2. Objetivos', '3. Marco Teórico', '4. Metodología', '5. Desarrollo', '6. Conclusiones', '7. Recomendaciones', '8. Referencias']:
        p = doc.add_paragraph()
        p.add_run(f"    {item}")
    doc.add_page_break()

    # Secciones
    secciones_orden = [
        ("1. INTRODUCCIÓN", 'introduccion'), ("2. OBJETIVOS", 'objetivos'),
        ("3. MARCO TEÓRICO", 'marco_teorico'), ("4. METODOLOGÍA", 'metodologia'),
        ("5. DESARROLLO", 'desarrollo'), ("6. CONCLUSIONES", 'conclusiones'),
        ("7. RECOMENDACIONES", 'recomendaciones'), ("8. REFERENCIAS", 'referencias')
    ]
    for titulo_sec, clave in secciones_orden:
        h = doc.add_heading(titulo_sec, level=1)
        if h.runs:
            h.runs[0].font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)
            h.runs[0].font.size = Pt(14)
        contenido_raw = secciones.get(clave, '')
        contenido = limpiar_para_word(contenido_raw)
        if contenido and len(contenido) > 50:
            parrafos = re.split(r'\n{2,}', contenido)
            if len(parrafos) == 1:
                parrafos = contenido.split('\n')
            for parrafo in parrafos:
                parrafo = parrafo.strip()
                if not parrafo:
                    continue
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                r = p.add_run(parrafo)
                r.font.size = Pt(11)
                r.font.name = 'Times New Roman'
                p.paragraph_format.first_line_indent = Cm(0.5)
                p.paragraph_format.space_after = Pt(8)
        else:
            p = doc.add_paragraph("Esta sección no pudo generarse correctamente.")
            p.runs[0].font.size = Pt(11)
        doc.add_page_break()

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# ============================================================
# RUTAS DEL SITIO WEB
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar')
def generar_page():
    return render_template('generar.html')

@app.route('/mis-informes')
def mis_informes():
    return render_template('mis-informes.html')

@app.route('/perfil')
def perfil():
    return render_template('perfil.html')


# ============================================================
# RUTAS DE LA API
# ============================================================

@app.route('/generar-seccion', methods=['POST'])
def generar_seccion_endpoint():
    try:
        data = request.json
        seccion = data.get('seccion', '')
        tema = data.get('tema', '').strip()
        nivel = data.get('nivel', 'universitario')
        tipo = data.get('tipo_informe', 'academico')
        norma = data.get('norma', 'APA 7')
        info = data.get('texto_usuario', '')
        refs_manuales = data.get('refs_manuales', '')
        if not seccion or not tema:
            return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400
        contenido = generar_seccion(seccion, tema, info, tipo, norma, nivel, refs_manuales)
        if contenido:
            return jsonify({'success': True, 'seccion': seccion, 'contenido': contenido})
        return jsonify({'success': False, 'error': f'No se pudo generar: {seccion}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/exportar-pdf', methods=['POST'])
def exportar_pdf():
    try:
        data = request.json
        filename, filepath = generar_pdf(data['datos_usuario'], data['secciones'])
        return send_file(filepath, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/exportar-word', methods=['POST'])
def exportar_word():
    try:
        data = request.json
        buffer = generar_word(data['datos_usuario'], data['secciones'])
        return send_file(buffer, as_attachment=True, download_name=f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx", mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'api_configured': bool(DEEPSEEK_API_KEY), 'version': '3.1'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
