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

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.makedirs('informes_generados', exist_ok=True)

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

# ============================================================
# FUNCIÓN CORREGIDA PARA LLAMAR A DEEPSEEK
# ============================================================
def llamar_deepseek(prompt_texto):
    """Envía una solicitud a DeepSeek y devuelve la respuesta."""
    if not DEEPSEEK_API_KEY:
        logger.error("API Key de DeepSeek no configurada.")
        return None

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    # --- ESTRUCTURA CORREGIDA Y SIMPLIFICADA ---
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt_texto}
        ],
        "max_tokens": 4000,
        "temperature": 0.7
    }

    try:
        logger.info("Enviando solicitud a DeepSeek...")
        response = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=60)
        
        # --- LOG PARA VER EL ERROR EXACTO ---
        if response.status_code != 200:
            logger.error(f"Error HTTP {response.status_code}: {response.text}")
            return None
            
        resultado = response.json()
        contenido = resultado['choices'][0]['message']['content']
        logger.info(f"Solicitud exitosa. Tokens usados: {resultado['usage']['total_tokens']}")
        return contenido

    except Exception as e:
        logger.error(f"Error en la solicitud a DeepSeek: {e}")
        return None

# ============================================================
# RUTA PRINCIPAL
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')

# ============================================================
# RUTA PARA GENERAR EL INFORME (VERSIÓN SIMPLIFICADA Y SEGURA)
# ============================================================
@app.route('/generar', methods=['POST'])
def generar():
    try:
        data = request.json
        tema = data.get('tema', '').strip()
        nombre = data.get('nombre', 'Estudiante')
        
        if not tema:
            return jsonify({'success': False, 'error': 'El tema es requerido'}), 400

        # --- PROMPT CORTO Y EFECTIVO PARA PRUEBA ---
        prompt = f"""Genera un informe académico corto sobre el tema: "{tema}".

El informe debe tener la siguiente estructura:
1. Introducción
2. Objetivos (1 general, 3 específicos)
3. Desarrollo (análisis del tema)
4. Conclusiones (3 puntos)
5. Recomendaciones (2 puntos)

Escribe en español, con un tono profesional y claro. Sé conciso.
"""
        
        logger.info(f"Generando informe para: {tema}")
        contenido_ia = llamar_deepseek(prompt)

        if not contenido_ia:
            return jsonify({'success': False, 'error': 'La IA no pudo generar el contenido.'}), 500

        # --- AQUÍ LUEGO AGREGARÁS LA LÓGICA PARA CREAR EL PDF ---
        # Por ahora, devolvemos el texto para confirmar que funciona.
        return jsonify({
            'success': True,
            'contenido': contenido_ia,
            'mensaje': 'Informe generado correctamente. (Fase 1: solo texto)'
        })

    except Exception as e:
        logger.error(f"Error en /generar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# HEALTH CHECK
# ============================================================
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'api_configured': bool(DEEPSEEK_API_KEY),
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
