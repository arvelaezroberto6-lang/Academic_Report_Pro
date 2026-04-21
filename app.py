from flask import Flask, render_template, request, jsonify, send_file
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os
import uuid
from datetime import datetime
import re
import requests
import html
import logging
from functools import wraps
import time

# Configuración de logging mejorado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB máximo
app.config['JSON_AS_ASCII'] = False

# Crear directorio para informes
os.makedirs('informes_generados', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# ========== CONFIGURACIÓN DE DEEPSEEK (reemplaza GROQ) ==========
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

logger.info("=" * 60)
logger.info("🚀 ACADEMIC REPORT PRO - VERSIÓN CON DEEPSEEK")
logger.info(f"🔑 DeepSeek API Key configurada: {'SÍ ✅' if DEEPSEEK_API_KEY else 'NO ❌'}")
logger.info(f"📁 Directorio de informes: {os.path.abspath('informes_generados')}")
logger.info("=" * 60)

# ========== CONFIGURACIÓN DE NORMAS ACADÉMICAS ==========
NORMAS_CONFIG = {
    'apa7': {
        'nombre': 'APA 7ª Edición',
        'descripcion': 'American Psychological Association - Séptima Edición',
        'margen_superior': 72,
        'margen_inferior': 72,
        'margen_izquierdo': 72,
        'margen_derecho': 72,
        'fuente': 'Times-Roman',
        'tamaño': 12,
        'interlineado': 24,
        'sangria': 36,
        'color_titulo': '#1a365d'
    },
    'apa6': {
        'nombre': 'APA 6ª Edición',
        'descripcion': 'American Psychological Association - Sexta Edición',
        'margen_superior': 72,
        'margen_inferior': 72,
        'margen_izquierdo': 72,
        'margen_derecho': 72,
        'fuente': 'Times-Roman',
        'tamaño': 12,
        'interlineado': 24,
        'sangria': 36,
        'color_titulo': '#1a365d'
    },
    'icontec': {
        'nombre': 'ICONTEC',
        'descripcion': 'Instituto Colombiano de Normas Técnicas',
        'margen_superior': 85,
        'margen_inferior': 85,
        'margen_izquierdo': 113,
        'margen_derecho': 85,
        'fuente': 'Helvetica',
        'tamaño': 12,
        'interlineado': 18,
        'sangria': 0,
        'color_titulo': '#2c5f2d'
    },
    'vancouver': {
        'nombre': 'Vancouver',
        'descripcion': 'Estilo Vancouver para ciencias de la salud',
        'margen_superior': 72,
        'margen_inferior': 72,
        'margen_izquierdo': 72,
        'margen_derecho': 72,
        'fuente': 'Times-Roman',
        'tamaño': 11,
        'interlineado': 16,
        'sangria': 0,
        'color_titulo': '#8b0000'
    },
    'chicago': {
        'nombre': 'Chicago',
        'descripcion': 'Manual de Estilo Chicago',
        'margen_superior': 72,
        'margen_inferior': 72,
        'margen_izquierdo': 72,
        'margen_derecho': 72,
        'fuente': 'Times-Roman',
        'tamaño': 12,
        'interlineado': 18,
        'sangria': 36,
        'color_titulo': '#8b4513'
    },
    'harvard': {
        'nombre': 'Harvard',
        'descripcion': 'Sistema de Referenciación Harvard',
        'margen_superior': 72,
        'margen_inferior': 72,
        'margen_izquierdo': 72,
        'margen_derecho': 72,
        'fuente': 'Times-Roman',
        'tamaño': 12,
        'interlineado': 18,
        'sangria': 36,
        'color_titulo': '#4b0082'
    },
    'mla': {
        'nombre': 'MLA 9ª Edición',
        'descripcion': 'Modern Language Association',
        'margen_superior': 72,
        'margen_inferior': 72,
        'margen_izquierdo': 72,
        'margen_derecho': 72,
        'fuente': 'Times-Roman',
        'tamaño': 12,
        'interlineado': 24,
        'sangria': 36,
        'color_titulo': '#191970'
    },
    'ieee': {
        'nombre': 'IEEE',
        'descripcion': 'Institute of Electrical and Electronics Engineers',
        'margen_superior': 72,
        'margen_inferior': 72,
        'margen_izquierdo': 72,
        'margen_derecho': 72,
        'fuente': 'Times-Roman',
        'tamaño': 10,
        'interlineado': 12,
        'sangria': 0,
        'color_titulo': '#003366'
    }
}

# ========== DECORADOR PARA MANEJAR ERRORES ==========
def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error en {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Error interno del servidor: {str(e)}'
            }), 500
    return decorated_function

# ========== FUNCIÓN MEJORADA DE LIMPIEZA DE TEXTO ==========
def limpiar_texto(texto):
    """Limpia y normaliza texto para ReportLab con manejo robusto de errores"""
    if not texto:
        return ""
    
    try:
        # Convertir bytes a string si es necesario
        if isinstance(texto, bytes):
            texto = texto.decode('utf-8', errors='ignore')
        
        # Escape HTML para seguridad
        texto = html.escape(texto)
        
        # Reemplazos de caracteres especiales
        reemplazos = {
            '\xa0': ' ',
            '\xad': '-',
            '\u2013': '-',
            '\u2014': '--',
            '\u2018': "'",
            '\u2019': "'",
            '\u201c': '"',
            '\u201d': '"',
            '\u2026': '...',
            '\u2022': '•',
            '\u00a9': '(c)',
            '\u00ae': '(R)',
            '\u2122': '(TM)',
        }
        
        for viejo, nuevo in reemplazos.items():
            texto = texto.replace(viejo, nuevo)
        
        # Normalizar saltos de línea múltiples
        texto = re.sub(r'\n{3,}', '<br/><br/>', texto)
        
        # Correcciones automáticas comunes
        correcciones = {
            'INFORMÉ': 'INFORME',
            'Conclusions': 'CONCLUSIONES',
            'CONCLUSIONS': 'CONCLUSIONES',
            'References': 'REFERENCIAS',
            'REFERENCES': 'REFERENCIAS',
        }
        
        for viejo, nuevo in correcciones.items():
            texto = texto.replace(viejo, nuevo)
        
        # Eliminar caracteres de control
        texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', texto)
        
        # Limpiar espacios múltiples
        texto = re.sub(r' {2,}', ' ', texto)
        
        return texto.strip()
        
    except Exception as e:
        logger.error(f"Error limpiando texto: {e}")
        return str(texto) if texto else ""

# ========== CONTENIDO GENÉRICO MEJORADO ==========
def contenido_local_generico(tema, tipo_informe="academico"):
    """Genera contenido genérico de respaldo más detallado"""
    tema_limpio = tema if tema else "el tema de investigación"
    fecha_actual = datetime.now().strftime('%Y')
    
    contenido_base = {
        'introduccion': f"""El presente informe académico tiene como propósito abordar el estudio integral de {tema_limpio}. 
        Este análisis se enmarca en un contexto contemporáneo donde la investigación rigurosa y metodológica 
        resulta fundamental para comprender la complejidad del tema en cuestión. 
        
        A lo largo de este documento se presentarán diversos aspectos relacionados con {tema_limpio}, 
        incluyendo su fundamentación teórica, metodología de análisis y principales hallazgos.""",
        
        'objetivos': f"""<b>Objetivo General</b><br/>
        Analizar de manera integral y sistemática {tema_limpio}, considerando sus múltiples dimensiones 
        y aplicaciones en el contexto actual.<br/><br/>
        
        <b>Objetivos Específicos</b><br/>
        1. Identificar y describir los factores clave que componen {tema_limpio}.<br/>
        2. Caracterizar las principales variables y elementos involucrados.<br/>
        3. Analizar las implicaciones teóricas y prácticas del estudio.<br/>
        4. Proponer recomendaciones basadas en evidencia para futuras investigaciones.<br/>
        5. Evaluar el impacto y relevancia del tema en el ámbito académico y profesional.""",
        
        'marco_teorico': f"""<b>Fundamentos Teóricos</b><br/>
        Para comprender adecuadamente {tema_limpio}, es necesario establecer un marco conceptual 
        que permita contextualizar el análisis. La literatura especializada ha desarrollado diversos 
        enfoques y perspectivas que enriquecen nuestra comprensión del fenómeno.<br/><br/>
        
        <b>Conceptos Fundamentales</b><br/>
        Los principales conceptos relacionados con {tema_limpio} incluyen elementos teóricos y 
        prácticos que han sido ampliamente estudiados por diversos autores en los últimos años.<br/><br/>
        
        <b>Estado del Arte</b><br/>
        Las investigaciones recientes demuestran un creciente interés en {tema_limpio}, 
        evidenciando su relevancia en el contexto académico y profesional actual.""",
        
        'metodologia': f"""<b>Enfoque Metodológico</b><br/>
        Para el desarrollo de esta investigación se ha adoptado un enfoque mixto que combina 
        elementos cualitativos y cuantitativos, permitiendo un análisis integral de {tema_limpio}.<br/><br/>
        
        <b>Diseño de la Investigación</b><br/>
        Tipo: Descriptivo-Analítico<br/>
        Enfoque: Mixto (Cualitativo-Cuantitativo)<br/>
        Alcance: Exploratorio y descriptivo<br/><br/>
        
        <b>Población y Muestra</b><br/>
        Población objetivo: Definida según criterios de inclusión específicos<br/>
        Muestra: 250 participantes seleccionados mediante muestreo probabilístico<br/>
        Margen de error: ±5% con 95% de confianza<br/><br/>
        
        <b>Técnicas de Recolección</b><br/>
        - Revisión documental y bibliográfica<br/>
        - Entrevistas estructuradas<br/>
        - Cuestionarios validados<br/>
        - Observación sistemática""",
        
        'desarrollo': f"""<b>Análisis de Resultados</b><br/>
        El análisis de los datos recopilados revela tendencias significativas en relación con {tema_limpio}. 
        Los hallazgos principales indican patrones consistentes que merecen atención detallada.<br/><br/>
        
        <b>Hallazgos Principales</b><br/>
        1. Se observa una correlación positiva entre las variables estudiadas.<br/>
        2. Los datos cualitativos complementan los hallazgos cuantitativos.<br/>
        3. Las tendencias identificadas son estadísticamente significativas (p < 0.05).<br/>
        4. Los resultados se alinean con investigaciones previas en el campo.<br/><br/>
        
        <b>Interpretación</b><br/>
        Los resultados obtenidos permiten comprender mejor las dinámicas relacionadas con {tema_limpio}, 
        ofreciendo perspectivas valiosas para futuras investigaciones y aplicaciones prácticas.""",
        
        'conclusiones': f"""1. {tema_limpio} demuestra ser un área de estudio relevante y necesaria 
        en el contexto académico actual, con implicaciones significativas para la teoría y la práctica.<br/><br/>
        
        2. Los hallazgos de esta investigación proporcionan evidencia empírica que respalda 
        la importancia de continuar profundizando en el estudio de {tema_limpio}.<br/><br/>
        
        3. Se identificaron oportunidades de investigación futura que pueden contribuir 
        al desarrollo del conocimiento en esta área específica.<br/><br/>
        
        4. Las metodologías empleadas demostraron ser efectivas para abordar los objetivos 
        planteados, generando resultados confiables y válidos.<br/><br/>
        
        5. Los resultados obtenidos tienen potencial de aplicación práctica en diversos 
        contextos profesionales y académicos.""",
        
        'recomendaciones': f"""1. <b>Para futuras investigaciones:</b> Se recomienda ampliar el alcance 
        del estudio incorporando variables adicionales y aumentando el tamaño de la muestra 
        para fortalecer la generalización de los hallazgos.<br/><br/>
        
        2. <b>Para la práctica profesional:</b> Implementar los hallazgos de esta investigación 
        en contextos reales, evaluando su efectividad y realizando ajustes según sea necesario.<br/><br/>
        
        3. <b>Para el ámbito académico:</b> Desarrollar programas de formación que integren 
        los conocimientos generados sobre {tema_limpio}, promoviendo una comprensión 
        más profunda del tema.<br/><br/>
        
        4. <b>Para stakeholders:</b> Establecer mecanismos de difusión que permitan compartir 
        los resultados con comunidades interesadas, fomentando el diálogo y la colaboración.""",
        
        'referencias': f"""1. Hernández Sampieri, R., Fernández Collado, C., & Baptista Lucio, P. ({fecha_actual}). 
        Metodología de la Investigación (7ª ed.). McGraw-Hill Interamericana.<br/><br/>
        
        2. Bisquerra Alzina, R. (2016). Metodología de la investigación educativa (5ª ed.). La Muralla.<br/><br/>
        
        3. Arias, F. G. (2012). El proyecto de investigación: Introducción a la metodología 
        científica (6ª ed.). Episteme.<br/><br/>
        
        4. Sabino, C. (2014). El proceso de investigación. Episteme.<br/><br/>
        
        5. Bernal Torres, C. A. (2010). Metodología de la investigación (3ª ed.). Pearson Educación.<br/><br/>
        
        6. Tamayo y Tamayo, M. (2012). El proceso de la investigación científica (5ª ed.). Limusa."""
    }
    
    return contenido_base

# ========== EXTRACCIÓN DE SECCIONES MEJORADA ==========
def extraer_seccion(contenido, nombre):
    """Extrae secciones del contenido generado con múltiples patrones de respaldo"""
    if not contenido or not nombre:
        return ""
    
    # Intentar múltiples patrones
    patrones = [
        rf'\*\*{nombre}\*\*:?(.*?)(?=\*\*[A-Z]|REFERENCIAS|CONCLUSIONES|RECOMENDACIONES|$)',
        rf'{nombre}:?(.*?)(?=\n\n[A-Z]|REFERENCIAS|CONCLUSIONES|RECOMENDACIONES|$)',
        rf'##\s*{nombre}\s*(.*?)(?=##|$)',
    ]
    
    for patron in patrones:
        match = re.search(patron, contenido, re.DOTALL | re.IGNORECASE)
        if match:
            texto = match.group(1).strip()
            # Convertir markdown a HTML básico
            texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
            texto = re.sub(r'\*(.*?)\*', r'<i>\1</i>', texto)
            texto = re.sub(r'```(.*?)```', r'<pre>\1</pre>', texto, flags=re.DOTALL)
            
            # Limpiar y retornar
            if len(texto) > 20:  # Asegurar que tenga contenido sustancial
                return limpiar_texto(texto)
    
    return ""

# ========== GENERACIÓN CON DEEPSEEK (reemplaza Groq) ==========
def generar_informe_con_ia(tema, tipo_informe="academico", info_extra="", norma="apa7"):
    """Genera informe usando DeepSeek API (estable y económico)"""
    
    if not DEEPSEEK_API_KEY:
        logger.warning("❌ No hay API key de DeepSeek configurada, usando contenido genérico")
        return None

    logger.info(f"🤖 Generando informe con DeepSeek - tipo '{tipo_informe}' sobre: {tema[:80]}...")
    
    # Construir prompt según tipo de informe
    prompts = {
        "laboratorio": f"""Genera un INFORME DE LABORATORIO completo, profesional y detallado sobre: "{tema}"

Información adicional del usuario: {info_extra if info_extra else 'No se proporcionaron datos específicos'}

⚠️ ESTRUCTURA OBLIGATORIA (debe seguirse exactamente):

**1. INTRODUCCIÓN**
- Objetivo del experimento (2-3 párrafos)
- Fundamento teórico detallado
- Hipótesis planteada

**2. MATERIALES Y REACTIVOS**
- Lista completa de materiales de laboratorio
- Reactivos químicos utilizados con concentraciones
- Equipos e instrumentos de medición

**3. PROCEDIMIENTO EXPERIMENTAL**
- Descripción paso a paso (mínimo 8 pasos)
- Precauciones de seguridad
- Controles positivos y negativos
- Tiempo y temperatura de cada etapa

**4. RESULTADOS**
- Tabla de resultados observados
- Datos cuantitativos (si aplica)
- Fotografías o esquemas descriptivos (mencionar)

**5. DISCUSIÓN**
- Análisis detallado de resultados
- Comparación con valores teóricos
- Explicación de reacciones químicas o procesos
- Errores y factores que afectaron resultados

**6. CONCLUSIONES**
- Mínimo 5 conclusiones específicas y numeradas
- Relacionar con los objetivos planteados
- Validación o rechazo de hipótesis

**7. RECOMENDACIONES**
- 3-4 sugerencias para mejorar el experimento
- Aplicaciones prácticas

**8. REFERENCIAS**
- 5-6 fuentes bibliográficas en formato {NORMAS_CONFIG.get(norma, NORMAS_CONFIG['apa7'])['nombre']}

IMPORTANTE: Escribe en español con tono técnico-profesional. Usa **negritas** para títulos y subtítulos.""",

        "empresarial": f"""Genera un INFORME EJECUTIVO completo y profesional sobre: "{tema}"

Contexto adicional: {info_extra if info_extra else 'Sin información adicional'}

**ESTRUCTURA OBLIGATORIA:**

**RESUMEN EJECUTIVO**
- Síntesis de hallazgos clave (1 página)
- Recomendaciones principales

**1. INTRODUCCIÓN**
- Contexto empresarial
- Propósito del informe
- Alcance y limitaciones

**2. ANÁLISIS DE SITUACIÓN**
- Análisis FODA (Fortalezas, Oportunidades, Debilidades, Amenazas)
- Análisis de mercado
- Análisis de competencia
- Indicadores clave de desempeño (KPIs)

**3. OPORTUNIDADES Y AMENAZAS**
- Identificación de oportunidades de negocio
- Riesgos y amenazas potenciales
- Análisis de tendencias del sector

**4. RECOMENDACIONES ESTRATÉGICAS**
- Estrategias a corto plazo (0-6 meses)
- Estrategias a mediano plazo (6-12 meses)
- Estrategias a largo plazo (1-3 años)
- Plan de implementación

**5. PROYECCIONES FINANCIERAS**
- Estimaciones de inversión
- Retorno de inversión esperado (ROI)
- Análisis costo-beneficio

**6. CONCLUSIONES**
- 5 conclusiones principales
- Próximos pasos

**7. REFERENCIAS**
- Fuentes consultadas en formato {NORMAS_CONFIG.get(norma, NORMAS_CONFIG['apa7'])['nombre']}

Escribe en español con tono ejecutivo profesional.""",

        "tesis": f"""Genera una estructura completa de TESIS/MONOGRAFÍA sobre: "{tema}"

Información adicional: {info_extra if info_extra else 'Sin información adicional'}

**ESTRUCTURA OBLIGATORIA:**

**RESUMEN**
- Abstract en español (250 palabras)
- Palabras clave (5-7 términos)

**1. INTRODUCCIÓN**
- Contextualización del tema
- Justificación de la investigación
- Antecedentes relevantes

**2. PLANTEAMIENTO DEL PROBLEMA**
- Descripción del problema
- Formulación del problema (pregunta de investigación)
- Delimitación espacial y temporal

**3. OBJETIVOS**
- Objetivo general (1)
- Objetivos específicos (4-5)

**4. HIPÓTESIS**
- Hipótesis general
- Hipótesis específicas
- Variables: dependientes e independientes

**5. MARCO TEÓRICO**
- Bases teóricas fundamentales
- Teorías relacionadas
- Definición de términos básicos
- Marco conceptual

**6. METODOLOGÍA**
- Tipo y diseño de investigación
- Población y muestra
- Técnicas e instrumentos de recolección
- Procedimiento de investigación
- Análisis de datos

**7. RESULTADOS ESPERADOS**
- Descripción de resultados anticipados
- Posibles hallazgos
- Limitaciones del estudio

**8. CRONOGRAMA**
- Fases de la investigación
- Tiempos estimados

**9. PRESUPUESTO**
- Recursos humanos
- Recursos materiales
- Costos estimados

**10. CONCLUSIONES PRELIMINARES**
- 5 conclusiones basadas en el marco teórico

**11. REFERENCIAS**
- Mínimo 15 fuentes en formato {NORMAS_CONFIG.get(norma, NORMAS_CONFIG['apa7'])['nombre']}

Escribe en español académico formal."""
    }
    
    # Prompt por defecto (académico)
    prompt_default = f"""Genera un INFORME ACADÉMICO completo, riguroso y profesional sobre: "{tema}"

Información adicional proporcionada: {info_extra if info_extra else 'Sin información adicional'}

**ESTRUCTURA OBLIGATORIA:**

**INTRODUCCIÓN**
- Contextualización del tema (2-3 párrafos)
- Justificación e importancia
- Planteamiento inicial

**OBJETIVOS**
- 1 objetivo general claro y específico
- 4-5 objetivos específicos medibles

**MARCO TEÓRICO**
- Fundamentos teóricos detallados
- Conceptos clave explicados
- Antecedentes y estado del arte
- Teorías relacionadas

**METODOLOGÍA**
- Tipo de investigación y diseño
- Población y muestra (con números específicos)
- Técnicas de recolección de datos
- Procedimiento detallado
- Análisis de datos

**DESARROLLO**
- Presentación de resultados con datos
- Análisis e interpretación
- Tablas o gráficos (describir en texto)
- Discusión de hallazgos

**CONCLUSIONES**
- Mínimo 5 conclusiones específicas y numeradas
- Relacionadas con los objetivos
- Basadas en evidencia del desarrollo

**RECOMENDACIONES**
- 3-4 recomendaciones prácticas y específicas
- Para investigadores futuros
- Para aplicación práctica

**REFERENCIAS**
- 6-8 fuentes bibliográficas académicas
- Formato: {NORMAS_CONFIG.get(norma, NORMAS_CONFIG['apa7'])['nombre']}
- Incluir libros, artículos y fuentes digitales

REQUISITOS:
- Escribe en español académico formal
- Usa **negritas** para todos los títulos y subtítulos
- Proporciona contenido sustancial (no solo títulos)
- Incluye datos específicos cuando sea posible
- Mantén coherencia y cohesión entre secciones"""

    prompt = prompts.get(tipo_informe, prompt_default)
    
    # Headers para DeepSeek
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",  # DeepSeek V3.2
        "messages": [
            {
                "role": "system",
                "content": "Eres un asistente académico experto en redactar informes profesionales. Generas contenido detallado, riguroso y bien estructurado en español."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 6000,
        "temperature": 0.7,
        "top_p": 0.9
    }
    
    try:
        logger.info("📡 Enviando solicitud a DeepSeek API...")
        response = requests.post(
            DEEPSEEK_URL,
            headers=headers,
            json=data,
            timeout=120
        )
        
        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado['choices'][0]['message']['content']
            contenido = limpiar_texto(contenido)
            
            logger.info(f"✅ Contenido generado exitosamente ({len(contenido)} caracteres)")
            
            # Extraer secciones según tipo de informe
            if tipo_informe == "laboratorio":
                secciones = {
                    'introduccion': extraer_seccion(contenido, '1. INTRODUCCIÓN') or extraer_seccion(contenido, 'INTRODUCCIÓN'),
                    'materiales': extraer_seccion(contenido, '2. MATERIALES Y REACTIVOS') or extraer_seccion(contenido, 'MATERIALES'),
                    'procedimiento': extraer_seccion(contenido, '3. PROCEDIMIENTO EXPERIMENTAL') or extraer_seccion(contenido, 'PROCEDIMIENTO'),
                    'resultados': extraer_seccion(contenido, '4. RESULTADOS'),
                    'discusion': extraer_seccion(contenido, '5. DISCUSIÓN') or extraer_seccion(contenido, 'DISCUSIÓN'),
                    'conclusiones': extraer_seccion(contenido, '6. CONCLUSIONES') or extraer_seccion(contenido, 'CONCLUSIONES'),
                    'recomendaciones': extraer_seccion(contenido, '7. RECOMENDACIONES') or extraer_seccion(contenido, 'RECOMENDACIONES'),
                    'referencias': extraer_seccion(contenido, '8. REFERENCIAS') or extraer_seccion(contenido, 'REFERENCIAS')
                }
            else:
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
            
            # Validar y completar secciones vacías
            contenido_respaldo = contenido_local_generico(tema, tipo_informe)
            for key in secciones:
                if not secciones[key] or len(secciones[key]) < 50:
                    logger.warning(f"⚠️ Sección '{key}' vacía o muy corta, usando contenido genérico")
                    secciones[key] = contenido_respaldo.get(key, "")
            
            logger.info(f"✅ Informe tipo '{tipo_informe}' generado correctamente con DeepSeek")
            return secciones
            
        else:
            logger.error(f"❌ Error con DeepSeek: HTTP {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("⏱️ Timeout: DeepSeek tardó más de 120 segundos")
        return None
    except Exception as e:
        logger.error(f"❌ Error con DeepSeek: {str(e)}")
        return None

# ========== GENERADOR DE PDF MEJORADO ==========
class GeneradorPDF:
    """Clase mejorada para generar PDFs profesionales"""
    
    def crear_estilos(self, config_norma):
        """Crea estilos personalizados según la norma académica"""
        styles = getSampleStyleSheet()
        
        # Estilo para texto justificado
        styles.add(ParagraphStyle(
            name='TextoJustificado',
            parent=styles['Normal'],
            alignment=TA_JUSTIFY,
            fontSize=config_norma['tamaño'],
            fontName=config_norma['fuente'],
            spaceAfter=12,
            spaceBefore=6,
            leading=config_norma['interlineado'],
            leftIndent=config_norma['sangria']
        ))
        
        # Estilo para títulos principales
        styles.add(ParagraphStyle(
            name='Titulo1',
            parent=styles['Heading1'],
            fontSize=config_norma['tamaño'] + 4,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor(config_norma.get('color_titulo', '#1a365d')),
            spaceBefore=24,
            spaceAfter=16,
            alignment=TA_LEFT
        ))
        
        # Estilo para subtítulos
        styles.add(ParagraphStyle(
            name='Titulo2',
            parent=styles['Heading2'],
            fontSize=config_norma['tamaño'] + 2,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor(config_norma.get('color_titulo', '#1a365d')),
            spaceBefore=18,
            spaceAfter=12,
            alignment=TA_LEFT
        ))
        
        # Estilo para portada
        styles.add(ParagraphStyle(
            name='TituloPortada',
            parent=styles['Title'],
            fontSize=24,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor(config_norma.get('color_titulo', '#1a365d'))
        ))
        
        # Estilo para texto centrado
        styles.add(ParagraphStyle(
            name='TextoCentrado',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=config_norma['tamaño'],
            fontName=config_norma['fuente'],
            spaceAfter=10
        ))
        
        return styles
    
    def generar_pdf(self, datos_usuario, secciones):
        """Genera el archivo PDF completo"""
        
        # Extraer y validar datos
        nombre = datos_usuario.get('nombre', 'Estudiante') or "Estudiante"
        otros_autores = datos_usuario.get('otros_autores', '')
        tema = datos_usuario.get('tema', 'Tema de Investigación') or "Tema de Investigación"
        asignatura = datos_usuario.get('asignatura', 'Asignatura') or "Asignatura"
        profesor = datos_usuario.get('profesor', 'Docente') or "Docente"
        institucion = datos_usuario.get('institucion', 'Institución Educativa') or "Institución Educativa"
        fecha_entrega = datos_usuario.get('fecha_entrega', datetime.now().strftime('%d/%m/%Y'))
        tipo_informe = datos_usuario.get('tipo_informe', 'academico')
        norma = datos_usuario.get('norma', 'apa7')
        
        # Obtener configuración de norma
        config_norma = NORMAS_CONFIG.get(norma, NORMAS_CONFIG['apa7'])
        
        # Generar nombre único para el archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:6]
        filename = f"informe_{tipo_informe}_{timestamp}_{unique_id}.pdf"
        filepath = os.path.join('informes_generados', filename)
        
        # Crear estilos
        styles = self.crear_estilos(config_norma)
        
        # Crear documento
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=config_norma['margen_derecho'],
            leftMargin=config_norma['margen_izquierdo'],
            topMargin=config_norma['margen_superior'],
            bottomMargin=config_norma['margen_inferior'],
            title=tema,
            author=nombre
        )
        
        story = []
        
        # ========== PORTADA ==========
        story.append(Spacer(1, 1.5*inch))
        story.append(Paragraph("INFORME ACADÉMICO", styles['TituloPortada']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(tema.upper(), styles['TextoCentrado']))
        story.append(Spacer(1, 1.5*inch))
        
        # Información del autor
        story.append(Paragraph(f"<b>Presentado por:</b> {nombre}", styles['TextoCentrado']))
        
        if otros_autores:
            if isinstance(otros_autores, list):
                otros_autores = ", ".join(otros_autores)
            story.append(Paragraph(f"<b>Colaboradores:</b> {otros_autores}", styles['TextoCentrado']))
        
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(f"<b>Asignatura:</b> {asignatura}", styles['TextoCentrado']))
        story.append(Paragraph(f"<b>Docente:</b> {profesor}", styles['TextoCentrado']))
        story.append(Paragraph(f"<b>Institución:</b> {institucion}", styles['TextoCentrado']))
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(f"<b>Fecha de entrega:</b> {fecha_entrega}", styles['TextoCentrado']))
        story.append(Paragraph(f"<b>Norma aplicada:</b> {config_norma['nombre']}", styles['TextoCentrado']))
        
        story.append(PageBreak())
        
        # ========== ÍNDICE ==========
        story.append(Paragraph("ÍNDICE", styles['Titulo1']))
        story.append(Spacer(1, 0.2*inch))
        
        indices = [
            "1. INTRODUCCIÓN",
            "2. OBJETIVOS",
            "3. MARCO TEÓRICO",
            "4. METODOLOGÍA",
            "5. DESARROLLO",
            "6. CONCLUSIONES",
            "7. RECOMENDACIONES",
            "8. REFERENCIAS"
        ]
        
        for idx in indices:
            story.append(Paragraph(f"• {idx}", styles['TextoJustificado']))
            story.append(Spacer(1, 0.1*inch))
        
        story.append(PageBreak())
        
        # ========== SECCIONES DEL CONTENIDO ==========
        secciones_estructura = [
            ("1. INTRODUCCIÓN", 'introduccion'),
            ("2. OBJETIVOS", 'objetivos'),
            ("3. MARCO TEÓRICO", 'marco_teorico'),
            ("4. METODOLOGÍA", 'metodologia'),
            ("5. DESARROLLO", 'desarrollo'),
            ("6. CONCLUSIONES", 'conclusiones'),
            ("7. RECOMENDACIONES", 'recomendaciones'),
            ("8. REFERENCIAS", 'referencias')
        ]
        
        for titulo, clave in secciones_estructura:
            story.append(Paragraph(titulo, styles['Titulo1']))
            story.append(Spacer(1, 0.2*inch))
            
            contenido = secciones.get(clave, '')
            if contenido:
                # Dividir en párrafos si es necesario
                parrafos = contenido.split('<br/><br/>')
                for parrafo in parrafos:
                    if parrafo.strip():
                        story.append(Paragraph(parrafo.strip(), styles['TextoJustificado']))
                        story.append(Spacer(1, 0.1*inch))
            else:
                story.append(Paragraph(f"Contenido no disponible para {titulo}", styles['TextoJustificado']))
            
            story.append(PageBreak())
        
        # Construir PDF
        try:
            doc.build(story)
            file_size = os.path.getsize(filepath)
            logger.info(f"✅ PDF generado: {filename} ({file_size} bytes)")
            return filename, filepath
        except Exception as e:
            logger.error(f"❌ Error generando PDF: {e}")
            raise

# Instancia global del generador
generador = GeneradorPDF()

# ========== RUTAS DE LA API ==========

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Endpoint de health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'deepseek_configured': bool(DEEPSEEK_API_KEY)
    })

@app.route('/api/normas')
def get_normas():
    """Obtiene lista de normas disponibles"""
    return jsonify({
        'success': True,
        'normas': NORMAS_CONFIG
    })

@app.route('/generar', methods=['POST'])
@handle_errors
def generar():
    """Endpoint principal para generar informes"""
    
    datos = request.json
    if not datos:
        return jsonify({
            'success': False,
            'error': 'No se recibieron datos'
        }), 400
    
    # Validar campos requeridos
    tema = datos.get('tema', '').strip()
    if not tema or len(tema) < 3:
        return jsonify({
            'success': False,
            'error': 'El tema debe tener al menos 3 caracteres'
        }), 400
    
    nombre = datos.get('nombre', '').strip()
    if not nombre:
        return jsonify({
            'success': False,
            'error': 'El nombre del autor es requerido'
        }), 400
    
    # Extraer datos
    texto_auto = datos.get('texto_completo', '')
    tipo_informe = datos.get('tipo_informe', 'academico')
    norma = datos.get('norma', 'apa7')
    
    logger.info(f"📨 Solicitud de informe: tipo={tipo_informe}, norma={norma}, tema={tema[:60]}...")
    
    # Generar con IA
    secciones = generar_informe_con_ia(tema, tipo_informe, texto_auto, norma)
    
    # Si falla IA, usar contenido genérico
    if not secciones:
        logger.warning("⚠️ Generación con IA falló, usando contenido genérico")
        secciones = contenido_local_generico(tema, tipo_informe)
    
    # Procesar autores múltiples
    otros_autores = datos.get('otros_autores', '')
    if otros_autores and isinstance(otros_autores, list):
        otros_autores = ", ".join(otros_autores)
    
    # Preparar datos de usuario
    datos_usuario = {
        'nombre': nombre,
        'otros_autores': otros_autores,
        'tema': tema,
        'asignatura': datos.get('asignatura', ''),
        'profesor': datos.get('profesor', ''),
        'institucion': datos.get('institucion', ''),
        'fecha_entrega': datos.get('fecha_entrega', ''),
        'tipo_informe': tipo_informe,
        'norma': norma
    }
    
    # Generar PDF
    try:
        filename, filepath = generador.generar_pdf(datos_usuario, secciones)
        
        return jsonify({
            'success': True,
            'message': 'Informe generado exitosamente',
            'filename': filename,
            'download_url': f'/descargar/{filename}',
            'metadata': {
                'tipo': tipo_informe,
                'norma': NORMAS_CONFIG.get(norma, {}).get('nombre', norma),
                'fecha_generacion': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"❌ Error generando PDF: {e}")
        return jsonify({
            'success': False,
            'error': f'Error al generar PDF: {str(e)}'
        }), 500

@app.route('/descargar/<filename>')
def descargar(filename):
    """Descarga un archivo PDF generado"""
    filepath = os.path.join('informes_generados', filename)
    
    if not os.path.exists(filepath):
        return jsonify({
            'success': False,
            'error': 'Archivo no encontrado'
        }), 404
    
    try:
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        logger.error(f"❌ Error descargando archivo: {e}")
        return jsonify({
            'success': False,
            'error': 'Error al descargar el archivo'
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Ruta no encontrada'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Error interno del servidor'
    }), 500

# ========== INICIO DE LA APLICACIÓN ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🚀 Iniciando servidor en puerto {port}")
    logger.info(f"🔧 Modo debug: {debug}")
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port,
        threaded=True
    )
