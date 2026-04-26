"""
database.py
===========
Módulo de integración con Supabase para Academic Report Pro.
Maneja usuarios, guardado de informes y referencias.

Instalación:
    pip install supabase

Variables de entorno necesarias (agregar a tu .env o Render):
    SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
    SUPABASE_KEY=tu_anon_key_aqui
"""

import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Inicializar cliente Supabase ──────────────────────────────
try:
    from supabase import create_client, Client
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        DB_DISPONIBLE = True
        logger.info("✅ Supabase conectado correctamente")
    else:
        supabase = None
        DB_DISPONIBLE = False
        logger.warning("⚠️ Supabase no configurado — funciona sin base de datos")
except ImportError:
    supabase = None
    DB_DISPONIBLE = False
    logger.warning("⚠️ supabase-py no instalado — pip install supabase")


# ============================================================
# USUARIOS
# ============================================================

def registrar_usuario(email: str, password: str, nombre: str = "") -> dict:
    """
    Registra un nuevo usuario con email y contraseña.
    Supabase crea automáticamente el perfil via trigger.
    """
    if not DB_DISPONIBLE:
        return {"success": False, "error": "Base de datos no disponible"}
    try:
        res = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"nombre": nombre}}
        })
        if res.user:
            return {"success": True, "user_id": res.user.id}
        return {"success": False, "error": "No se pudo crear el usuario"}
    except Exception as e:
        logger.error(f"Error registrando usuario: {e}")
        return {"success": False, "error": str(e)}


def login_usuario(email: str, password: str) -> dict:
    """Inicia sesión y devuelve el token de acceso."""
    if not DB_DISPONIBLE:
        return {"success": False, "error": "Base de datos no disponible"}
    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if res.session:
            return {
                "success":      True,
                "access_token": res.session.access_token,
                "user_id":      res.user.id,
                "email":        res.user.email,
            }
        return {"success": False, "error": "Credenciales incorrectas"}
    except Exception as e:
        logger.error(f"Error en login: {e}")
        return {"success": False, "error": "Email o contraseña incorrectos"}


def obtener_perfil(user_id: str) -> dict | None:
    """Devuelve el perfil del usuario o None si no existe."""
    if not DB_DISPONIBLE:
        return None
    try:
        res = supabase.table("usuarios").select("*").eq("id", user_id).single().execute()
        return res.data
    except Exception as e:
        logger.error(f"Error obteniendo perfil: {e}")
        return None


def actualizar_perfil(user_id: str, datos: dict) -> bool:
    """Actualiza nombre, institución, ciudad, norma y nivel favorito."""
    if not DB_DISPONIBLE:
        return False
    campos_permitidos = {"nombre", "institucion", "ciudad", "norma_favorita", "nivel_favorito"}
    datos_limpios = {k: v for k, v in datos.items() if k in campos_permitidos}
    if not datos_limpios:
        return False
    try:
        supabase.table("usuarios").update(datos_limpios).eq("id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error actualizando perfil: {e}")
        return False


# ============================================================
# INFORMES
# ============================================================

def guardar_informe(user_id: str, datos_usuario: dict,
                    secciones: dict, refs_reales: list = None,
                    tipo_informe: str = "academico", norma: str = "APA 7",
                    nivel: str = "universitario", modo: str = "rapido") -> str | None:
    """
    Guarda un informe completo en Supabase.
    Devuelve el UUID del informe guardado, o None si falla.

    Uso en app.py:
        from database import guardar_informe
        informe_id = guardar_informe(user_id, datos_usuario, secciones, refs_reales)
    """
    if not DB_DISPONIBLE:
        return None
    try:
        registro = {
            "user_id":          user_id,
            "tema":             datos_usuario.get("tema", ""),
            "tipo_informe":     tipo_informe,
            "norma":            norma,
            "nivel":            nivel,
            "modo":             modo,
            "nombre_autor":     datos_usuario.get("nombre", ""),
            "asignatura":       datos_usuario.get("asignatura", ""),
            "profesor":         datos_usuario.get("profesor", ""),
            "institucion":      datos_usuario.get("institucion", ""),
            "ciudad":           datos_usuario.get("ciudad", ""),
            # Secciones
            "sec_introduccion":    secciones.get("introduccion", ""),
            "sec_objetivos":       secciones.get("objetivos", ""),
            "sec_marco_teorico":   secciones.get("marco_teorico", ""),
            "sec_metodologia":     secciones.get("metodologia", ""),
            "sec_desarrollo":      secciones.get("desarrollo", ""),
            "sec_conclusiones":    secciones.get("conclusiones", ""),
            "sec_recomendaciones": secciones.get("recomendaciones", ""),
            "sec_referencias":     secciones.get("referencias", ""),
            # Metadata
            "refs_fuente":  "crossref_openalex" if refs_reales else "ia_fallback",
            "refs_total":   len(refs_reales) if refs_reales else 0,
            "estado":       "completo",
        }

        res = supabase.table("informes").insert(registro).execute()
        if not res.data:
            return None

        informe_id = res.data[0]["id"]
        logger.info(f"Informe guardado: {informe_id}")

        # Guardar referencias individuales si las hay
        if refs_reales:
            _guardar_referencias(informe_id, refs_reales)

        return informe_id

    except Exception as e:
        logger.error(f"Error guardando informe: {e}")
        return None


def _guardar_referencias(informe_id: str, refs: list):
    """Guarda las referencias individuales del informe."""
    try:
        registros = []
        for ref in refs:
            registros.append({
                "informe_id": informe_id,
                "tipo":       ref.get("tipo", "articulo"),
                "titulo":     ref.get("titulo", ""),
                "autores":    ref.get("autores", []),
                "anio":       ref.get("anio"),
                "revista":    ref.get("revista", ""),
                "editorial":  ref.get("editorial", ""),
                "volumen":    ref.get("volumen", ""),
                "numero":     ref.get("numero", ""),
                "paginas":    ref.get("paginas", ""),
                "doi":        ref.get("doi", ""),
                "fuente":     ref.get("fuente", "crossref"),
            })
        if registros:
            supabase.table("referencias_informe").insert(registros).execute()
    except Exception as e:
        logger.error(f"Error guardando referencias individuales: {e}")


def obtener_mis_informes(user_id: str, limite: int = 20) -> list:
    """
    Devuelve los informes del usuario ordenados por fecha descendente.
    Solo trae los campos necesarios para el listado (no el texto completo).
    """
    if not DB_DISPONIBLE:
        return []
    try:
        res = (
            supabase.table("informes")
            .select("id, tema, tipo_informe, norma, nivel, nombre_autor, "
                    "asignatura, institucion, refs_total, estado, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limite)
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.error(f"Error obteniendo informes: {e}")
        return []


def obtener_informe(informe_id: str, user_id: str) -> dict | None:
    """
    Devuelve un informe completo con todas sus secciones.
    Verifica que pertenezca al usuario (seguridad).
    """
    if not DB_DISPONIBLE:
        return None
    try:
        res = (
            supabase.table("informes")
            .select("*")
            .eq("id", informe_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return res.data
    except Exception as e:
        logger.error(f"Error obteniendo informe {informe_id}: {e}")
        return None


def eliminar_informe(informe_id: str, user_id: str) -> bool:
    """Elimina un informe (y sus referencias por CASCADE)."""
    if not DB_DISPONIBLE:
        return False
    try:
        supabase.table("informes").delete().eq("id", informe_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error eliminando informe: {e}")
        return False


# ============================================================
# RUTAS FLASK — pega esto en tu app.py
# ============================================================
"""
INSTRUCCIONES DE INTEGRACIÓN EN app.py:
========================================

1. Agrega al inicio de app.py:
   from database import (
       registrar_usuario, login_usuario, obtener_perfil,
       actualizar_perfil, guardar_informe, obtener_mis_informes,
       obtener_informe, eliminar_informe, DB_DISPONIBLE
   )

2. En api_generar(), después de generar el informe, guárdalo:

   # Guardar en Supabase si el usuario está autenticado
   user_id = request.headers.get('X-User-Id')  # el frontend lo manda
   if user_id and DB_DISPONIBLE:
       guardar_informe(
           user_id=user_id,
           datos_usuario=datos_usuario,
           secciones=secciones,
           refs_reales=refs_reales,   # necesitas pasar refs_reales desde generar_informe_completo
           tipo_informe=tipo_informe,
           norma=norma,
           nivel=nivel,
           modo=data.get('modo', 'rapido')
       )

3. Agrega estas rutas nuevas:

@app.route('/api/auth/registro', methods=['POST'])
def api_registro():
    data = request.json
    return jsonify(registrar_usuario(
        data.get('email',''), data.get('password',''), data.get('nombre','')
    ))

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json
    return jsonify(login_usuario(data.get('email',''), data.get('password','')))

@app.route('/api/mis-informes', methods=['GET'])
def api_mis_informes():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    informes = obtener_mis_informes(user_id)
    return jsonify({'success': True, 'informes': informes})

@app.route('/api/informe/<informe_id>', methods=['GET'])
def api_obtener_informe(informe_id):
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    informe = obtener_informe(informe_id, user_id)
    if not informe:
        return jsonify({'success': False, 'error': 'No encontrado'}), 404
    return jsonify({'success': True, 'informe': informe})

@app.route('/api/informe/<informe_id>', methods=['DELETE'])
def api_eliminar_informe(informe_id):
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    ok = eliminar_informe(informe_id, user_id)
    return jsonify({'success': ok})

@app.route('/api/perfil', methods=['GET'])
def api_perfil():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    perfil = obtener_perfil(user_id)
    return jsonify({'success': True, 'perfil': perfil})

@app.route('/api/perfil', methods=['PUT'])
def api_actualizar_perfil():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    ok = actualizar_perfil(user_id, request.json)
    return jsonify({'success': ok})
"""
