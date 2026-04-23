from flask import Flask, render_template, request, jsonify, send_file
from reportlab.lib.pagesizes import A4
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
import requests as http_requests
import logging
import re
import html

# ── Importar módulo de referencias reales ──────────────────────
from referencias_reales import buscar_referencias_reales, formatear_referencias

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.makedirs('informes_generados', exist_ok=True)

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL     = "https://api.deepseek.com/v1/chat/completions"

logger.info("=" * 60)
logger.info("🚀 ACADEMIC REPORT PRO - VERSIÓN 3.2")
logger.info(f"🔑 API Key: {'SÍ ✅' if DEEPSEEK_API_KEY else 'NO ❌'}")
logger.info("=" * 60)

# ============================================================
# NORMAS Y TIPOS
# ============================================================
NORMAS_INSTRUCCIONES = {
    'APA 7': """NORMA APA 7 — En texto: (Apellido, año). 3+ autores: primer apellido et al.
Referencias: Apellido, I. (año). Título. Revista, vol(num), págs. https://doi.org/...""",
    'APA 6': """NORMA APA 6 — En texto: (Apellido, año, p. XX). 3-5 autores: primera vez todos; luego et al.
Referencias: Apellido, I. (año). Título del libro en cursiva. Ciudad: Editorial.""",
    'ICONTEC': """NORMA ICONTEC (NTC 5613) — Notas al pie numeradas. Referencias en ORDEN DE APARICIÓN.
Formato: APELLIDO, Nombre. Título en cursiva. Ed. Ciudad: Editorial, año.""",
    'IEEE': """NORMA IEEE — En texto: [1], [2]. Referencias numeradas en orden de aparición.
Artículos: [1] I. Apellido, "Título," Revista, vol. X, no. X, pp. XX, año.""",
    'Vancouver': """NORMA VANCOUVER — Números superíndice en orden de aparición.
Artículos: Apellido AB. Título. Revista. año;vol(num):págs.""",
    'Chicago': """NORMA CHICAGO 17 — En texto: (Apellido año, página). Bibliografía alfabética.
Libros: Apellido, Nombre. Año. Título. Ciudad: Editorial.""",
    'MLA': """NORMA MLA 9 — En texto: (Apellido página). Works Cited alfabético.
Artículos: Apellido, Nombre. "Título." Revista, vol. X, no. X, año, pp. XX.""",
    'Harvard': """NORMA HARVARD — En texto: (Apellido año). Referencias alfabéticas.
Artículos: Apellido, I. (año) 'Título', Revista, vol. X, no. X, pp. XX.""",
}

TIPOS_INSTRUCCIONES = {
    'academico':  "Informe académico estándar con rigor teórico, citas y análisis crítico.",
    'laboratorio':"Informe de laboratorio: hipótesis, materiales, procedimiento, resultados con datos/tablas, análisis de error.",
    'ejecutivo':  "Informe ejecutivo: lenguaje conciso, KPIs, análisis costo-beneficio, recomendaciones accionables.",
    'tesis':      "Tesis académica: argumentación profunda, revisión exhaustiva de literatura, marco metodológico robusto.",
    'pasantia':   "Informe de pasantía: descripción de la empresa, actividades, competencias, aprendizajes.",
    'proyecto':   "Informe de proyecto: cronograma, recursos, entregables, gestión de riesgos, estado de avance.",
}

# ============================================================
# DEEPSEEK
# ============================================================
def llamar_deepseek(prompt, system_prompt=None, max_tokens=3000):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    data = {
        "model":       "deepseek-chat",
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": 0.7
    }
    try:
        response = http_requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=120)
        if response.status_code == 200:
            contenido = response.json()['choices'][0]['message']['content']
            return contenido.encode('utf-8', 'ignore').decode('utf-8')
        else:
            logger.error(f"DeepSeek HTTP {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"Error DeepSeek: {e}")
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
    instruccion_tipo  = TIPOS_INSTRUCCIONES.get(tipo, TIPOS_INSTRUCCIONES['academico'])

    base = f"""Tipo de informe: {instruccion_tipo}
Nivel educativo: {nivel}.
Norma bibliográfica activa: {norma}.
{instruccion_norma}
"""
    if seccion == 'introduccion':
        return base + f"""Escribe ÚNICAMENTE la INTRODUCCIÓN del informe sobre: "{tema}".
Info adicional: {info or 'Ninguna'}.
- Mínimo 4 párrafos: contexto, justificación, planteamiento del problema, estructura del informe.
- Redacción formal y académica. Al menos 2 citas en formato {norma}.
- NO incluyas el título, solo el contenido puro."""

    elif seccion == 'objetivos':
        return base + f"""Escribe ÚNICAMENTE los OBJETIVOS del informe sobre: "{tema}".
OBJETIVO GENERAL:
[Un objetivo general claro y medible en infinitivo]
OBJETIVOS ESPECÍFICOS:
1. [Objetivo 1 — verbo en infinitivo + acción + resultado]
2. [Objetivo 2]
3. [Objetivo 3]
4. [Objetivo 4]
5. [Objetivo 5]"""

    elif seccion == 'marco_teorico':
        return base + f"""Escribe ÚNICAMENTE el MARCO TEÓRICO del informe sobre: "{tema}".
Info adicional: {info or 'Ninguna'}.
- Mínimo 5 párrafos: antecedentes, definiciones clave, teorías, estado del arte.
- Al menos 4 citas en formato {norma}. Vocabulario especializado."""

    elif seccion == 'metodologia':
        return base + f"""Escribe ÚNICAMENTE la METODOLOGÍA del informe de tipo "{tipo}" sobre: "{tema}".
- Mínimo 4 párrafos: enfoque, tipo de investigación, técnicas, procedimiento, ética.
- Si es laboratorio: materiales y procedimiento paso a paso.
- Justifica cada decisión metodológica."""

    elif seccion == 'desarrollo':
        return base + f"""Escribe ÚNICAMENTE el DESARROLLO del informe de tipo "{tipo}" sobre: "{tema}".
Info adicional: {info or 'Ninguna'}.
- Mínimo 6 párrafos. Es la sección más extensa.
- Resultados, análisis, discusión crítica, comparación con teoría.
- Al menos 3 citas en formato {norma}."""

    elif seccion == 'conclusiones':
        return base + f"""Escribe ÚNICAMENTE las CONCLUSIONES del informe sobre: "{tema}".
1. [Conclusión 1: responde al objetivo general — mínimo 3 oraciones]
2. [Conclusión 2: hallazgo más importante]
3. [Conclusión 3: implicaciones prácticas]
4. [Conclusión 4: limitaciones]
5. [Conclusión 5: perspectivas futuras]"""

    elif seccion == 'recomendaciones':
        return base + f"""Escribe ÚNICAMENTE las RECOMENDACIONES del informe de tipo "{tipo}" sobre: "{tema}".
1. [Recomendación 1: dirigida a quién + acción + justificación — 3 oraciones]
2. [Recomendación 2]
3. [Recomendación 3]
4. [Recomendación 4]
5. [Recomendación 5: para futuras investigaciones]"""

    elif seccion == 'referencias':
        refs_extra = f"\nIncluye o adapta estas referencias del autor:\n{refs_manuales}" if refs_manuales else ""
        return base + f"""Genera ÚNICAMENTE la lista de REFERENCIAS BIBLIOGRÁFICAS sobre: "{tema}".
{refs_extra}
- Entre 8 y 10 referencias académicas reales (libros, artículos, reportes).
- Aplica formato {norma} con precisión. Años 2015-2024. Sin título de sección."""

    return ""

# ============================================================
# GENERAR SECCIÓN
# ============================================================
def generar_seccion(seccion, tema, info_extra, tipo_informe, norma, nivel, refs_manuales=''):
    prompt = build_prompt(seccion, tema, info_extra, tipo_informe, norma, nivel, refs_manuales)
    if not prompt:
        return None

    system_prompt = (
        f"Eres un experto en redacción académica universitaria en español con especialización en norma {norma}. "
        "Escribes contenido sustancial, formal y bien estructurado. "
        "Respondes SOLO con el contenido solicitado, sin títulos, sin preámbulos, sin '**', sin markdown."
    )

    contenido = llamar_deepseek(prompt, system_prompt=system_prompt, max_tokens=3000)
    if contenido:
        contenido = contenido.strip()
        logger.info(f"Sección '{seccion}' generada: {len(contenido)} chars")
    return contenido

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
    nombre      = datos_usuario.get('nombre', 'Estudiante')
    autores_extra = datos_usuario.get('autores_extra', [])
    tema        = datos_usuario.get('tema', 'Tema')
    asignatura  = datos_usuario.get('asignatura', '')
    profesor    = datos_usuario.get('profesor', '')
    institucion = datos_usuario.get('institucion', '')
    ciudad      = datos_usuario.get('ciudad', '')
    fecha       = datos_usuario.get('fecha', datetime.now().strftime('%d/%m/%Y'))
    norma       = datos_usuario.get('norma', 'APA 7')

    filename = f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join('informes_generados', filename)

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='TextoJustificado',
        parent=styles['Normal'],
        alignment=TA_JUSTIFY,
        fontSize=11,
        fontName='Times-Roman',
        spaceAfter=10,
        leading=18,
        firstLineIndent=18
    ))
    styles.add(ParagraphStyle(
        name='Titulo1',
        parent=styles['Heading1'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a365d'),
        spaceBefore=20,
        spaceAfter=10,
        alignment=TA_LEFT
    ))
    styles.add(ParagraphStyle(
        name='TituloPortada',
        parent=styles['Normal'],
        fontSize=22,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a365d'),
        alignment=TA_CENTER,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='SubtituloPortada',
        parent=styles['Normal'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2d4a7a'),
        alignment=TA_CENTER,
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name='TextoCentrado',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Times-Roman',
        alignment=TA_CENTER,
        spaceAfter=5
    ))
    styles.add(ParagraphStyle(
        name='TextoLista',
        parent=styles['Normal'],
        alignment=TA_LEFT,
        fontSize=11,
        fontName='Times-Roman',
        spaceAfter=6,
        leftIndent=20,
        leading=16
    ))

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2.5*cm,
        leftMargin=2.5*cm,
        topMargin=2.5*cm,
        bottomMargin=2.5*cm
    )
    story = []

    # PORTADA
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

    # ÍNDICE
    story.append(Paragraph("ÍNDICE", styles['Titulo1']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=8))
    for idx in ["1. Introducción", "2. Objetivos", "3. Marco Teórico",
                "4. Metodología", "5. Desarrollo", "6. Conclusiones",
                "7. Recomendaciones", "8. Referencias Bibliográficas"]:
        story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{idx}", styles['TextoLista']))
    story.append(PageBreak())

    # SECCIONES
    secciones_orden = [
        ("1. INTRODUCCIÓN",               'introduccion'),
        ("2. OBJETIVOS",                  'objetivos'),
        ("3. MARCO TEÓRICO",              'marco_teorico'),
        ("4. METODOLOGÍA",                'metodologia'),
        ("5. DESARROLLO",                 'desarrollo'),
        ("6. CONCLUSIONES",               'conclusiones'),
        ("7. RECOMENDACIONES",            'recomendaciones'),
        ("8. REFERENCIAS BIBLIOGRÁFICAS", 'referencias'),
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
            for p in parrafos:
                p = p.strip()
                if p:
                    if re.match(r'^(\d+\.|•|-|\*)\s', p):
                        story.append(Paragraph(p, styles['TextoLista']))
                    else:
                        story.append(Paragraph(p, styles['TextoJustificado']))
        else:
            story.append(Paragraph("Esta sección no pudo generarse.", styles['TextoJustificado']))

        story.append(PageBreak())

    doc.build(story)
    return filename, filepath

# ============================================================
# GENERAR WORD
# ============================================================
def generar_word(datos_usuario, secciones):
    nombre      = datos_usuario.get('nombre', 'Estudiante')
    autores_extra = datos_usuario.get('autores_extra', [])
    tema        = datos_usuario.get('tema', 'Tema')
    asignatura  = datos_usuario.get('asignatura', '')
    profesor    = datos_usuario.get('profesor', '')
    institucion = datos_usuario.get('institucion', '')
    ciudad      = datos_usuario.get('ciudad', '')
    fecha       = datos_usuario.get('fecha', datetime.now().strftime('%d/%m/%Y'))
    norma       = datos_usuario.get('norma', 'APA 7')

    doc = Document()
    section = doc.sections[0]
    section.top_margin    = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin   = Cm(3.0)
    section.right_margin  = Cm(2.5)

    # PORTADA
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

    # ÍNDICE
    h_idx = doc.add_heading('ÍNDICE', level=1)
    h_idx.runs[0].font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)
    for item in ['1. Introducción', '2. Objetivos', '3. Marco Teórico', '4. Metodología',
                 '5. Desarrollo', '6. Conclusiones', '7. Recomendaciones', '8. Referencias Bibliográficas']:
        p = doc.add_paragraph()
        r = p.add_run(f"    {item}")
        r.font.size = Pt(11)

    doc.add_page_break()

    # SECCIONES
    secciones_orden = [
        ("1. INTRODUCCIÓN",               'introduccion'),
        ("2. OBJETIVOS",                  'objetivos'),
        ("3. MARCO TEÓRICO",              'marco_teorico'),
        ("4. METODOLOGÍA",                'metodologia'),
        ("5. DESARROLLO",                 'desarrollo'),
        ("6. CONCLUSIONES",               'conclusiones'),
        ("7. RECOMENDACIONES",            'recomendaciones'),
        ("8. REFERENCIAS BIBLIOGRÁFICAS", 'referencias'),
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
# RUTAS — PÁGINAS (GET)
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar', methods=['GET'])
def generar_page():
    return render_template('generar.html')

@app.route('/mis-informes')
def mis_informes():
    return render_template('mis-informes.html')

@app.route('/perfil')
def perfil():
    return render_template('perfil.html')

# ============================================================
# RUTAS — API (POST)
# ============================================================
@app.route('/api/generar', methods=['POST'])
def api_generar():
    try:
        data            = request.json
        tema            = data.get('tema', '').strip()
        nivel           = data.get('nivel', 'universitario')
        tipo_informe    = data.get('tipo_informe', 'academico')
        norma           = data.get('norma', 'APA 7')
        nombre          = data.get('nombre', 'Estudiante')
        asignatura      = data.get('asignatura', '')
        profesor        = data.get('profesor', '')
        institucion     = data.get('institucion', '')
        ciudad          = data.get('ciudad', '')
        texto_usuario   = data.get('texto_usuario', '')
        autores         = data.get('autores', [])
        nombre_principal = autores[0].get('nombre', nombre) if autores else nombre

        if not tema:
            return jsonify({'success': False, 'error': 'El tema es requerido'}), 400

        logger.info(f"📨 Generando informe — Tema: {tema[:50]}...")
        secciones = generar_informe_completo(tema, texto_usuario, tipo_informe, norma, nivel)

        if not secciones:
            return jsonify({'success': False, 'error': 'No se pudo generar el informe'}), 500

        datos_usuario = {
            'nombre':      nombre_principal,
            'autores_extra': autores[1:] if len(autores) > 1 else [],
            'tema':        tema,
            'asignatura':  asignatura,
            'profesor':    profesor,
            'institucion': institucion,
            'ciudad':      ciudad,
            'fecha':       datetime.now().strftime('%d/%m/%Y'),
            'norma':       norma
        }

        return jsonify({'success': True, 'secciones': secciones, 'datos_usuario': datos_usuario})

    except Exception as e:
        logger.error(f"Error en /api/generar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/generar-seccion', methods=['POST'])
def api_generar_seccion():
    try:
        data      = request.json
        seccion   = data.get('seccion', '')
        tema      = data.get('tema', '').strip()
        nivel     = data.get('nivel', 'universitario')
        tipo      = data.get('tipo_informe', 'academico')
        norma     = data.get('norma', 'APA 7')
        info      = data.get('texto_usuario', '')
        refs_man  = data.get('refs_manuales', '')

        if not seccion or not tema:
            return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400

        contenido = generar_seccion(seccion, tema, info, tipo, norma, nivel, refs_man)

        if contenido:
            return jsonify({'success': True, 'seccion': seccion, 'contenido': contenido})
        return jsonify({'success': False, 'error': f'No se pudo generar: {seccion}'}), 500

    except Exception as e:
        logger.error(f"Error en /api/generar-seccion: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/referencias-reales', methods=['POST'])
def api_referencias_reales():
    """
    Obtiene referencias REALES de CrossRef y OpenAlex,
    las formatea según la norma y las devuelve al frontend.
    """
    try:
        data         = request.json
        tema         = data.get('tema', '').strip()
        norma        = data.get('norma', 'APA 7')
        refs_manuales = data.get('refs_manuales', '')

        if not tema:
            return jsonify({'success': False, 'error': 'Tema requerido'}), 400

        logger.info(f"🔬 Buscando referencias reales para: '{tema[:50]}'")

        # Buscar en CrossRef + OpenAlex
        refs = buscar_referencias_reales(tema, cantidad_total=12)

        if not refs:
            # Fallback: usar DeepSeek para generar referencias plausibles
            logger.warning("No se encontraron referencias reales, usando fallback IA")
            contenido_ia = generar_seccion('referencias', tema, refs_manuales, 'academico', norma, 'universitario', refs_manuales)
            return jsonify({
                'success':    True,
                'contenido':  contenido_ia or 'No se pudieron obtener referencias.',
                'fuente':     'ia_fallback',
                'total':      0
            })

        # Formatear según la norma
        texto_refs = formatear_referencias(refs, norma)

        # Si hay referencias manuales, agregarlas al final
        if refs_manuales and refs_manuales.strip():
            texto_refs += f"\n\n{refs_manuales.strip()}"

        logger.info(f"✅ {len(refs)} referencias reales formateadas en norma {norma}")

        return jsonify({
            'success':   True,
            'contenido': texto_refs,
            'fuente':    'crossref_openalex',
            'total':     len(refs),
            'detalles':  [{'tipo': r['tipo'], 'titulo': r['titulo'][:60], 'anio': r['anio']} for r in refs]
        })

    except Exception as e:
        logger.error(f"Error en /api/referencias-reales: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/exportar-pdf', methods=['POST'])
def exportar_pdf():
    try:
        data = request.json
        filename, filepath = generar_pdf(data['datos_usuario'], data['secciones'])
        return send_file(filepath, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        logger.error(f"Error PDF: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/exportar-word', methods=['POST'])
def exportar_word():
    try:
        data   = request.json
        buffer = generar_word(data['datos_usuario'], data['secciones'])
        nombre_archivo = f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=nombre_archivo,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        logger.error(f"Error Word: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health')
def health():
    return jsonify({
        'status':              'healthy',
        'api_configured':      bool(DEEPSEEK_API_KEY),
        'normas_disponibles':  list(NORMAS_INSTRUCCIONES.keys()),
        'tipos_disponibles':   list(TIPOS_INSTRUCCIONES.keys()),
        'version':             '3.2'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
