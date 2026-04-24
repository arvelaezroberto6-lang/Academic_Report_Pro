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
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Importar módulo de referencias reales ──────────────────────
from referencias_reales import buscar_referencias_reales, formatear_referencias

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.makedirs('informes_generados', exist_ok=True)

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL     = "https://api.deepseek.com/v1/chat/completions"

logger.info("=" * 60)
logger.info("🚀 ACADEMIC REPORT PRO - VERSIÓN 3.3")
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
def llamar_deepseek(prompt, system_prompt=None, max_tokens=3000, reintentos=3):
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
    for intento in range(1, reintentos + 1):
        try:
            response = http_requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=150)
            if response.status_code == 200:
                contenido = response.json()['choices'][0]['message']['content']
                return contenido.encode('utf-8', 'ignore').decode('utf-8')
            elif response.status_code in (429, 503, 502):
                wait = 5 * intento
                logger.warning(f"DeepSeek HTTP {response.status_code} — reintento {intento}/{reintentos} en {wait}s")
                time.sleep(wait)
            else:
                logger.error(f"DeepSeek HTTP {response.status_code}: {response.text[:200]}")
                return None
        except http_requests.exceptions.Timeout:
            wait = 8 * intento
            logger.warning(f"Timeout DeepSeek — reintento {intento}/{reintentos} en {wait}s")
            time.sleep(wait)
        except Exception as e:
            logger.error(f"Error DeepSeek: {e}")
            if intento < reintentos:
                time.sleep(5 * intento)
            else:
                return None
    logger.error(f"DeepSeek falló después de {reintentos} reintentos")
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
# PROMPTS POR SECCIÓN  (v3.3 — mejorado con recomendaciones)
# ============================================================
# Contexto colombiano inyectado en todas las secciones relevantes
_CONTEXTO_COLOMBIA = """
CONTEXTO COLOMBIANO OBLIGATORIO:
- Cuando sea pertinente al tema, menciona entidades reales de Colombia:
  Ministerio de Tecnologías de la Información y las Comunicaciones (MinTIC),
  Departamento Administrativo Nacional de Estadística (DANE),
  Comisión de Regulación de Comunicaciones (CRC), Colciencias/MinCiencias,
  SENA, DNP, Superintendencia de Industria y Comercio, etc.
- Cita datos estadísticos reales o verosímiles de Colombia (porcentajes, cifras sectoriales).
- Menciona empresas, sectores o casos reales del país cuando sea aplicable.
- Aterriza los conceptos globales al contexto nacional colombiano.
"""

_ESTILO_NATURAL = """
ESTILO DE REDACCIÓN:
- Redacción académica pero con voz propia: mezcla de análisis técnico y reflexión del autor.
- Evita frases vacías, genéricas o que suenen completamente automatizadas.
- Usa variedad de estructuras sintácticas; no comiences todos los párrafos igual.
- Incluye interpretaciones o valoraciones propias del autor en las secciones analíticas.
"""

def build_prompt(seccion, tema, info, tipo, norma, nivel, refs_manuales=''):
    instruccion_norma = NORMAS_INSTRUCCIONES.get(norma, NORMAS_INSTRUCCIONES['APA 7'])
    instruccion_tipo  = TIPOS_INSTRUCCIONES.get(tipo, TIPOS_INSTRUCCIONES['academico'])

    base = f"""Tipo de informe: {instruccion_tipo}
Nivel educativo: {nivel}.
Norma bibliográfica activa: {norma}.
{instruccion_norma}
{_CONTEXTO_COLOMBIA}
{_ESTILO_NATURAL}
"""
    if seccion == 'introduccion':
        return base + f"""Escribe ÚNICAMENTE la INTRODUCCIÓN del informe sobre: "{tema}".
Info adicional del autor: {info or 'Ninguna'}.
Estructura obligatoria (4-5 párrafos):
1. Contexto general del tema con datos estadísticos concretos y referencia a Colombia.
2. Justificación: por qué es relevante este tema en el panorama colombiano y latinoamericano.
3. Planteamiento del problema: ¿cuál es la brecha, tensión o necesidad que aborda el informe?
4. Alineación con los objetivos del informe: anuncia brevemente qué secciones siguen y qué aporta cada una.
- Al menos 2 citas en formato {norma}. Referencias entre 2019 y 2025.
- Menciona al menos una entidad colombiana relevante (MinTIC, DANE, CRC, etc.) si aplica al tema.
- NO incluyas el título de la sección, solo el contenido puro."""

    elif seccion == 'objetivos':
        return base + f"""Escribe ÚNICAMENTE los OBJETIVOS del informe sobre: "{tema}".
Usa este formato exacto:

OBJETIVO GENERAL:
[Un objetivo general claro, medible y redactado en infinitivo que capture la esencia del informe]

OBJETIVOS ESPECÍFICOS:
1. [Verbo en infinitivo + acción concreta + resultado esperado — directamente vinculado al tema]
2. [Verbo en infinitivo + acción concreta + resultado esperado]
3. [Verbo en infinitivo + acción concreta + resultado esperado]
4. [Verbo en infinitivo + acción concreta + resultado esperado]
5. [Verbo en infinitivo + acción concreta + resultado esperado]

Cada objetivo específico debe ser verificable y conectarse con una sección del informe (marco teórico, metodología, desarrollo, conclusiones o recomendaciones)."""

    elif seccion == 'marco_teorico':
        return base + f"""Escribe ÚNICAMENTE el MARCO TEÓRICO del informe sobre: "{tema}".
Info adicional del autor: {info or 'Ninguna'}.
Estructura obligatoria (mínimo 5 párrafos):
1. Antecedentes históricos o evolución del tema.
2. Definiciones y conceptos clave con citas de autores reconocidos.
3. Teorías o modelos teóricos principales que sustentan el informe.
4. Estado del arte: investigaciones recientes (2020-2025) sobre el tema.
5. Contexto colombiano: cómo se ha estudiado o implementado este tema en Colombia.
- Al menos 5 citas en formato {norma} con años entre 2019 y 2025.
- Incluye autores latinoamericanos o colombianos cuando existan."""

    elif seccion == 'metodologia':
        return base + f"""Escribe ÚNICAMENTE la METODOLOGÍA del informe de tipo "{tipo}" sobre: "{tema}".
Info adicional del autor: {info or 'Ninguna'}.
Estructura obligatoria (mínimo 4 párrafos):
1. Enfoque investigativo (cuantitativo, cualitativo o mixto) con justificación del por qué.
2. Tipo y alcance de la investigación (descriptivo, explicativo, correlacional, etc.).
3. Técnicas e instrumentos: describe herramientas concretas, fuentes de información y cómo se usaron.
   - IMPORTANTE: describe las herramientas de forma simple y creíble para el nivel {nivel}.
   - Si se usaron herramientas digitales o software, explica exactamente el procedimiento paso a paso.
4. Criterios éticos y limitaciones del estudio.
{"5. Si aplica: materiales, equipos utilizados y procedimiento experimental detallado." if tipo == 'laboratorio' else ""}
- Justifica cada decisión metodológica con argumentos académicos."""

    elif seccion == 'desarrollo':
        return base + f"""Escribe ÚNICAMENTE el DESARROLLO del informe de tipo "{tipo}" sobre: "{tema}".
Info adicional del autor: {info or 'Ninguna'}.
Estructura obligatoria (mínimo 7 párrafos):
1. Presentación de resultados principales con datos, cifras o ejemplos concretos.
2. Para cumplir el Objetivo Específico 1 se realizó... [explícita vinculación con objetivos].
3. Para cumplir el Objetivo Específico 2 se realizó... [análisis de segundo hallazgo].
4. Comparación con el marco teórico: ¿los resultados confirman o contradicen la teoría?
5. Análisis del contexto colombiano: aplica los resultados a la realidad de Colombia.
   - Menciona datos del DANE, MinTIC, CRC u otras entidades si aplican al tema.
   - Nombra empresas, sectores o casos reales del país.
6. Tablas o datos estructurados: incluye al menos UNA tabla con datos relevantes en formato de texto:
   Tabla 1. [Nombre de la tabla]
   | Categoría | Valor | Año | Fuente |
   | ... | ... | ... | ... |
7. Análisis crítico y opinión del autor: ¿qué implican estos resultados? ¿qué limitaciones existen?
- Al menos 4 citas en formato {norma}. Fuentes entre 2019 y 2025."""

    elif seccion == 'conclusiones':
        return base + f"""Escribe ÚNICAMENTE las CONCLUSIONES del informe sobre: "{tema}".
Usa este formato (5 conclusiones numeradas):
1. [Responde directamente al objetivo general — mínimo 3-4 oraciones explicando si se cumplió y por qué]
2. [Hallazgo más importante del desarrollo: dato clave o resultado central]
3. [Implicaciones prácticas para Colombia: qué debería cambiar o mejorar en el país]
4. [Limitaciones del estudio: qué no pudo resolverse y por qué]
5. [Perspectivas futuras: líneas de investigación o acciones recomendadas a futuro]
- Incluye al menos 1 opinión o interpretación propia del autor en las conclusiones.
- Usa un tono reflexivo y personal, no únicamente descriptivo."""

    elif seccion == 'recomendaciones':
        return base + f"""Escribe ÚNICAMENTE las RECOMENDACIONES del informe de tipo "{tipo}" sobre: "{tema}".
Usa este formato (5 recomendaciones numeradas):
1. [Dirigida al Ministerio o entidad pública colombiana relevante: acción concreta + justificación — 3 oraciones]
2. [Dirigida a empresas del sector privado en Colombia: acción específica + beneficio esperado]
3. [Dirigida a instituciones educativas o de investigación: formación, programas o estudios sugeridos]
4. [Dirigida a profesionales o practicantes del área: cambio de práctica o habilidad a desarrollar]
5. [Para futuras investigaciones: pregunta de investigación abierta o metodología a explorar]
- Cada recomendación debe ser accionable, dirigida a un actor específico y justificada."""

    elif seccion == 'referencias':
        refs_extra = f"\nIncluye o adapta estas referencias del autor:\n{refs_manuales}" if refs_manuales else ""
        return base + f"""Genera ÚNICAMENTE la lista de REFERENCIAS BIBLIOGRÁFICAS sobre: "{tema}".
{refs_extra}
Criterios obligatorios:
- Entre 10 y 12 referencias académicas (artículos, libros, informes técnicos, reportes institucionales).
- TODAS las referencias deben ser de años 2019-2025.
- Al menos 3 referencias deben provenir de entidades o autores colombianos o latinoamericanos
  (DANE, MinTIC, Colciencias, CEPAL, revistas colombianas indexadas, etc.).
- Al menos 4 referencias deben ser artículos de revista académica con DOI.
- Aplica formato {norma} con precisión. Sin título de sección ni preámbulo."""

    return ""

# ============================================================
# GENERAR SECCIÓN
# ============================================================
def generar_seccion(seccion, tema, info_extra, tipo_informe, norma, nivel, refs_manuales=''):
    prompt = build_prompt(seccion, tema, info_extra, tipo_informe, norma, nivel, refs_manuales)
    if not prompt:
        return None

    system_prompt = (
        f"Eres un experto en redacción académica universitaria en español con especialización en norma {norma} "
        "y profundo conocimiento del contexto colombiano y latinoamericano. "
        "Escribes contenido sustancial, formal y bien estructurado, con voz propia y análisis crítico. "
        "Cuando aplique al tema, incluyes datos reales de Colombia, referencias a entidades como MinTIC, DANE, "
        "CRC, Colciencias o similares, y mencionas casos o ejemplos concretos del país. "
        "Usas referencias de años 2019-2025. Incluyes tablas de datos cuando el contenido lo amerita. "
        "Balanceas el análisis técnico con interpretaciones propias del autor. "
        "Respondes SOLO con el contenido solicitado, sin títulos de sección, sin preámbulos, sin '**', sin markdown."
    )

    contenido = llamar_deepseek(prompt, system_prompt=system_prompt, max_tokens=3000)
    if contenido:
        contenido = contenido.strip()
        logger.info(f"Sección '{seccion}' generada: {len(contenido)} chars")
    return contenido

def generar_informe_completo(tema, info_extra, tipo_informe, norma, nivel):
    """
    Genera las 8 secciones en paralelo (hasta 4 simultáneas) para reducir
    tiempos de espera y minimizar fallos por timeout secuencial.
    """
    claves = ['introduccion', 'objetivos', 'marco_teorico', 'metodologia',
              'desarrollo', 'conclusiones', 'recomendaciones', 'referencias']
    secciones = {c: '' for c in claves}

    def _generar(clave):
        resultado = generar_seccion(clave, tema, info_extra, tipo_informe, norma, nivel)
        return clave, resultado or ''

    with ThreadPoolExecutor(max_workers=4) as executor:
        futuros = {executor.submit(_generar, c): c for c in claves}
        for futuro in as_completed(futuros):
            try:
                clave, contenido = futuro.result()
                secciones[clave] = contenido
                logger.info(f"✅ Sección '{clave}' completada ({len(contenido)} chars)")
            except Exception as e:
                clave = futuros[futuro]
                logger.error(f"❌ Error en sección '{clave}': {e}")

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
        'version':             '3.3'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
