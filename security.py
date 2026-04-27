"""
security.py
===========
Módulo de seguridad para Academic Report Pro.
Centraliza autenticación, validación, rate limiting y sanitización.

Instalación de dependencias nuevas:
    pip install flask-limiter bleach
"""

import re
import html
import uuid
import logging
import os
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)

# ============================================================
# VALIDADORES DE FORMATO
# ============================================================

def es_uuid_valido(valor: str) -> bool:
    """Verifica que el valor sea un UUID válido."""
    try:
        uuid.UUID(str(valor))
        return True
    except (ValueError, AttributeError):
        return False


def es_email_valido(email: str) -> bool:
    """Validación básica de formato de email."""
    patron = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
    return bool(patron.match(email)) and len(email) <= 254


def es_password_seguro(password: str) -> tuple[bool, str]:
    """
    Valida que la contraseña cumpla requisitos mínimos de seguridad.
    Devuelve (bool, mensaje_error).
    """
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    if len(password) > 128:
        return False, "La contraseña es demasiado larga"
    if not re.search(r'[A-Z]', password):
        return False, "La contraseña debe contener al menos una letra mayúscula"
    if not re.search(r'[0-9]', password):
        return False, "La contraseña debe contener al menos un número"
    return True, ""


# ============================================================
# SANITIZACIÓN DE TEXTO
# ============================================================

def sanitizar_texto(texto: str, max_len: int = 2000) -> str:
    """
    Limpia el texto de HTML peligroso y caracteres de control.
    Úsalo en cualquier input que venga del usuario.
    """
    if not texto or not isinstance(texto, str):
        return ""
    # Escapar HTML entities
    texto = html.escape(texto.strip())
    # Eliminar caracteres de control (excepto saltos de línea y tab)
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)
    # Limitar longitud
    return texto[:max_len]


def sanitizar_html_email(texto: str) -> str:
    """
    Escapa texto para insertar de forma segura en el cuerpo HTML de un email.
    Previene XSS cuando el texto del usuario se muestra en el email del admin.
    """
    if not texto or not isinstance(texto, str):
        return ""
    # Escapar todos los caracteres HTML especiales
    safe = html.escape(texto, quote=True)
    # Convertir saltos de línea en <br> (safe después del escape)
    safe = safe.replace('\n', '<br>')
    return safe


def sanitizar_nombre(nombre: str) -> str:
    """Limpia un nombre de usuario eliminando caracteres peligrosos."""
    if not nombre:
        return "Anónimo"
    # Solo letras, espacios, guiones y apóstrofes
    nombre = re.sub(r"[^\w\s\-'\.]", '', nombre.strip(), flags=re.UNICODE)
    return nombre[:100] or "Anónimo"


# ============================================================
# VERIFICACIÓN DE TOKEN JWT (Supabase)
# ============================================================

def obtener_user_id_verificado(request_obj) -> str | None:
    """
    Verifica el JWT de Supabase desde el header Authorization.
    Devuelve el user_id real si es válido, None si no.

    El frontend debe enviar:
        headers: { 'Authorization': 'Bearer <access_token>' }

    Esto reemplaza el uso inseguro de X-User-Id que venía del cliente
    sin ninguna verificación del servidor.
    """
    try:
        from database import supabase, DB_DISPONIBLE
        if not DB_DISPONIBLE or supabase is None:
            # Fallback temporal: aceptar X-User-Id solo en desarrollo
            # EN PRODUCCIÓN con pagos esto debe eliminarse
            env = os.environ.get('FLASK_ENV', 'production')
            if env == 'development':
                uid = request_obj.headers.get('X-User-Id', '').strip()
                return uid if es_uuid_valido(uid) else None
            return None

        auth_header = request_obj.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ', 1)[1].strip()
        if not token:
            return None

        # Verificar el token con Supabase (esto valida firma y expiración)
        user_response = supabase.auth.get_user(token)
        if user_response and user_response.user:
            return str(user_response.user.id)
        return None

    except Exception as e:
        logger.warning(f"Token JWT inválido o expirado: {e}")
        return None


# ============================================================
# DECORADORES DE AUTENTICACIÓN
# ============================================================

def requiere_auth(f):
    """
    Decorador para rutas que requieren usuario autenticado.
    Inyecta el user_id verificado como primer argumento.

    Uso:
        @app.route('/api/mis-informes')
        @requiere_auth
        def mis_informes(user_id):
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = obtener_user_id_verificado(request)
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'No autenticado. Inicia sesión de nuevo.',
                'code': 'AUTH_REQUIRED'
            }), 401
        return f(user_id, *args, **kwargs)
    return decorated


# ============================================================
# VALIDACIÓN DE PARÁMETROS DE NEGOCIO
# ============================================================

NORMAS_VALIDAS = {'APA 7', 'APA 6', 'ICONTEC', 'IEEE', 'Vancouver', 'Chicago', 'MLA', 'Harvard'}
TIPOS_VALIDOS  = {'academico', 'laboratorio', 'ejecutivo', 'tesis', 'pasantia', 'proyecto'}
NIVELES_VALIDOS = {'colegio', 'tecnico', 'universitario', 'posgrado'}
MODOS_VALIDOS   = {'rapido', 'automatico', 'manual'}


def validar_params_informe(data: dict) -> tuple[bool, str]:
    """
    Valida los parámetros de generación de un informe.
    Devuelve (es_valido, mensaje_error).
    """
    tema = data.get('tema', '').strip()
    if not tema:
        return False, "El tema es requerido"
    if len(tema) < 5:
        return False, "El tema es demasiado corto (mínimo 5 caracteres)"
    if len(tema) > 500:
        return False, "El tema es demasiado largo (máximo 500 caracteres)"

    norma = data.get('norma', 'APA 7')
    if norma not in NORMAS_VALIDAS:
        return False, f"Norma inválida: {norma}"

    tipo = data.get('tipo_informe', 'academico')
    if tipo not in TIPOS_VALIDOS:
        return False, f"Tipo de informe inválido: {tipo}"

    nivel = data.get('nivel', 'universitario')
    if nivel not in NIVELES_VALIDOS:
        return False, f"Nivel inválido: {nivel}"

    modo = data.get('modo', 'rapido')
    if modo not in MODOS_VALIDOS:
        return False, f"Modo inválido: {modo}"

    return True, ""


# ============================================================
# HEADERS DE SEGURIDAD HTTP
# ============================================================

def aplicar_headers_seguridad(response):
    """
    Agrega headers de seguridad a todas las respuestas HTTP.
    Protege contra XSS, clickjacking, sniffing de contenido, etc.

    Registrar en app.py con:
        app.after_request(aplicar_headers_seguridad)
    """
    # Previene que el navegador ejecute JS inyectado en respuestas
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Previene que la app se cargue en un iframe (clickjacking)
    response.headers['X-Frame-Options'] = 'DENY'
    # Activa el filtro XSS del navegador (compatibilidad legacy)
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Controla qué URL se envía como Referer
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Restricción de recursos: solo carga desde el propio origen + CDNs necesarios
    # IMPORTANTE: cuando agregues pagos, incluir dominios de Stripe/PayU aquí
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net unpkg.com cdn.sweetalert2.io cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' fonts.googleapis.com cdn.jsdelivr.net; "
        "font-src 'self' fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' api.deepseek.com *.supabase.co; "
        "frame-ancestors 'none';"
    )
    # Fuerza HTTPS en navegadores que ya visitaron el sitio
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Evita enviar información sensible en logs de red
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

    return response


# ============================================================
# LOGGING DE EVENTOS DE SEGURIDAD
# ============================================================

def log_evento_seguridad(tipo: str, detalle: str, request_obj=None):
    """
    Registra eventos de seguridad importantes para auditoría.
    Cuando tengas pagos, estos logs son esenciales para detectar fraude.
    """
    ip = 'unknown'
    if request_obj:
        # X-Forwarded-For viene del proxy/CDN (Render, Cloudflare, etc.)
        ip = request_obj.headers.get('X-Forwarded-For', request_obj.remote_addr or 'unknown')
        ip = ip.split(',')[0].strip()  # tomar solo la primera IP

    logger.warning(f"[SEGURIDAD] {tipo} | IP: {ip} | {detalle}")


# ============================================================
# UTILIDADES PARA PAGOS FUTUROS
# (preparado para cuando integres Stripe o PayU)
# ============================================================

def validar_webhook_stripe(payload: bytes, sig_header: str, secret: str) -> bool:
    """
    Valida la firma de webhooks de Stripe para prevenir webhooks falsos.
    Usar cuando integres pagos con Stripe.

    Requiere: pip install stripe
    """
    try:
        import stripe
        stripe.Webhook.construct_event(payload, sig_header, secret)
        return True
    except Exception as e:
        logger.error(f"Webhook Stripe inválido: {e}")
        return False


def sanitizar_datos_pago(data: dict) -> dict:
    """
    Sanitiza los datos antes de enviarlos a la pasarela de pago.
    NUNCA manejes datos de tarjeta directamente — usa el SDK del proveedor.
    Esta función solo limpia metadatos (nombre, email, plan).
    """
    return {
        'email':    sanitizar_texto(data.get('email', ''), 254),
        'nombre':   sanitizar_nombre(data.get('nombre', '')),
        'plan':     sanitizar_texto(data.get('plan', ''), 50),
        'user_id':  data.get('user_id', '') if es_uuid_valido(data.get('user_id', '')) else '',
    }
