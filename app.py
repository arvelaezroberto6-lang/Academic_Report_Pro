from flask import Flask, render_template, request, jsonify, send_file
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os
import uuid
from datetime import datetime
import re
import requests

app = Flask(__name__)
os.makedirs("informes_generados", exist_ok=True)

# ========== CONFIGURACIÓN ==========
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

print("=" * 50)
print("🚀 ACADEMIC REPORT PRO - VERSIÓN PROFESIONAL")
print(f"🔑 IA: {'ACTIVADA ✅' if GROQ_API_KEY else 'DESACTIVADA ❌'}")
print("=" * 50)

# ========== NORMAS ACADÉMICAS ==========
NORMAS_CONFIG = {
    "apa7": {
        "nombre": "APA 7ª Edición",
        "margen_superior": 72,
        "margen_inferior": 72,
        "margen_izquierdo": 72,
        "margen_derecho": 72,
        "fuente": "Times-Roman",
        "tamaño": 12,
        "interlineado": 24,
        "sangria": 36,
    },
    "apa6": {
        "nombre": "APA 6ª Edición",
        "margen_superior": 72,
        "margen_inferior": 72,
        "margen_izquierdo": 72,
        "margen_derecho": 72,
        "fuente": "Times-Roman",
        "tamaño": 12,
        "interlineado": 24,
        "sangria": 36,
    },
    "icontec": {
        "nombre": "ICONTEC (Colombia)",
        "margen_superior": 85,
        "margen_inferior": 85,
        "margen_izquierdo": 113,
        "margen_derecho": 85,
        "fuente": "Helvetica",
        "tamaño": 12,
        "interlineado": 18,
        "sangria": 0,
    },
    "vancouver": {
        "nombre": "Vancouver",
        "margen_superior": 72,
        "margen_inferior": 72,
        "margen_izquierdo": 72,
        "margen_derecho": 72,
        "fuente": "Times-Roman",
        "tamaño": 11,
        "interlineado": 16,
        "sangria": 0,
    },
    "chicago": {
        "nombre": "Chicago",
        "margen_superior": 72,
        "margen_inferior": 72,
        "margen_izquierdo": 72,
        "margen_derecho": 72,
        "fuente": "Times-Roman",
        "tamaño": 12,
        "interlineado": 18,
        "sangria": 36,
    },
    "harvard": {
        "nombre": "Harvard",
        "margen_superior": 72,
        "margen_inferior": 72,
        "margen_izquierdo": 72,
        "margen_derecho": 72,
        "fuente": "Times-Roman",
        "tamaño": 12,
        "interlineado": 18,
        "sangria": 36,
    },
    "mla": {
        "nombre": "MLA 9ª Edición",
        "margen_superior": 72,
        "margen_inferior": 72,
        "margen_izquierdo": 72,
        "margen_derecho": 72,
        "fuente": "Times-Roman",
        "tamaño": 12,
        "interlineado": 24,
        "sangria": 36,
    },
    "ieee": {
        "nombre": "IEEE",
        "margen_superior": 72,
        "margen_inferior": 72,
        "margen_izquierdo": 72,
        "margen_derecho": 72,
        "fuente": "Times-Roman",
        "tamaño": 10,
        "interlineado": 12,
        "sangria": 0,
    },
}


def limpiar_texto(texto):
    """Limpia caracteres especiales y corrige errores comunes"""
    if not texto:
        return ""

    # Eliminar caracteres no imprimibles (CORRECCIÓN: regex correcto)
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", texto)

    # CORRECCIONES CRÍTICAS
    texto = texto.replace("INFORMÉ", "INFORME")
    texto = texto.replace("informé", "informe")
    texto = texto.replace("Conclusions", "CONCLUSIONES")
    texto = texto.replace("CONCLUSIONS", "CONCLUSIONES")

    # Eliminar espacios excesivos (CORRECCIÓN: evitar destruir saltos de línea)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    texto = re.sub(r"[ \t]{2,}", " ", texto)

    return texto.strip()


def contenido_local_generico(tema):
    """Contenido de respaldo GENÉRICO (sin referencias de temas específicos)"""
    tema_limpio = tema if tema else "el tema de investigación"

    return {
        "introduccion": f"El presente informe académico aborda el estudio de {tema_limpio}, una temática de creciente relevancia en el contexto actual. La investigación se justifica por la necesidad de generar evidencia empírica que contribuya al conocimiento existente.",
        "objetivos": f"<b>Objetivo General</b><br/><br/>Analizar los principales aspectos relacionados con {tema_limpio} en el contexto actual.<br/><br/><b>Objetivos Específicos</b><br/><br/>1. Identificar los factores clave asociados a {tema_limpio}.<br/><br/>2. Describir las principales características y tendencias actuales.<br/><br/>3. Analizar las implicaciones prácticas y teóricas de los hallazgos.<br/><br/>4. Proponer recomendaciones basadas en el análisis realizado.",
        "marco_teorico": f"<b>Conceptos clave</b><br/><br/>Para comprender adecuadamente {tema_limpio}, es necesario definir los conceptos fundamentales que lo sustentan. Las teorías existentes proporcionan un marco conceptual sólido para el análisis de esta temática. Investigaciones recientes han profundizado en aspectos específicos, identificando tendencias y áreas de oportunidad.",
        "metodologia": f"<b>Enfoque</b><br/><br/>La investigación adopta un enfoque mixto, combinando elementos cualitativos y cuantitativos.<br/><br/><b>Población y muestra</b><br/><br/>Se seleccionó una muestra representativa de 250 participantes, utilizando técnicas de muestreo estratificado.<br/><br/><b>Instrumentos</b><br/><br/>Cuestionarios estructurados, entrevistas semiestructuradas y revisión documental.<br/><br/><b>Procedimiento</b><br/><br/>El estudio se desarrolló en tres fases: diseño y validación de instrumentos, recolección de datos, y análisis e interpretación de resultados.",
        "desarrollo": f"<b>Resultados obtenidos</b><br/><br/>Los resultados del análisis muestran tendencias significativas relacionadas con {tema_limpio}. Los datos recopilados permiten identificar patrones y relaciones relevantes.<br/><br/><b>Análisis de resultados</b><br/><br/>Los hallazgos indican que existen múltiples factores que inciden en {tema_limpio}. Se observan variaciones según el contexto y las condiciones específicas de cada caso.<br/><br/><b>Discusión</b><br/><br/>Los resultados se alinean parcialmente con lo reportado en la literatura especializada, confirmando hallazgos previos y aportando nuevas perspectivas al conocimiento existente.",
        "conclusiones": f"1. {tema_limpio} es un tema de gran relevancia en el contexto actual.<br/><br/>2. Los hallazgos confirman la importancia de abordar este tema desde una perspectiva integral.<br/><br/>3. Se requiere mayor investigación para profundizar en aspectos específicos no cubiertos en este estudio.<br/><br/>4. Las recomendaciones propuestas constituyen una base para futuras intervenciones.<br/><br/>5. Este estudio contribuye al conocimiento existente y abre líneas de investigación adicionales.",
        "recomendaciones": f"<b>Recomendaciones</b><br/><br/>1. Fortalecer las líneas de investigación relacionadas con {tema_limpio}.<br/><br/>2. Aplicar los hallazgos en contextos prácticos relevantes.<br/><br/>3. Ampliar la muestra y el alcance geográfico para generalizar los resultados.",
        # CORRECCIÓN: incluir referencias para evitar KeyError al rellenar si IA falla
        "referencias": "No se proporcionaron referencias.",
    }


def generar_informe_con_ia(tema):
    """Genera el informe completo usando IA"""

    if not GROQ_API_KEY:
        print("❌ No hay API key configurada")
        return None

    print(f"🤖 Generando informe con IA para: {tema[:50]}...")

    prompt = f"""Genera un informe académico completo y profesional sobre: "{tema}"

⚠️ INSTRUCCIONES ESTRICTAS:
1. El título del informe debe ser "INFORME ACADÉMICO" (sin tilde en INFORME)
2. Usa "CONCLUSIONES" (nunca "Conclusions")
3. Las referencias deben ser COHERENTES con el tema "{tema}"
4. NO uses referencias de otros temas (café, cambio climático, etc.)

Escribe estas secciones:

**INTRODUCCIÓN** (Contexto, problema, justificación - 3 párrafos)

**OBJETIVOS**
**Objetivo General:** (1)
**Objetivos Específicos:** (4)

**MARCO TEÓRICO** (Conceptos clave, autores relevantes, citas)

**METODOLOGÍA** (Enfoque, muestra con números concretos, instrumentos, procedimiento)

**DESARROLLO** (Resultados con porcentajes, análisis detallado, discusión)

**CONCLUSIONES** (5 puntos)

**RECOMENDACIONES** (3-4 puntos)

**REFERENCIAS** (5-6 fuentes reales y coherentes con el tema)

Escribe TODO en español. Cada sección debe ser extensa y con contenido específico sobre el tema."""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 5000,
    }

    try:
        # CORRECCIÓN: requests.post válido, sin markdown
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=90,
        )

        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado["choices"][0]["message"]["content"]
            contenido = limpiar_texto(contenido)

            # Extraer secciones
            secciones = {
                "introduccion": extraer_seccion(contenido, "INTRODUCCIÓN"),
                "objetivos": extraer_seccion(contenido, "OBJETIVOS"),
                "marco_teorico": extraer_seccion(contenido, "MARCO TEÓRICO"),
                "metodologia": extraer_seccion(contenido, "METODOLOGÍA"),
                "desarrollo": extraer_seccion(contenido, "DESARROLLO"),
                "conclusiones": extraer_seccion(contenido, "CONCLUSIONES"),
                "recomendaciones": extraer_seccion(contenido, "RECOMENDACIONES"),
                "referencias": extraer_seccion(contenido, "REFERENCIAS"),
            }

            # Rellenar secciones vacías
            for key in secciones:
                if not secciones[key] or len(secciones[key]) < 100:
                    print(f"⚠️ Sección {key} incompleta, usando contenido local")
                    # CORRECCIÓN: evitar KeyError si una clave no existe
                    secciones[key] = contenido_local_generico(tema).get(key, "")

            return secciones
        else:
            print(f"❌ Error IA: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def extraer_seccion(contenido, nombre):
    # CORRECCIÓN: patrón más robusto para secciones Markdown tipo **TITULO**
    # Mantiene la intención original: extraer entre encabezados de secciones
    patron = rf"\*\*{re.escape(nombre)}\*\*\s*:?(.*?)(?=\n\s*\*\*[A-ZÁÉÍÓÚÑ ]+\*\*|\Z)"
    # CORRECCIÓN: re.search válido, sin markdown
    match = re.search(patron, contenido, re.DOTALL | re.IGNORECASE)
    if match:
        # CORRECCIÓN: match.group válido, sin markdown
        texto = match.group(1).strip()
        texto = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", texto)
        return texto
    return ""


# ========== GENERADOR DE PDF ==========
class GeneradorPDF:
    def crear_estilos(self, config_norma):
        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(
                name="TextoJustificado",
                parent=styles["Normal"],
                alignment=TA_JUSTIFY,
                fontSize=config_norma["tamaño"],
                fontName=config_norma["fuente"],
                spaceAfter=12,
                leading=config_norma["interlineado"],
                leftIndent=config_norma["sangria"],
            )
        )
        styles.add(
            ParagraphStyle(
                name="Titulo1",
                parent=styles["Heading1"],
                fontSize=config_norma["tamaño"] + 2,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor("#1a365d"),
                spaceBefore=24,
                spaceAfter=16,
            )
        )
        styles.add(
            ParagraphStyle(
                name="TituloPortada",
                parent=styles["Title"],
                fontSize=22,
                alignment=TA_CENTER,
                spaceAfter=20,
                textColor=colors.HexColor("#1a365d"),
            )
        )
        return styles

    def generar_pdf(self, datos_usuario, secciones):
        nombre = datos_usuario.get("nombre", "Estudiante") or "Estudiante"
        tema = (
            datos_usuario.get("tema", "Tema de Investigación")
            or "Tema de Investigación"
        )
        asignatura = datos_usuario.get("asignatura", "Asignatura") or "Asignatura"
        profesor = datos_usuario.get("profesor", "Docente") or "Docente"
        institucion = (
            datos_usuario.get("institucion", "Institución Educativa")
            or "Institución Educativa"
        )
        # CORRECCIÓN: datetime.now válido, sin markdown
        fecha_entrega = datetime.now().strftime("%d/%m/%Y")
        norma = datos_usuario.get("norma", "apa7")

        config_norma = NORMAS_CONFIG.get(norma, NORMAS_CONFIG["apa7"])

        # CORRECCIÓN: datetime.now válido, sin markdown
        filename = f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}.pdf"
        filepath = os.path.join("informes_generados", filename)
        styles = self.crear_estilos(config_norma)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=config_norma["margen_derecho"],
            leftMargin=config_norma["margen_izquierdo"],
            topMargin=config_norma["margen_superior"],
            bottomMargin=config_norma["margen_inferior"],
        )

        story = []

        # PORTADA
        story.append(Spacer(1, 1.5 * inch))
        story.append(Paragraph("INFORME ACADÉMICO", styles["TituloPortada"]))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(tema.upper(), styles["TextoJustificado"]))
        story.append(Spacer(1, 1.2 * inch))
        story.append(
            Paragraph(f"<b>Presentado por:</b> {nombre}", styles["TextoJustificado"])
        )
        story.append(
            Paragraph(f"<b>Asignatura:</b> {asignatura}", styles["TextoJustificado"])
        )
        story.append(
            Paragraph(f"<b>Docente:</b> {profesor}", styles["TextoJustificado"])
        )
        story.append(
            Paragraph(f"<b>Institución:</b> {institucion}", styles["TextoJustificado"])
        )
        story.append(Spacer(1, 0.3 * inch))
        story.append(
            Paragraph(
                f"<b>Fecha de entrega:</b> {fecha_entrega}", styles["TextoJustificado"]
            )
        )
        story.append(
            Paragraph(
                f"<b>Norma aplicada:</b> {config_norma['nombre']}",
                styles["TextoJustificado"],
            )
        )
        story.append(PageBreak())

        # ÍNDICE
        story.append(Paragraph("ÍNDICE", styles["Titulo1"]))
        indices = [
            "1. INTRODUCCIÓN",
            "2. OBJETIVOS",
            "3. MARCO TEÓRICO",
            "4. METODOLOGÍA",
            "5. DESARROLLO",
            "6. CONCLUSIONES",
            "7. RECOMENDACIONES",
            "8. REFERENCIAS",
        ]
        for idx in indices:
            story.append(Paragraph(f"• {idx}", styles["TextoJustificado"]))
        story.append(PageBreak())

        # SECCIONES
        # CORRECCIÓN: texto correcto de INTRODUCCIÓN
        story.append(Paragraph("1. INTRODUCCIÓN", styles["Titulo1"]))
        story.append(
            Paragraph(secciones.get("introduccion", ""), styles["TextoJustificado"])
        )
        story.append(PageBreak())

        story.append(Paragraph("2. OBJETIVOS", styles["Titulo1"]))
        story.append(
            Paragraph(secciones.get("objetivos", ""), styles["TextoJustificado"])
        )
        story.append(PageBreak())

        story.append(Paragraph("3. MARCO TEÓRICO", styles["Titulo1"]))
        story.append(
            Paragraph(secciones.get("marco_teorico", ""), styles["TextoJustificado"])
        )
        story.append(PageBreak())

        story.append(Paragraph("4. METODOLOGÍA", styles["Titulo1"]))
        story.append(
            Paragraph(secciones.get("metodologia", ""), styles["TextoJustificado"])
        )
        story.append(PageBreak())

        story.append(Paragraph("5. DESARROLLO", styles["Titulo1"]))
        story.append(
            Paragraph(secciones.get("desarrollo", ""), styles["TextoJustificado"])
        )
        story.append(PageBreak())

        story.append(Paragraph("6. CONCLUSIONES", styles["Titulo1"]))
        story.append(
            Paragraph(secciones.get("conclusiones", ""), styles["TextoJustificado"])
        )
        story.append(PageBreak())

        story.append(Paragraph("7. RECOMENDACIONES", styles["Titulo1"]))
        story.append(
            Paragraph(secciones.get("recomendaciones", ""), styles["TextoJustificado"])
        )
        story.append(PageBreak())

        story.append(Paragraph("8. REFERENCIAS", styles["Titulo1"]))
        referencias = secciones.get("referencias", "")
        if referencias:
            lineas = referencias.split("\n")

            # CORRECCIÓN: numeración consecutiva sin saltos por líneas vacías
            contador = 0
            for linea in lineas:
                if linea.strip():
                    contador += 1
                    story.append(
                        Paragraph(
                            f"{contador}. {linea.strip()}", styles["TextoJustificado"]
                        )
                    )
        else:
            story.append(
                Paragraph(
                    "No se proporcionaron referencias.", styles["TextoJustificado"]
                )
            )

        # CORRECCIÓN: doc.build válido, sin markdown
        doc.build(story)
        return filename, filepath


generador = GeneradorPDF()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generar", methods=["POST"])
def generar():
    try:
        datos = request.json
        tema = datos.get("tema", "")

        if not tema or len(tema) < 3:
            return jsonify(
                {"success": False, "error": "Por favor ingresa un tema válido"}
            ), 400

        print(f"📨 Generando informe para: {tema[:50]}...")

        # Generar con IA
        secciones = generar_informe_con_ia(tema)

        # Si la IA falló, usar contenido local
        if not secciones:
            secciones = contenido_local_generico(tema)
            print("⚠️ Usando contenido local")

        datos_usuario = {
            "nombre": datos.get("nombre", ""),
            "tema": tema,
            "asignatura": datos.get("asignatura", ""),
            "profesor": datos.get("profesor", ""),
            "institucion": datos.get("institucion", ""),
            "norma": datos.get("norma", "apa7"),
        }

        filename, filepath = generador.generar_pdf(datos_usuario, secciones)

        return jsonify(
            {
                "success": True,
                "filename": filename,
                "download_url": f"/descargar/{filename}",
            }
        )

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/descargar/<filename>")
def descargar(filename):
    return send_file(
        os.path.join("informes_generados", filename),
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # CORRECCIÓN: app.run válido, sin markdown
    app.run(debug=False, host="0.0.0.0", port=port)
