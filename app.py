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
logger.info("🚀 ACADEMIC REPORT PRO - VERSIÓN 2.0 MEJORADA")
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
- Referencias al final: Apellido, I. (año). Título en cursiva sin capitalizar excepto primera palabra. Editorial. DOI o URL si aplica.
- Artículos: Apellido, I. (año). Título del artículo. Nombre de Revista en Cursiva, volumen(número), páginas. https://doi.org/...
- DOI obligatorio cuando esté disponible.
""",
    'APA 6': """
NORMA APA 6ª EDICIÓN — Aplica estas reglas ESTRICTAMENTE:
- En texto: (Apellido, año, p. XX) para citas directas.
- 3-5 autores: primera vez todos; luego primer autor et al. 6+: et al. siempre.
- Referencias: Apellido, I. (año). Título del libro en cursiva. Ciudad, País: Editorial.
- Artículos: Apellido, I. (año). Título artículo. Nombre Revista en Cursiva, volumen(número), pp. XX-XX. doi:XXXXXXX
- Recuperado de URL (sin punto final en URL).
""",
    'ICONTEC': """
NORMA ICONTEC (NTC 5613) — Aplica estas reglas ESTRICTAMENTE:
- En texto: notas al pie numeradas superíndice (¹, ², ³...) O sistema autor-año según la variante.
- Referencias al final en ORDEN DE APARICIÓN (no alfabético).
- Formato libro: APELLIDO, Nombre. Título en cursiva. Número de edición. Ciudad: Editorial, año. Páginas.
- Artículos: APELLIDO, Nombre. Título artículo. En: Nombre de la Revista. Ciudad. Vol. X, No. X (mes, año); p. XX-XX.
- Mayúsculas solo en apellido del autor principal.
- Citar páginas específicas cuando aplique (p. o pp.).
""",
    'IEEE': """
NORMA IEEE — Aplica estas reglas ESTRICTAMENTE:
- En texto: números entre corchetes [1], [2], [3] en orden de aparición.
- Múltiples fuentes: [1], [2] o rango [1]–[3].
- Referencias numeradas en orden de aparición, NO alfabético.
- Artículos: [1] I. Apellido y N. Apellido, "Título del artículo," Nombre Revista en Abbrev. Cursiva, vol. X, no. X, pp. XX–XX, Mes año, doi: XX.XXXX/XXXXX.
- Libros: [2] I. Apellido, Título del Libro en Cursiva, Xth ed. Ciudad, País: Editorial, año, pp. XX–XX.
- Conferencias: [3] I. Apellido, "Título," en Proc. Nombre Conferencia, Ciudad, año, pp. XX–XX.
""",
    'Vancouver': """
NORMA VANCOUVER — Aplica estas reglas ESTRICTAMENTE (usada en ciencias de la salud):
- En texto: números superíndice o entre paréntesis en orden de aparición (1), (2)...
- Referencias numeradas consecutivamente según aparición en el texto.
- Artículos: Apellido AB, Apellido CD. Título del artículo. Abrev Revista. año;volumen(número):páginas.
- Libros: Apellido AB. Título del libro. Xth ed. Ciudad: Editorial; año.
- Capítulos: Apellido AB. Título capítulo. En: Apellido AB, editor. Título libro. Ciudad: Editorial; año. p. XX-XX.
- Hasta 6 autores: listar todos. Más de 6: primeros 6 + et al.
""",
    'Chicago': """
NORMA CHICAGO 17ª EDICIÓN (autor-fecha) — Aplica estas reglas ESTRICTAMENTE:
- En texto: (Apellido año, página) — sin coma entre autor y año.
- Bibliografía final en orden ALFABÉTICO.
- Libros: Apellido, Nombre. Año. Título en Cursiva. Ciudad: Editorial.
- Artículos: Apellido, Nombre. Año. "Título del artículo." Nombre Revista en Cursiva número, no. X: páginas. DOI o URL.
- Capítulos: Apellido, Nombre. Año. "Título capítulo." En Título del libro, editado por Nombre Apellido, XX-XX. Ciudad: Editorial.
- Fuentes en línea: incluir fecha de acceso si no hay fecha de publicación.
""",
    'MLA': """
NORMA MLA 9ª EDICIÓN — Aplica estas reglas ESTRICTAMENTE:
- En texto: (Apellido número de página) sin coma entre apellido y página.
- Bibliografía final llamada "Works Cited" en orden ALFABÉTICO.
- Libros: Apellido, Nombre. Título del Libro en Cursiva. Editorial, año.
- Artículos: Apellido, Nombre. "Título del artículo." Nombre Revista en Cursiva, vol. X, no. X, año, pp. XX-XX.
- Web: Apellido, Nombre. "Título de la página." Nombre del Sitio en Cursiva, fecha publicación, URL. Accedido día mes año.
- Si hay DOI, usar en lugar de URL.
""",
    'Harvard': """
NORMA HARVARD — Aplica estas reglas ESTRICTAMENTE:
- En texto: (Apellido año) o (Apellido año, p. XX) para citas directas.
- 3+ autores en texto: Apellido et al. año.
- Referencias al final en orden ALFABÉTICO.
- Libros: Apellido, I. (año) Título en cursiva, Xth edn. Ciudad: Editorial.
- Artículos: Apellido, I. (año) 'Título artículo', Nombre Revista en Cursiva, vol. X, no. X, pp. XX-XX.
- Capítulos: Apellido, I. (año) 'Título capítulo', en Apellido (ed.) Título libro en cursiva. Ciudad: Editorial, pp. XX-XX.
"""
}

# ============================================================
# INSTRUCCIONES ESPECÍFICAS POR TIPO DE INFORME
# ============================================================
TIPOS_INSTRUCCIONES = {
    'academico': "Informe académico estándar con rigor teórico, citas bibliográficas y análisis crítico.",
    'laboratorio': "Informe de laboratorio/práctica: incluye hipótesis, materiales, procedimiento experimental, resultados con datos/tablas, análisis de error y discusión científica.",
    'ejecutivo': "Informe ejecutivo empresarial: lenguaje claro y conciso, enfocado en KPIs, decisiones estratégicas, análisis costo-beneficio, recomendaciones accionables para tomadores de decisiones.",
    'tesis': "Tesis académica de alto rigor: argumentación profunda, revisión exhaustiva de literatura, marco metodológico robusto, contribución original al conocimiento, lenguaje formal universitario avanzado.",
    'pasantia': "Informe de pasantía/práctica profesional: describe la empresa/organización, actividades realizadas, competencias desarrolladas, aprendizajes obtenidos y evaluación de la experiencia.",
    'proyecto': "Informe de proyecto: incluye cronograma, recursos, entregables, gestión de riesgos, estado de avance y análisis de cumplimiento de objetivos."
}

# ============================================================
# FUNCIÓN PARA LLAMAR A DEEPSEEK
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
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=120)
        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado['choices'][0]['message']['content']
            contenido = contenido.encode('utf-8', 'ignore').decode('utf-8')
            logger.info(f"✅ Contenido recibido: {len(contenido)} caracteres")
            return contenido
        else:
            logger.error(f"Error HTTP {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"Error llamando DeepSeek: {e}")
        return None

# ============================================================
# FUNCIÓN PARA LIMPIAR TEXTO PARA PDF (sin HTML tags)
# ============================================================
def limpiar_para_pdf(texto):
    """Convierte el texto a formato seguro para ReportLab — sin <br/> ni tags HTML"""
    if not texto:
        return ""
    # Reemplazar saltos de línea reales
    texto = texto.replace('<br/>', '\n').replace('<br>', '\n')
    # Eliminar cualquier otro tag HTML que pueda existir
    texto = re.sub(r'<[^>]+>', '', texto)
    # Decodificar entidades HTML
    texto = html.unescape(texto)
    # Limpiar espacios múltiples
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()

# ============================================================
# FUNCIÓN PARA LIMPIAR TEXTO PARA WORD
# ============================================================
def limpiar_para_word(texto):
    """Convierte el texto a formato limpio para python-docx"""
    if not texto:
        return ""
    texto = texto.replace('<br/>', '\n').replace('<br>', '\n')
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = html.unescape(texto)
    return texto.strip()

# ============================================================
# PROMPTS DEDICADOS POR SECCIÓN — CON SOPORTE DE NORMA Y TIPO
# ============================================================
def build_prompt(seccion, tema, info, tipo, norma, nivel, refs_manuales=''):
    instruccion_norma = NORMAS_INSTRUCCIONES.get(norma, NORMAS_INSTRUCCIONES['APA 7'])
    instruccion_tipo = TIPOS_INSTRUCCIONES.get(tipo, TIPOS_INSTRUCCIONES['academico'])

    base = f"""Tipo de informe: {instruccion_tipo}
Nivel educativo: {nivel}.
Norma bibliográfica activa: {norma}.
{instruccion_norma}
"""

    if seccion == 'introduccion':
        return base + f"""Escribe ÚNICAMENTE la sección de INTRODUCCIÓN para el informe sobre: "{tema}".
Información adicional del autor: {info or 'Ninguna'}.

Requisitos:
- Mínimo 4 párrafos bien desarrollados
- Contexto general del tema, justificación, planteamiento del problema, estructura del informe
- Redacción formal y académica acorde al nivel {nivel}
- Incluye al menos 2 citas en el cuerpo del texto usando el formato {norma}
- NO incluyas el título, solo el contenido puro"""

    elif seccion == 'objetivos':
        return base + f"""Escribe ÚNICAMENTE la sección de OBJETIVOS para el informe sobre: "{tema}".

Formato EXACTO que debes seguir:
OBJETIVO GENERAL:
[Un objetivo general claro y medible que abarque todo el informe, en infinitivo]

OBJETIVOS ESPECÍFICOS:
1. [Objetivo específico 1 — verbo en infinitivo + acción concreta + resultado esperado]
2. [Objetivo específico 2]
3. [Objetivo específico 3]
4. [Objetivo específico 4]
5. [Objetivo específico 5]

Verbos sugeridos: Analizar, Identificar, Evaluar, Determinar, Describir, Comparar, Proponer, Establecer."""

    elif seccion == 'marco_teorico':
        return base + f"""Escribe ÚNICAMENTE el MARCO TEÓRICO para el informe sobre: "{tema}".
Información adicional: {info or 'Ninguna'}.

Requisitos:
- Mínimo 5 párrafos completos
- Antecedentes históricos, definiciones clave, teorías y modelos relevantes, estado actual del conocimiento
- Incluye al menos 4 citas bibliográficas en el cuerpo usando formato {norma} estrictamente
- Vocabulario especializado, redacción formal"""

    elif seccion == 'metodologia':
        return base + f"""Escribe ÚNICAMENTE la METODOLOGÍA para el informe de tipo "{tipo}" sobre: "{tema}".

Requisitos:
- Mínimo 4 párrafos
- Tipo y enfoque de investigación, población/muestra (si aplica), técnicas e instrumentos, procedimiento de análisis, consideraciones éticas
- Si es laboratorio: incluir materiales, procedimiento paso a paso, variables
- Si es ejecutivo: incluir fuentes de datos, métricas e indicadores usados
- Justifica cada decisión metodológica"""

    elif seccion == 'desarrollo':
        return base + f"""Escribe ÚNICAMENTE el DESARROLLO para el informe de tipo "{tipo}" sobre: "{tema}".
Información adicional: {info or 'Ninguna'}.

Requisitos:
- Mínimo 6 párrafos — es la sección más extensa
- Presentación de resultados/hallazgos, análisis detallado, discusión crítica, comparación con teoría
- Incluir datos concretos, ejemplos reales, comparaciones
- Al menos 3 citas en texto con formato {norma}
- Si es laboratorio: resultados con datos y análisis de error
- Si es ejecutivo: KPIs, métricas, análisis estratégico"""

    elif seccion == 'conclusiones':
        return base + f"""Escribe ÚNICAMENTE las CONCLUSIONES para el informe sobre: "{tema}".

Formato:
1. [Conclusión 1: responde directamente al objetivo general — mínimo 3 oraciones]
2. [Conclusión 2: hallazgo más importante del desarrollo — mínimo 3 oraciones]
3. [Conclusión 3: implicaciones prácticas o teóricas — mínimo 3 oraciones]
4. [Conclusión 4: limitaciones encontradas — mínimo 2 oraciones]
5. [Conclusión 5: perspectivas futuras o reflexión final — mínimo 3 oraciones]

Cada conclusión debe ser un párrafo sustancial. Conecta con los objetivos planteados."""

    elif seccion == 'recomendaciones':
        return base + f"""Escribe ÚNICAMENTE las RECOMENDACIONES para el informe de tipo "{tipo}" sobre: "{tema}".

Formato:
1. [Recomendación 1: dirigida a quién + acción concreta + justificación — 3 oraciones]
2. [Recomendación 2]
3. [Recomendación 3]
4. [Recomendación 4]
5. [Recomendación 5: para futuras investigaciones — 3 oraciones]

Deben ser prácticas, específicas, medibles y justificadas según el análisis del informe."""

    elif seccion == 'referencias':
        refs_extra = f"\nAdemás incluye o adapta estas referencias que el autor proporcionó:\n{refs_manuales}" if refs_manuales else ""
        return base + f"""Genera ÚNICAMENTE la lista de REFERENCIAS BIBLIOGRÁFICAS para el informe sobre: "{tema}".
Norma: {norma}.
{refs_extra}

Requisitos ESTRICTOS:
- Genera entre 8 y 10 referencias reales y académicas sobre este tema
- APLICA el formato {norma} con absoluta precisión según las instrucciones de norma anteriores
- Incluir: libros, artículos de revista científica, reportes de organismos (ONU, UNESCO, CEPAL, etc.), fuentes web académicas
- Años: preferiblemente 2015-2024
- Ordenar según lo indique la norma {norma} (alfabético o por aparición)
- Autores, títulos, editoriales y DOIs académicos y plausibles

Escribe solo la lista, sin título de sección."""

    return ""

# ============================================================
# GENERAR UNA SECCIÓN INDIVIDUAL
# ============================================================
def generar_seccion(seccion, tema, info_extra, tipo_informe, norma, nivel, refs_manuales=''):
    prompt = build_prompt(seccion, tema, info_extra, tipo_informe, norma, nivel, refs_manuales)
    if not prompt:
        return None

    system_prompt = (
        f"Eres un experto en redacción académica universitaria en español con especialización en normas bibliográficas ({norma}). "
        "Escribes contenido sustancial, formal y bien estructurado con vocabulario académico apropiado. "
        f"Aplicas la norma {norma} con absoluta precisión en citas y referencias. "
        "Respondes SOLO con el contenido solicitado, sin títulos de sección, sin preámbulos, sin '**', sin comentarios adicionales."
    )

    contenido = llamar_deepseek(prompt, system_prompt=system_prompt, max_tokens=3000)

    if not contenido:
        return None

    contenido = contenido.strip()
    # Guardar con \n para preservar párrafos — el frontend maneja la visualización
    logger.info(f"Sección '{seccion}' generada: {len(contenido)} caracteres")
    return contenido

# ============================================================
# GENERAR INFORME COMPLETO (fallback)
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
# GENERAR PDF — CORREGIDO (sin <br/> en ReportLab)
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

    # Estilos personalizados
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
        fontSize=15,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a365d'),
        spaceBefore=20,
        spaceAfter=10,
        alignment=TA_LEFT
    ))
    styles.add(ParagraphStyle(
        name='TituloPortada',
        parent=styles['Title'],
        fontSize=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a365d'),
        fontName='Helvetica-Bold',
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='SubtituloPortada',
        parent=styles['Normal'],
        fontSize=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#2d4a7a'),
        fontName='Helvetica-Bold',
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name='TextoCentrado',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=11,
        fontName='Helvetica',
        spaceAfter=6
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

    # ── PORTADA ──
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

    # ── ÍNDICE ──
    story.append(Paragraph("ÍNDICE", styles['Titulo1']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=8))
    for idx in [
        "1. Introducción",
        "2. Objetivos",
        "3. Marco Teórico",
        "4. Metodología",
        "5. Desarrollo",
        "6. Conclusiones",
        "7. Recomendaciones",
        "8. Referencias Bibliográficas"
    ]:
        story.append(Paragraph(f"{'&nbsp;' * 4}{idx}", styles['TextoLista']))
    story.append(PageBreak())

    # ── SECCIONES ──
    secciones_orden = [
        ("1. INTRODUCCIÓN", 'introduccion'),
        ("2. OBJETIVOS", 'objetivos'),
        ("3. MARCO TEÓRICO", 'marco_teorico'),
        ("4. METODOLOGÍA", 'metodologia'),
        ("5. DESARROLLO", 'desarrollo'),
        ("6. CONCLUSIONES", 'conclusiones'),
        ("7. RECOMENDACIONES", 'recomendaciones'),
        ("8. REFERENCIAS BIBLIOGRÁFICAS", 'referencias')
    ]

    for titulo, clave in secciones_orden:
        story.append(Paragraph(titulo, styles['Titulo1']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0'), spaceAfter=8))
        contenido_raw = secciones.get(clave, '')
        contenido = limpiar_para_pdf(contenido_raw)

        if contenido and len(contenido) > 50:
            # Dividir en párrafos por líneas dobles o saltos simples
            parrafos = re.split(r'\n{2,}', contenido)
            if len(parrafos) == 1:
                # Si no hay párrafos múltiples, dividir por líneas simples
                parrafos = contenido.split('\n')

            for parrafo in parrafos:
                parrafo = parrafo.strip()
                if parrafo:
                    # Detectar si es una lista numerada o con viñeta
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
# GENERAR WORD — MEJORADO
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

    # Configurar márgenes
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.5)

    # ── PORTADA ──
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

    # ── ÍNDICE ──
    h_idx = doc.add_heading('ÍNDICE', level=1)
    h_idx.runs[0].font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)

    indices = ['1. Introducción', '2. Objetivos', '3. Marco Teórico', '4. Metodología',
               '5. Desarrollo', '6. Conclusiones', '7. Recomendaciones', '8. Referencias Bibliográficas']
    for item in indices:
        p = doc.add_paragraph(style='List Number')
        p.text = ''
        p.clear()
        r = p.add_run(f"    {item}")
        r.font.size = Pt(11)

    doc.add_page_break()

    # ── SECCIONES ──
    secciones_orden = [
        ("1. INTRODUCCIÓN", 'introduccion'),
        ("2. OBJETIVOS", 'objetivos'),
        ("3. MARCO TEÓRICO", 'marco_teorico'),
        ("4. METODOLOGÍA", 'metodologia'),
        ("5. DESARROLLO", 'desarrollo'),
        ("6. CONCLUSIONES", 'conclusiones'),
        ("7. RECOMENDACIONES", 'recomendaciones'),
        ("8. REFERENCIAS BIBLIOGRÁFICAS", 'referencias')
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

@app.route('/generar-seccion', methods=['POST'])
def generar_seccion_endpoint():
    # ... tu código existente ...


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
        nombre_principal = autores[0].get('nombre', nombre) if autores else nombre

        if not tema:
            return jsonify({'success': False, 'error': 'El tema es requerido'}), 400

        logger.info(f"📨 Generando informe completo — Tema: {tema[:50]}...")
        secciones = generar_informe_completo(tema, texto_usuario, tipo_informe, norma, nivel)

        if not secciones:
            return jsonify({'success': False, 'error': 'No se pudo generar el informe'}), 500

        datos_usuario = {
            'nombre': nombre_principal,
            'autores_extra': autores[1:] if len(autores) > 1 else [],
            'tema': tema,
            'asignatura': asignatura,
            'profesor': profesor,
            'institucion': institucion,
            'ciudad': ciudad,
            'fecha': datetime.now().strftime('%d/%m/%Y'),
            'norma': norma
        }

        return jsonify({'success': True, 'secciones': secciones, 'datos_usuario': datos_usuario})
    except Exception as e:
        logger.error(f"Error en /generar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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

        logger.info(f"Generando sección '{seccion}' | Norma: {norma} | Tipo: {tipo} | Tema: {tema[:40]}...")
        contenido = generar_seccion(seccion, tema, info, tipo, norma, nivel, refs_manuales)

        if contenido:
            return jsonify({'success': True, 'seccion': seccion, 'contenido': contenido})
        else:
            return jsonify({'success': False, 'error': f'No se pudo generar: {seccion}'}), 500

    except Exception as e:
        logger.error(f"Error en /generar-seccion: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/exportar-pdf', methods=['POST'])
def exportar_pdf():
    try:
        data = request.json
        filename, filepath = generar_pdf(data['datos_usuario'], data['secciones'])
        return send_file(filepath, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        logger.error(f"Error exportando PDF: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/exportar-word', methods=['POST'])
def exportar_word():
    try:
        data = request.json
        buffer = generar_word(data['datos_usuario'], data['secciones'])
        nombre_archivo = f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=nombre_archivo,
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
        prompt = f"Genera un breve resumen académico sobre: {tema} en 300 palabras, con lenguaje formal."
        contenido = llamar_deepseek(prompt)
        if contenido:
            return jsonify({'success': True, 'contenido': contenido[:1000]})
        return jsonify({'success': False, 'error': 'No se pudo generar'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/normas', methods=['GET'])
def get_normas():
    """Retorna la lista de normas disponibles y sus descripciones"""
    return jsonify({
        'normas': list(NORMAS_INSTRUCCIONES.keys()),
        'tipos': list(TIPOS_INSTRUCCIONES.keys())
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'api_configured': bool(DEEPSEEK_API_KEY),
        'normas_disponibles': list(NORMAS_INSTRUCCIONES.keys()),
        'tipos_disponibles': list(TIPOS_INSTRUCCIONES.keys()),
        'version': '2.0'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
