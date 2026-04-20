from flask import Flask, render_template, request, jsonify, send_file
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os
import uuid
from datetime import datetime
import re
import requests
import html

app = Flask(__name__)
os.makedirs('informes_generados', exist_ok=True)

# ========== CONFIGURACIÓN DE GROQ ==========
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

print("=" * 50)
print("🚀 ACADEMIC REPORT PRO - VERSIÓN DEFINITIVA")
print("🧠 IA configurada como INVESTIGADOR CRÍTICO")
print(f"🔑 Groq API Key cargada: {'SÍ ✅' if GROQ_API_KEY else 'NO ❌'}")
print("=" * 50)

# ========== NORMAS ACADÉMICAS ==========
NORMAS_CONFIG = {
    'apa7': {'nombre': 'APA 7ª Edición', 'margen_superior': 72, 'margen_inferior': 72,
             'margen_izquierdo': 72, 'margen_derecho': 72, 'fuente': 'Times-Roman', 
             'tamaño': 12, 'interlineado': 24, 'sangria': 36},
    'apa6': {'nombre': 'APA 6ª Edición', 'margen_superior': 72, 'margen_inferior': 72,
             'margen_izquierdo': 72, 'margen_derecho': 72, 'fuente': 'Times-Roman',
             'tamaño': 12, 'interlineado': 24, 'sangria': 36},
    'icontec': {'nombre': 'ICONTEC (Colombia)', 'margen_superior': 85, 'margen_inferior': 85,
                'margen_izquierdo': 113, 'margen_derecho': 85, 'fuente': 'Helvetica',
                'tamaño': 12, 'interlineado': 18, 'sangria': 0},
    'vancouver': {'nombre': 'Vancouver', 'margen_superior': 72, 'margen_inferior': 72,
                  'margen_izquierdo': 72, 'margen_derecho': 72, 'fuente': 'Times-Roman',
                  'tamaño': 11, 'interlineado': 16, 'sangria': 0},
    'chicago': {'nombre': 'Chicago', 'margen_superior': 72, 'margen_inferior': 72,
                'margen_izquierdo': 72, 'margen_derecho': 72, 'fuente': 'Times-Roman',
                'tamaño': 12, 'interlineado': 18, 'sangria': 36},
    'harvard': {'nombre': 'Harvard', 'margen_superior': 72, 'margen_inferior': 72,
                'margen_izquierdo': 72, 'margen_derecho': 72, 'fuente': 'Times-Roman',
                'tamaño': 12, 'interlineado': 18, 'sangria': 36},
    'mla': {'nombre': 'MLA 9ª Edición', 'margen_superior': 72, 'margen_inferior': 72,
            'margen_izquierdo': 72, 'margen_derecho': 72, 'fuente': 'Times-Roman',
            'tamaño': 12, 'interlineado': 24, 'sangria': 36},
    'ieee': {'nombre': 'IEEE', 'margen_superior': 72, 'margen_inferior': 72,
             'margen_izquierdo': 72, 'margen_derecho': 72, 'fuente': 'Times-Roman',
             'tamaño': 10, 'interlineado': 12, 'sangria': 0}
}

def limpiar_texto(texto):
    """Limpia caracteres especiales y prepara texto para ReportLab"""
    if not texto:
        return ""

    try:
        if isinstance(texto, bytes):
            texto = texto.decode('utf-8')
        texto = html.escape(texto)
    except:
        pass

    # Reemplazar caracteres problemáticos
    reemplazos = {
        '\xa0': ' ', '\xad': '-', '\u2013': '-', '\u2014': '-',
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2026': '...',
    }
    for viejo, nuevo in reemplazos.items():
        texto = texto.replace(viejo, nuevo)

    texto = re.sub(r'\n{3,}', '<br/><br/>', texto)

    # CORRECCIONES CRÍTICAS
    texto = texto.replace('INFORMÉ', 'INFORME')
    texto = texto.replace('Conclusions', 'CONCLUSIONES')
    texto = texto.replace('CONCLUSIONS', 'CONCLUSIONES')

    # Eliminar caracteres no imprimibles
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', texto)

    return texto

def contenido_local_generico(tema):
    """Contenido de respaldo GENÉRICO (se adapta al tema del usuario)"""
    tema_limpio = tema if tema else "el tema de investigación"

    return {
        'introduccion': f"""El presente informe académico aborda el estudio de {tema_limpio}, una temática de creciente relevancia en el contexto actual.<br/><br/>
La investigación se justifica por la necesidad de generar evidencia empírica que contribuya al conocimiento existente.<br/><br/>
Las preguntas que guían esta investigación son: ¿Cuáles son los principales aspectos relacionados con {tema_limpio}? ¿Qué estrategias pueden implementarse?""",

        'objetivos': f"""<b>Objetivo General</b><br/><br/>Analizar los principales aspectos relacionados con {tema_limpio} en el contexto actual.<br/><br/><br/>
<b>Objetivos Específicos</b><br/><br/>
1. Identificar los factores clave asociados a {tema_limpio}.<br/><br/>
2. Describir las principales características y tendencias actuales.<br/><br/>
3. Analizar las implicaciones prácticas y teóricas de los hallazgos.<br/><br/>
4. Proponer recomendaciones basadas en el análisis realizado.""",

        'marco_teorico': f"""<b>Conceptos clave</b><br/><br/>
Para comprender adecuadamente {tema_limpio}, es necesario definir los conceptos fundamentales que lo sustentan.<br/><br/>
<b>Bases teóricas</b><br/><br/>
Las teorías existentes proporcionan un marco conceptual sólido para el análisis de {tema_limpio}.<br/><br/>
<b>Estado del arte</b><br/><br/>
Investigaciones recientes han profundizado en aspectos específicos de {tema_limpio}.""",

        'metodologia': f"""<b>Enfoque</b><br/><br/>La investigación adopta un enfoque mixto.<br/><br/>
<b>Población y muestra</b><br/><br/>Se seleccionó una muestra representativa de 250 participantes, utilizando técnicas de muestreo estratificado.<br/><br/>
<b>Instrumentos</b><br/><br/>Cuestionarios estructurados, entrevistas semiestructuradas y revisión documental.<br/><br/>
<b>Procedimiento</b><br/><br/>El estudio se desarrolló en tres fases: diseño, recolección y análisis.""",

        'desarrollo': f"""<b>Resultados obtenidos</b><br/><br/>
Los resultados del análisis muestran tendencias significativas relacionadas con {tema_limpio}. Los datos recopilados permiten identificar patrones y relaciones relevantes.<br/><br/>
<b>Análisis de resultados</b><br/><br/>
Los hallazgos indican que existen múltiples factores que inciden en {tema_limpio}. Se observan variaciones según el contexto y las condiciones específicas de cada caso.<br/><br/>
<b>Discusión</b><br/><br/>
Los resultados se alinean parcialmente con lo reportado en la literatura especializada, confirmando hallazgos previos y aportando nuevas perspectivas al conocimiento existente.""",

        'conclusiones': f"""1. {tema_limpio} es un tema de gran relevancia en el contexto actual.<br/><br/>
2. Los hallazgos confirman la importancia de abordar este tema desde una perspectiva integral.<br/><br/>
3. Se requiere mayor investigación para profundizar en aspectos específicos.<br/><br/>
4. Las recomendaciones propuestas constituyen una base para futuras intervenciones.<br/><br/>
5. Este estudio contribuye al conocimiento existente.""",

        'recomendaciones': f"""<b>Recomendaciones</b><br/><br/>
1. Fortalecer las líneas de investigación relacionadas con {tema_limpio}.<br/><br/>
2. Aplicar los hallazgos en contextos prácticos.<br/><br/>
3. Ampliar la muestra y el alcance geográfico."""
    }

def generar_informe_completo_con_ia(tema, info_usuario="", modo_referencias="auto", referencias_manuales=""):
    """Genera TODO el informe en UNA sola llamada a Groq con ANÁLISIS CRÍTICO REAL"""

    if not GROQ_API_KEY:
        print("❌ No hay API key de Groq configurada")
        return None, None

    print(f"🤖 Generando informe ANALÍTICO REAL con Groq para: {tema[:50]}...")

    if modo_referencias == "manual" and referencias_manuales:
        instruccion_refs = f"NO generes referencias. Usa estas: {referencias_manuales[:300]}"
    elif modo_referencias == "mixto":
        instruccion_refs = f"Usa estas referencias si son relevantes: {referencias_manuales[:300]}. Complementa con 3-4 más."
    else:
        instruccion_refs = "Genera 6-8 referencias bibliográficas reales y actualizadas sobre el tema."

    # PROMPT DEFINITIVO: LE DICE A LA IA CÓMO PENSAR
    prompt = f"""Tema: "{tema}"

{instruccion_refs}

⚠️ **INSTRUCCIÓN FUNDAMENTAL: NO ERES UN ESCRITOR, ERES UN INVESTIGADOR CRÍTICO.**
Tu tarea no es llenar un formato, es **ANALIZAR, CUESTIONAR y OPINAR** sobre el tema.

Para cada sección del informe, sigue estas reglas:

1.  **INTRODUCCIÓN**: No solo introduzcas el tema. Plantea una **TESIS** o una **PREGUNTA DE INVESTIGACIÓN** clara que guiará todo el informe. Justifica por qué el tema es **CRÍTICO** en este momento.

2.  **OBJETIVOS**: Deben ser específicos y medibles. Deben responder directamente a la pregunta de investigación.

3.  **MARCO TEÓRICO**: No solo nombres autores. **COMPARA** las posturas de diferentes autores. Señala si hay **CONSENSOS** o **DISPUTAS** en la literatura. ¿Qué es lo que la academia aún no ha resuelto sobre este tema?

4.  **METODOLOGÍA**: Justifica por qué elegiste esa muestra o enfoque. Señala una **LIMITACIÓN CLARA** de tu propio diseño (ej. "El tamaño de muestra, aunque representativo, no permite analizar..."). Un estudio sin limitaciones no es creíble.

5.  **DESARROLLO / RESULTADOS**:
    *   **DESCRIBE** tus hallazgos principales (ej. "El 70% de los productores dijeron...").
    *   **ANALIZA** el hallazgo. ¿Qué implica ese número? ¿Es alto, bajo, esperado, sorprendente? **COMPÁRALO** con los resultados de los autores que citaste en el marco teórico. ¿Tus resultados coinciden con los de Pérez (2020)? ¿Contradicen los de Gómez (2022)?
    *   **CRITICA** el hallazgo. ¿Hay una explicación alternativa? ¿El resultado podría estar sesgado?

6.  **CONCLUSIONES**:
    *   **HALLAZGOS PRINCIPALES**: Resume los 3 análisis más importantes que hiciste.
    *   **LIMITACIONES DEL ESTUDIO**: Enumera al menos 2 limitaciones CLARAS y ESPECÍFICAS de tu propia investigación (ej. "El estudio se limitó a la región andina, por lo que los resultados no son generalizables a la costa").
    *   **LÍNEAS DE INVESTIGACIÓN FUTURA**: Propón 2 preguntas de investigación NUEVAS y ESPECÍFICAS que surgen a partir de las limitaciones que acabas de mencionar.

7.  **RECOMENDACIONES**: Deben ser **ACCIONABLES** y **ESPECÍFICAS**. No digas "mejorar la educación". Di "Crear un programa de capacitación en IoT para pequeños agricultores en el departamento de Caldas".

**ESTRUCTURA OBLIGATORIA (debe ser exacta):**

**INTRODUCCIÓN**
**OBJETIVOS**
**Objetivo General:** (1)
**Objetivos Específicos:** (4)
**MARCO TEÓRICO**
**METODOLOGÍA**
**DESARROLLO** (Incluye una tabla con tus resultados y la discusión crítica)
**CONCLUSIONES** (Debe tener las subsecciones: Hallazgos principales, Limitaciones del estudio, Líneas de investigación futura)
**RECOMENDACIONES** (3-4 puntos)
**REFERENCIAS** (6-8 fuentes)

Escribe TODO en español. El tono debe ser ACADÉMICO, PROFESIONAL y CRÍTICO. No tengas miedo de señalar contradicciones o problemas. La credibilidad de un informe viene de su honestidad y profundidad analítica."""

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Eres un investigador académico senior, no un asistente. Tu especialidad es el análisis crítico. Tu tarea es escribir informes que no solo describan, sino que cuestionen, comparen y opinen. Para ti, un dato sin análisis no es un hallazgo. Las conclusiones deben generar nuevas preguntas."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 7500
    }

    try:
        print(f"📡 Enviando petición a Groq...")
        response = requests.post(GROQ_URL, headers=headers, json=data, timeout=180)
        print(f"📡 Respuesta código: {response.status_code}")

        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado['choices'][0]['message']['content']
            print(f"✅ Groq generó {len(contenido)} caracteres")
            contenido = limpiar_texto(contenido)

            secciones = {
                'introduccion': extraer_seccion_mejorada(contenido, 'INTRODUCCIÓN'),
                'objetivos': extraer_seccion_mejorada(contenido, 'OBJETIVOS'),
                'marco_teorico': extraer_seccion_mejorada(contenido, 'MARCO TEÓRICO'),
                'metodologia': extraer_seccion_mejorada(contenido, 'METODOLOGÍA'),
                'desarrollo': extraer_seccion_mejorada(contenido, 'DESARROLLO'),
                'conclusiones': extraer_seccion_mejorada(contenido, 'CONCLUSIONES'),
                'recomendaciones': extraer_seccion_mejorada(contenido, 'RECOMENDACIONES'),
                'referencias': extraer_seccion_mejorada(contenido, 'REFERENCIAS')
            }

            referencias_extraidas = extraer_referencias_desde_contenido(contenido)

            for key in secciones:
                if not secciones[key] or len(secciones[key]) < 200:
                    print(f"⚠️ Sección {key} incompleta, usando contenido local")
                    secciones[key] = contenido_local_generico(tema).get(key, "")

            print("✅ Informe analítico REAL generado correctamente.")
            return secciones, referencias_extraidas
        else:
            print(f"❌ Error HTTP {response.status_code}")
            return None, None
    except Exception as e:
        print(f"❌ Error conectando con Groq: {str(e)}")
        return None, None

def extraer_seccion_mejorada(contenido, nombre):
    patrones = [
        rf'\*\*{nombre}\*\*:?(.*?)(?=\*\*[A-ZÁÉÍÓÚ]|$)',
        rf'{nombre}:?(.*?)(?=\n\n\*\*[A-Z]|\n\n[A-ZÁÉÍÓÚ]|$)',
        rf'{nombre}\s*\n(.*?)(?=\n\n\*\*[A-Z]|\n\n[A-ZÁÉÍÓÚ]|$)'
    ]
    for patron in patrones:
        match = re.search(patron, contenido, re.DOTALL | re.IGNORECASE)
        if match:
            texto = match.group(1).strip()
            texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
            texto = texto.replace('\n', '<br/>')
            if len(texto) > 8000:
                texto = texto[:8000] + "..."
            return texto
    return ""

def extraer_referencias_desde_contenido(contenido):
    referencias = []
    patrones_refs = [
        r'##\s*Referencias?\s*\n(.*?)(?=\n##|$)',
        r'\*\*Referencias?\*\*:?(.*?)(?=\*\*[A-Z]|$)'
    ]
    for patron in patrones_refs:
        match = re.search(patron, contenido, re.DOTALL | re.IGNORECASE)
        if match:
            texto_refs = match.group(1)
            lineas = texto_refs.split('\n')
            for linea in lineas:
                linea = linea.strip()
                if linea and len(linea) > 10 and any(x in linea for x in ['(', ')', 'et al', 'vol', 'pp']):
                    referencias.append(linea)
            break
    return referencias[:8]

def obtener_referencias(tema, referencias_ia=None, referencias_manuales=None, modo_referencias="auto", norma="apa7"):
    if modo_referencias == "manual" and referencias_manuales:
        refs = [r.strip() for r in referencias_manuales.split('\n') if r.strip()]
        return refs if refs else ["Referencia no especificada"]
    elif modo_referencias == "mixto":
        refs = []
        if referencias_manuales:
            refs.extend([r.strip() for r in referencias_manuales.split('\n') if r.strip()])
        if referencias_ia:
            refs.extend(referencias_ia)
        return list(dict.fromkeys(refs))[:10]
    else:
        return referencias_ia if referencias_ia else [
            "Hernández Sampieri, R. (2021). Metodología de la Investigación. McGraw-Hill.",
            "Bisquerra Alzina, R. (2016). Metodología de la investigación educativa. La Muralla."
        ]

# ========== GENERADOR DE PDF ==========
class GeneradorPDF:
    def __init__(self):
        pass

    def crear_estilos(self, config_norma):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='TextoJustificado', parent=styles['Normal'],
            alignment=TA_JUSTIFY, fontSize=config_norma['tamaño'],
            fontName=config_norma['fuente'], spaceAfter=12, 
            leading=config_norma['interlineado'],
            leftIndent=config_norma['sangria']))
        styles.add(ParagraphStyle(name='Titulo1', parent=styles['Heading1'],
            fontSize=config_norma['tamaño'] + 2, fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1a365d'), spaceBefore=24, spaceAfter=16))
        styles.add(ParagraphStyle(name='TituloPortada', parent=styles['Title'],
            fontSize=22, alignment=TA_CENTER, spaceAfter=20,
            textColor=colors.HexColor('#1a365d')))
        return styles

    def generar_pdf(self, datos_usuario, opciones, secciones_ia=None, referencias_ia=None):
        nombre = datos_usuario.get('nombre', 'Estudiante') or "Estudiante"
        tema = datos_usuario.get('tema', 'Tema de Investigación') or "Tema de Investigación"
        asignatura = datos_usuario.get('asignatura', 'Asignatura') or "Asignatura"
        profesor = datos_usuario.get('profesor', 'Docente') or "Docente"
        institucion = datos_usuario.get('institucion', 'Institución Educativa') or "Institución Educativa"
        fecha_entrega = datos_usuario.get('fecha_entrega', datetime.now().strftime('%d/%m/%Y'))
        norma = datos_usuario.get('norma', 'apa7')
        modo_referencias = datos_usuario.get('modo_referencias', 'auto')
        referencias_manuales = datos_usuario.get('referencias_manuales', '')

        config_norma = NORMAS_CONFIG.get(norma, NORMAS_CONFIG['apa7'])
        print(f"📏 Aplicando norma: {config_norma['nombre']}")

        if secciones_ia and isinstance(secciones_ia, dict):
            introduccion = limpiar_texto(secciones_ia.get('introduccion', ''))
            objetivos = limpiar_texto(secciones_ia.get('objetivos', ''))
            marco_teorico = limpiar_texto(secciones_ia.get('marco_teorico', ''))
            metodologia = limpiar_texto(secciones_ia.get('metodologia', ''))
            desarrollo = limpiar_texto(secciones_ia.get('desarrollo', ''))
            conclusiones = limpiar_texto(secciones_ia.get('conclusiones', ''))
            recomendaciones = limpiar_texto(secciones_ia.get('recomendaciones', ''))
            print("✅ Usando secciones generadas por IA")
        else:
            introduccion = contenido_local_generico('introduccion', tema)
            objetivos = contenido_local_generico('objetivos', tema)
            marco_teorico = contenido_local_generico('marco_teorico', tema)
            metodologia = contenido_local_generico('metodologia', tema)
            desarrollo = contenido_local_generico('desarrollo', tema)
            conclusiones = contenido_local_generico('conclusiones', tema)
            recomendaciones = contenido_local_generico('recomendaciones', tema)
            print("⚠️ Usando contenido local genérico")

        referencias = obtener_referencias(tema, referencias_ia, referencias_manuales, modo_referencias, norma)

        filename = f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}.pdf"
        filepath = os.path.join('informes_generados', filename)
        styles = self.crear_estilos(config_norma)

        doc = SimpleDocTemplate(filepath, 
            pagesize=letter,
            rightMargin=config_norma['margen_derecho'],
            leftMargin=config_norma['margen_izquierdo'],
            topMargin=config_norma['margen_superior'],
            bottomMargin=config_norma['margen_inferior'])

        story = []

        # PORTADA
        story.append(Spacer(1, 1.5*inch))
        story.append(Paragraph("INFORME ACADÉMICO", styles['TituloPortada']))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(tema.upper(), styles['TextoJustificado']))
        story.append(Spacer(1, 1.2*inch))
        story.append(Paragraph(f"<b>Presentado por:</b> {nombre}", styles['TextoJustificado']))
        story.append(Paragraph(f"<b>Asignatura:</b> {asignatura}", styles['TextoJustificado']))
        story.append(Paragraph(f"<b>Docente:</b> {profesor}", styles['TextoJustificado']))
        story.append(Paragraph(f"<b>Institución:</b> {institucion}", styles['TextoJustificado']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"<b>Fecha de entrega:</b> {fecha_entrega}", styles['TextoJustificado']))
        story.append(Paragraph(f"<b>Norma aplicada:</b> {config_norma['nombre']}", styles['TextoJustificado']))
        story.append(PageBreak())

        # ÍNDICE
        story.append(Paragraph("ÍNDICE", styles['Titulo1']))
        indices = ["1. INTRODUCCIÓN", "2. OBJETIVOS", "3. MARCO TEÓRICO", "4. METODOLOGÍA",
                   "5. DESARROLLO", "6. CONCLUSIONES", "7. RECOMENDACIONES", "8. REFERENCIAS"]
        for idx in indices:
            story.append(Paragraph(f"• {idx}", styles['TextoJustificado']))
        story.append(PageBreak())

        # SECCIONES
        story.append(Paragraph("1. INTRODUCCIÓN", styles['Titulo1']))
        story.append(Paragraph(introduccion, styles['TextoJustificado']))
        story.append(PageBreak())

        story.append(Paragraph("2. OBJETIVOS", styles['Titulo1']))
        story.append(Paragraph(objetivos, styles['TextoJustificado']))
        story.append(PageBreak())

        story.append(Paragraph("3. MARCO TEÓRICO", styles['Titulo1']))
        story.append(Paragraph(marco_teorico, styles['TextoJustificado']))
        story.append(PageBreak())

        story.append(Paragraph("4. METODOLOGÍA", styles['Titulo1']))
        story.append(Paragraph(metodologia, styles['TextoJustificado']))
        story.append(PageBreak())

        story.append(Paragraph("5. DESARROLLO", styles['Titulo1']))
        story.append(Paragraph(desarrollo, styles['TextoJustificado']))
        story.append(PageBreak())

        story.append(Paragraph("6. CONCLUSIONES", styles['Titulo1']))
        story.append(Paragraph(conclusiones, styles['TextoJustificado']))
        story.append(PageBreak())

        story.append(Paragraph("7. RECOMENDACIONES", styles['Titulo1']))
        story.append(Paragraph(recomendaciones, styles['TextoJustificado']))
        story.append(PageBreak())

        story.append(Paragraph("8. REFERENCIAS", styles['Titulo1']))
        for i, ref in enumerate(referencias, 1):
            story.append(Paragraph(f"{i}. {ref}", styles['TextoJustificado']))
            story.append(Spacer(1, 0.1*inch))

        doc.build(story)
        print(f"✅ PDF generado: {filename}")
        return filename, filepath

generador = GeneradorPDF()

# ========== RUTAS ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar', methods=['POST'])
def generar():
    try:
        datos = request.json
        modo = datos.get('modo', 'auto')
        tema = datos.get('tema', '')
        texto_auto = datos.get('texto_completo', '') if modo in ['auto', 'rapido'] else ''
        modo_referencias = datos.get('modo_referencias', 'auto')
        referencias_manuales = datos.get('referencias_manuales', '')

        if modo == 'rapido' and texto_auto:
            tema = texto_auto

        if not tema or len(tema) < 3:
            return jsonify({'success': False, 'error': 'Por favor ingresa un tema válido'}), 400

        opciones = {'incluir_recomendaciones': True}

        secciones_ia, referencias_ia = generar_informe_completo_con_ia(tema, texto_auto, modo_referencias, referencias_manuales)

        datos_usuario = {
            'nombre': datos.get('nombre', ''),
            'tema': tema,
            'asignatura': datos.get('asignatura', ''),
            'profesor': datos.get('profesor', ''),
            'institucion': datos.get('institucion', ''),
            'fecha_entrega': datos.get('fecha_entrega', ''),
            'norma': datos.get('norma', 'apa7'),
            'modo_referencias': modo_referencias,
            'referencias_manuales': referencias_manuales
        }

        filename, filepath = generador.generar_pdf(datos_usuario, opciones, secciones_ia, referencias_ia)

        return jsonify({'success': True, 'filename': filename, 'download_url': f'/descargar/{filename}'})

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/descargar/<filename>')
def descargar(filename):
    return send_file(
        os.path.join('informes_generados', filename),
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Servidor iniciado en puerto {port}")
    app.run(debug=False, host='0.0.0.0', port=port)
