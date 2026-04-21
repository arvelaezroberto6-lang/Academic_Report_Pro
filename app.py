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

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.makedirs('informes_generados', exist_ok=True)

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

logger.info("=" * 60)
logger.info("🚀 ACADEMIC REPORT PRO - VERSIÓN SIMPLIFICADA")
logger.info(f"🔑 API Key configurada: {'SÍ ✅' if DEEPSEEK_API_KEY else 'NO ❌'}")
logger.info("=" * 60)

def llamar_deepseek(prompt):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000
    }
    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            logger.error(f"Error HTTP {response.status_code}: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

@app.route('/')
def index():
    return "✅ API funcionando. Usa POST /test para probar."

@app.route('/test', methods=['POST'])
def test():
    prompt = "Dime 'Hola, funciono' en español"
    resultado = llamar_deepseek(prompt)
    if resultado:
        return jsonify({'success': True, 'respuesta': resultado})
    else:
        return jsonify({'success': False, 'error': 'La API no respondió'}), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'api_configured': bool(DEEPSEEK_API_KEY)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
