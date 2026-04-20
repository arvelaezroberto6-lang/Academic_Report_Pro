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

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

print("=" * 50)
print("🚀 ACADEMIC REPORT PRO - VERSIÓN DEFINITIVA")
print(f"🔑 IA: {'ACTIVADA ✅' if GROQ_API_KEY else 'DESACTIVADA ❌'}")
print("=" * 50)

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
    if not texto:
        return ""
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", texto)
    texto = texto.replace("INFORMÉ", "INFORME")
    texto = texto.replace("Conclusions", "CONCLUSIONES")
    texto = texto.replace("CONCLUSIONS", "CONCLUSIONES")
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def contenido_local_generico(tema):
    tema_limpio = tema if tema else "el tema de investigación"
    return {
        "introduccion": f"El presente informe académico aborda {tema_limpio}.",
        "objetivos": f"<b>Objetivo General</b><br/>Analizar {tema_limpio}.<br/><br/><b>Objetivos Específicos</b><br/>1. Identificar factores clave.<br/>2. Describir características.<br/>3. Analizar implicaciones.<br/>4. Proponer recomendaciones.",
        "marco_teorico": f"<b>Conceptos clave</b><br/>Para comprender {tema_limpio}.",
        "metodologia": f"<b>Enfoque</b><br/>Mixto.<br/><b>Muestra</b><br/>250 participantes.",
        "desarrollo": f"<b>Resultados</b><br/>Tendencias significativas en {tema_limpio}.",
        "conclusiones": f"1. {tema_limpio} es relevante.<br/>2. Se requiere más investigación.<br/>3. Recomendaciones viables.",
        "recomendaciones": f"1. Fortalecer investigación.<br/>2. Aplicar hallazgos.<br/>3. Ampliar muestra.",
    }


def extraer_seccion(contenido, nombre):
    patron = rf"\*\*{nombre}\*\*:?(.*?)(?=\*\*[A-Z]|$)"
    match = re.search(patron, contenido, re.DOTALL | re.IGNORECASE)
    if match:
        texto = match.group(1).strip()
        texto = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", texto)
        return texto
    return ""


def generar_informe_con_ia(tema):
    if not GROQ_API_KEY:
        return None
    print(f"🤖 Generando informe para: {tema[:50]}...")
    prompt = f"""Genera un informe académico completo y profesional sobre: "{tema}"

**INTRODUCCIÓN** (contexto, problema, justificación)
**OBJETIVOS** (1 general + 4 específicos)
**MARCO TEÓRICO** (conceptos clave, autores)
**METODOLOGÍA** (enfoque, muestra, instrumentos)
**DESARROLLO** (resultados con porcentajes, análisis)
**CONCLUSIONES** (5 puntos)
**RECOMENDACIONES** (3-4 puntos)
**REFERENCIAS** (5-6 fuentes reales)

Usa español. Usa CONCLUSIONES (nunca Conclusions)."""

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
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60,
        )
        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado["choices"][0]["message"]["content"]
            contenido = limpiar_texto(contenido)
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
            for key in secciones:
                if not secciones[key] or len(secciones[key]) < 50:
                    secciones[key] = contenido_local_generico(tema).get(key, "")
            return secciones
    except Exception as e:
        print(f"Error IA: {e}")
    return None


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
        fecha_entrega = datetime.now().strftime("%d/%m/%Y")
        norma = datos_usuario.get("norma", "apa7")
        config_norma = NORMAS_CONFIG.get(norma, NORMAS_CONFIG["apa7"])

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
            for i, linea in enumerate(lineas, 1):
                if linea.strip():
                    story.append(
                        Paragraph(f"{i}. {linea.strip()}", styles["TextoJustificado"])
                    )
        else:
            story.append(
                Paragraph(
                    "No se proporcionaron referencias.", styles["TextoJustificado"]
                )
            )

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
        secciones = generar_informe_con_ia(tema)
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
    app.run(debug=False, host="0.0.0.0", port=port)
