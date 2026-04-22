from flask import Flask, request, jsonify
import os
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

@app.route('/test', methods=['GET'])
def test():
    """Prueba directa a DeepSeek"""
    
    if not DEEPSEEK_API_KEY:
        return jsonify({'error': 'API Key no configurada'}), 500
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "Dime 'Hola, funciono' en español, solo eso"}
        ],
        "max_tokens": 50
    }
    
    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=30)
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado['choices'][0]['message']['content']
            return jsonify({'success': True, 'respuesta': contenido})
        else:
            return jsonify({'success': False, 'error': f'HTTP {response.status_code}: {response.text}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/')
def index():
    return "Prueba. Ve a /test para verificar DeepSeek"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
