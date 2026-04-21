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

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear directorio para informes
os.makedirs('informes_generados', exist_ok=True)

# ============================================================
# CONFIGURACIÓN DE DEEPSEEK
# ============================================================
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

logger.info("=" * 60)
logger.info("🚀 ACADEMIC REPORT PRO - VERSIÓN CON DEEPSEEK")
logger.info(f"🔑 API Key configurada: {'SÍ ✅' if DEEPSEEK_API_KEY else 'NO ❌'}")
logger.info("=" * 60)

# ============================================================
# FUNCIÓN PARA GENERAR INFORME CON DEEPSEEK
# ============================================================
def generar_informe_con_ia(tema, info_extra=""):
    """Genera un informe académico profesional usando DeepSeek API"""
    
    if not DEEPSEEK_API_KEY:
        logger.error("❌ No hay API key de DeepSeek")
        return None
    
    logger.info(f"🤖 Generando informe con DeepSeek sobre: {tema[:50]}...")
    
    # Prompt profesional y detallado
    prompt = f"""Eres un asistente académico experto. Genera un INFORME ACADÉMICO PROFESIONAL sobre: "{tema}"

Información adicional proporcionada: {info_extra if info_extra else 'No hay información adicional'}

⚠️ ESTRUCTURA OBLIGATORIA (debes seguir este formato exactamente):

**INTRODUCCIÓN**
Escribe 2-3 párrafos que incluyan:
- Contexto general del tema
- Planteamiento del problema
- Justificación de la investigación
- Objetivos generales del informe

**OBJETIVOS**
- Objetivo General: (1 objetivo claro y medible)
- Objetivos Específicos: (4-5 objetivos detallados)

**MARCO TEÓRICO**
Desarrolla 3-4 párrafos con:
- Conceptos fundamentales relacionados al tema
- Teorías o enfoques principales
- Antecedentes de investigaciones previas
- Definición de términos clave

**METODOLOGÍA**
Describe detalladamente:
- Tipo de investigación (ej: descriptiva, exploratoria)
- Enfoque (cualitativo, cuantitativo o mixto)
- Población y muestra (con datos específicos)
- Técnicas e instrumentos de recolección
- Procedimiento paso a paso

**DESARROLLO Y RESULTADOS**
Presenta:
- Hallazgos principales (mínimo 4 puntos)
- Análisis de datos (incluye porcentajes o cifras)
- Tablas o gráficos descritos en texto
- Discusión de resultados
- Comparación con otros estudios

**CONCLUSIONES**
Escribe mínimo 5 conclusiones numeradas que:
- Respondan a los objetivos planteados
- Sean específicas y basadas en evidencia
- Muestren el cumplimiento de la investigación

**RECOMENDACIONES**
Formula 4 recomendaciones prácticas:
- Para futuras investigaciones
- Para la comunidad académica
- Para aplicación profesional
- Para políticas o decisiones

**REFERENCIAS**
Lista 6-8 fuentes bibliográficas relevantes en formato APA 7ª edición (libros, artículos, tesis)

REQUISITOS IMPORTANTES:
- Escribe en español neutro y académico
- Usa **negritas** SOLO para los títulos de sección
- Proporciona contenido sustancial (no solo títulos vacíos)
- Incluye datos específicos, fechas, nombres, cifras
- Extensión total: mínimo 2000 palabras
- Sé original y evita texto genérico
- Mantén coherencia entre todas las secciones

¡Genera un informe completo, riguroso y de alta calidad!"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "Eres un asistente académico profesional con amplia experiencia en investigación. Generas informes detallados, rigurosos y bien estructurados en español. Siempre incluyes datos específicos, ejemplos concretos y análisis profundos."
            },
            {
                "role": "user",
                "content": prompt
            }
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
            logger.info(f"✅ Informe generado exitosamente ({len(contenido)} caracteres)")
            return contenido
        else:
            logger.error(f"❌ Error HTTP {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("⏱️ Timeout: DeepSeek tardó más de 120 segundos")
        return None
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return None

# ============================================================
# FUNCIÓN PARA EXTRAER SECCIONES
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
    
    # Patrones de búsqueda
    patrones = {
        'introduccion': r'\*\*INTRODUCCIÓN\*\*:?(.*?)(?=\*\*OBJETIVOS|\*\*MARCO|\*\*METODOLOGÍA|\*\*DESARROLLO|\*\*CONCLUSIONES|$)',
        'objetivos': r'\*\*OBJETIVOS\*\*:?(.*?)(?=\*\*MARCO|\*\*METODOLOGÍA|\*\*DESARROLLO|\*\*CONCLUSIONES|$)',
        'marco_teorico': r'\*\*MARCO TEÓRICO\*\*:?(.*?)(?=\*\*METODOLOGÍA|\*\*DESARROLLO|\*\*CONCLUSIONES|$)',
        'metodologia': r'\*\*METODOLOGÍA\*\*:?(.*?)(?=\*\*DESARROLLO|\*\*RESULTADOS|\*\*CONCLUSIONES|$)',
        'desarrollo': r'\*\*DESARROLLO Y RESULTADOS\*\*:?(.*?)(?=\*\*CONCLUSIONES|$)',
        'conclusiones': r'\*\*CONCLUSIONES\*\*:?(.*?)(?=\*\*RECOMENDACIONES|$)',
        'recomendaciones': r'\*\*RECOMENDACIONES\*\*:?(.*?)(?=\*\*REFERENCIAS|$)',
        'referencias': r'\*\*REFERENCIAS\*\*:?(.*?)$'
    }
    
    for key, patron in patrones.items():
        match = re.search(patron, contenido, re.DOTALL | re.IGNORECASE)
        if match:
            texto = match.group(1).strip()
            # Convertir markdown a HTML para ReportLab
            texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
            texto = re.sub(r'\*(.*?)\*', r'<i>\1</i>', texto)
            texto = texto.replace('\n', '<br/>')
            secciones[key] = texto
            logger.info(f"✅ Sección '{key}' extraída: {len(texto)} caracteres")
    
    return secciones

# ============================================================
# CONTENIDO DE RESPALDO (si la IA falla)
# ============================================================
def contenido_respaldo(tema):
    """Contenido genérico de respaldo (solo si la IA falla)"""
    return {
        'introduccion': f"<b>Contexto</b><br/>Este informe aborda el tema: {tema}. La IA no está disponible en este momento, por favor verifica la conexión.",
        'objetivos': "<b>Objetivo General</b><br/>Analizar el tema propuesto.<br/><br/><b>Objetivos Específicos</b><br/>1. Comprender los conceptos clave<br/>2. Identificar aplicaciones prácticas",
        'marco_teorico': "Contenido no disponible temporalmente. Por favor, intenta nuevamente más tarde.",
        'metodologia': "Contenido no disponible temporalmente.",
        'desarrollo': "Contenido no disponible temporalmente.",
        'conclusiones': "Contenido no disponible temporalmente.",
        'recomendaciones': "Contenido no disponible temporalmente.",
        'referencias': "No hay referencias disponibles en este momento."
    }

# ============================================================
# GENERADOR DE PDF
# ============================================================
def generar_pdf(datos_usuario, secciones):
    """Genera el PDF profesional con el contenido"""
    
    # Validar datos
    nombre = datos_usuario.get('nombre', 'Estudiante')
    tema = datos_usuario.get('tema', 'Tema de Investigación')
    
    # Generar nombre único
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    filename = f"informe_{timestamp}_{unique_id}.pdf"
    filepath = os.path.join('informes_generados', filename)
    
    # Configurar estilos
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
        spaceAfter=20,
        textColor=colors.HexColor('#1a365d')
    ))
    
    styles.add(ParagraphStyle(
        name='TextoCentrado',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=12,
        spaceAfter=10
    ))
    
    # Crear documento
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    story = []
    
    # PORTADA
    story.append(Spacer(1, 2.5*inch))
    story.append(Paragraph("INFORME ACADÉMICO", styles['TituloPortada']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(tema.upper(), styles['TextoCentrado']))
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph(f"<b>Presentado por:</b> {nombre}", styles['TextoCentrado']))
    story.append(Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')}", styles['TextoCentrado']))
    story.append(PageBreak())
    
    # SECCIONES
    secciones_orden = [
        ("1. INTRODUCCIÓN", 'introduccion'),
        ("2. OBJETIVOS", 'objetivos'),
        ("3. MARCO TEÓRICO", 'marco_teorico'),
        ("4. METODOLOGÍA", 'metodologia'),
        ("5. DESARROLLO Y RESULTADOS", 'desarrollo'),
        ("6. CONCLUSIONES", 'conclusiones'),
        ("7. RECOMENDACIONES", 'recomendaciones'),
        ("8. REFERENCIAS", 'referencias')
    ]
    
    for titulo, clave in secciones_orden:
        story.append(Paragraph(titulo, styles['Titulo1']))
        story.append(Spacer(1, 0.2*inch))
        
        contenido = secciones.get(clave, '')
        if contenido and len(contenido) > 20:
            # Dividir en párrafos
            parrafos = contenido.split('<br/>')
            for parrafo in parrafos:
                if parrafo.strip():
                    story.append(Paragraph(parrafo.strip(), styles['TextoJustificado']))
                    story.append(Spacer(1, 0.1*inch))
        else:
            story.append(Paragraph("Contenido no disponible", styles['TextoJustificado']))
        
        story.append(PageBreak())
    
    # Construir PDF
    doc.build(story)
    file_size = os.path.getsize(filepath)
    logger.info(f"✅ PDF generado: {filename} ({file_size} bytes)")
    
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
        
        if not tema:
            return jsonify({'success': False, 'error': 'El tema es requerido'}), 400
        
        logger.info(f"📨 Generando informe para: {nombre} - Tema: {tema[:50]}...")
        
        # Generar con IA
        contenido_ia = generar_informe_con_ia(tema, info_extra)
        
        if contenido_ia:
            secciones = extraer_secciones(contenido_ia)
            logger.info("✅ Informe generado con IA correctamente")
        else:
            secciones = contenido_respaldo(tema)
            logger.warning("⚠️ Usando contenido de respaldo (IA falló)")
        
        datos_usuario = {
            'nombre': nombre,
            'tema': tema
        }
        
        filename, filepath = generar_pdf(datos_usuario, secciones)
        
        return jsonify({
            'success': True,
            'message': 'Informe generado exitosamente',
            'download_url': f'/descargar/{filename}'
        })
        
    except Exception as e:
        logger.error(f"❌ Error en /generar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/descargar/<filename>')
def descargar(filename):
    filepath = os.path.join('informes_generados', filename)
    
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'Archivo no encontrado'}), 404
    
    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'deepseek_configured': bool(DEEPSEEK_API_KEY),
        'timestamp': datetime.now().isoformat()
    })

# ============================================================
# INICIO DE LA APLICACIÓN
# ============================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Iniciando servidor en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
