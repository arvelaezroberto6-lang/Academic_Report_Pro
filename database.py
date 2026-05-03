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
from datetime import datetime, timedelta, timezone

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

def registrar_usuario(nombre: str = "", email: str = "", password: str = "") -> dict:
    """
    Registra un nuevo usuario con email y contraseña.
    Si Supabase tiene confirmación de email desactivada, devuelve sesión directamente.
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
        if not res.user:
            return {"success": False, "error": "No se pudo crear el usuario"}

        if res.session:
            return {
                "success":      True,
                "user_id":      res.user.id,
                "email":        res.user.email,
                "nombre":       nombre,
                "access_token": res.session.access_token,
                "auto_login":   True,
            }
        return {
            "success":    True,
            "user_id":    res.user.id,
            "auto_login": False,
        }
    except Exception as e:
        logger.error(f"Error registrando usuario: {e}")
        msg = str(e)
        if "already registered" in msg or "already been registered" in msg:
            msg = "Este correo ya está registrado. Intenta iniciar sesión."
        return {"success": False, "error": msg}


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
            nombre = ""
            if res.user and res.user.user_metadata:
                nombre = res.user.user_metadata.get("nombre", "")
            return {
                "success":      True,
                "access_token": res.session.access_token,
                "user_id":      res.user.id,
                "email":        res.user.email,
                "nombre":       nombre,
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


def actualizar_perfil(user_id: str, nombre_o_datos=None, institucion: str = "",
                      carrera: str = "", ciudad: str = "", telefono: str = "") -> dict:
    """
    Actualiza el perfil del usuario.
    Acepta dos formas de llamada:
      - actualizar_perfil(user_id, datos_dict)
      - actualizar_perfil(user_id, nombre, inst, carr, ciudad, tel)
    """
    if not DB_DISPONIBLE:
        return {"success": False, "error": "Base de datos no disponible"}

    if isinstance(nombre_o_datos, dict):
        datos = nombre_o_datos
    else:
        datos = {
            "nombre":      nombre_o_datos or "",
            "institucion": institucion,
            "carrera":     carrera,
            "ciudad":      ciudad,
            "telefono":    telefono,
        }

    campos_permitidos = {"nombre", "institucion", "carrera", "ciudad", "telefono",
                         "norma_favorita", "nivel_favorito"}

    datos_limpios = {
        k: v for k, v in datos.items()
        if k in campos_permitidos and v is not None
    }

    if not datos_limpios:
        return {"success": False, "error": "No hay datos válidos para actualizar"}

    try:
        res = supabase.table("usuarios").update(datos_limpios).eq("id", user_id).execute()
        if res.data is not None and len(res.data) == 0:
            datos_limpios["id"] = user_id
            supabase.table("usuarios").upsert(datos_limpios).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error actualizando perfil: {e}")
        return {"success": False, "error": str(e)}


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
            "sec_introduccion":    secciones.get("introduccion", ""),
            "sec_objetivos":       secciones.get("objetivos", ""),
            "sec_marco_teorico":   secciones.get("marco_teorico", ""),
            "sec_metodologia":     secciones.get("metodologia", ""),
            "sec_desarrollo":      secciones.get("desarrollo", ""),
            "sec_conclusiones":    secciones.get("conclusiones", ""),
            "sec_recomendaciones": secciones.get("recomendaciones", ""),
            "sec_referencias":     secciones.get("referencias", ""),
            "refs_fuente":  "crossref_openalex" if refs_reales else "ia_fallback",
            "refs_total":   len(refs_reales) if refs_reales else 0,
            "estado":       "completo",
        }

        res = supabase.table("informes").insert(registro).execute()
        if not res.data:
            return None

        informe_id = res.data[0]["id"]
        logger.info(f"Informe guardado: {informe_id}")

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


def obtener_mis_informes(user_id: str, limite: int = 20, offset: int = 0) -> list:
    """
    Devuelve los informes del usuario ordenados por fecha descendente.
    Solo trae los campos necesarios para el listado (no el texto completo).
    """
    if not DB_DISPONIBLE:
        return []
    try:
        query = (
            supabase.table("informes")
            .select("id, tema, tipo_informe, norma, nivel, nombre_autor, "
                    "asignatura, institucion, refs_total, estado, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limite)
        )
        if offset:
            query = query.range(offset, offset + limite - 1)
        res = query.execute()
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


def eliminar_informe(informe_id: str, user_id: str) -> dict:
    """Elimina un informe (y sus referencias por CASCADE). Devuelve dict con success."""
    if not DB_DISPONIBLE:
        return {"success": False, "error": "Base de datos no disponible"}
    try:
        supabase.table("informes").delete().eq("id", informe_id).eq("user_id", user_id).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error eliminando informe: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# ESTADÍSTICAS DE USUARIO
# ============================================================

def obtener_estadisticas_usuario(user_id: str) -> dict | None:
    """
    Devuelve estadísticas agregadas del historial de informes del usuario.

    Retorna un dict con:
        total_informes      int   — total de informes completados
        total_referencias   int   — suma de todas las referencias
        norma_mas_usada     str   — norma que más usa (ej. "APA 7")
        tipo_mas_usado      str   — tipo de informe más frecuente
        nivel_mas_usado     str   — nivel más frecuente
        dias_activo         int   — días únicos con al menos 1 informe
        primer_informe      str   — fecha ISO del primer informe
        ultimo_informe      str   — fecha ISO del último informe
        informes_por_norma  dict  — {"APA 7": 5, "ICONTEC": 2, ...}
        informes_por_tipo   dict  — {"academico": 4, "tesis": 1, ...}
        racha_actual        int   — días consecutivos recientes con actividad
    """
    if not DB_DISPONIBLE:
        return None
    try:
        res = (
            supabase.table("informes")
            .select("norma, tipo_informe, nivel, refs_total, created_at")
            .eq("user_id", user_id)
            .eq("estado", "completo")
            .order("created_at", desc=False)
            .execute()
        )
        rows = res.data or []

        if not rows:
            return {
                "total_informes":     0,
                "total_referencias":  0,
                "norma_mas_usada":    None,
                "tipo_mas_usado":     None,
                "nivel_mas_usado":    None,
                "dias_activo":        0,
                "primer_informe":     None,
                "ultimo_informe":     None,
                "informes_por_norma": {},
                "informes_por_tipo":  {},
                "racha_actual":       0,
            }

        total_informes    = len(rows)
        total_referencias = sum(r.get("refs_total") or 0 for r in rows)

        conteo_norma = {}
        conteo_tipo  = {}
        conteo_nivel = {}
        fechas       = set()

        for r in rows:
            norma = r.get("norma") or "Desconocida"
            tipo  = r.get("tipo_informe") or "academico"
            nivel = r.get("nivel") or "universitario"
            fecha_iso = r.get("created_at", "")

            conteo_norma[norma] = conteo_norma.get(norma, 0) + 1
            conteo_tipo[tipo]   = conteo_tipo.get(tipo, 0) + 1
            conteo_nivel[nivel] = conteo_nivel.get(nivel, 0) + 1

            if fecha_iso:
                try:
                    fechas.add(fecha_iso[:10])
                except Exception:
                    pass

        norma_mas_usada = max(conteo_norma, key=conteo_norma.get) if conteo_norma else None
        tipo_mas_usado  = max(conteo_tipo,  key=conteo_tipo.get)  if conteo_tipo  else None
        nivel_mas_usado = max(conteo_nivel, key=conteo_nivel.get) if conteo_nivel else None

        primer_informe = rows[0].get("created_at")
        ultimo_informe = rows[-1].get("created_at")

        racha_actual = _calcular_racha(sorted(fechas))

        return {
            "total_informes":     total_informes,
            "total_referencias":  total_referencias,
            "norma_mas_usada":    norma_mas_usada,
            "tipo_mas_usado":     tipo_mas_usado,
            "nivel_mas_usado":    nivel_mas_usado,
            "dias_activo":        len(fechas),
            "primer_informe":     primer_informe,
            "ultimo_informe":     ultimo_informe,
            "informes_por_norma": conteo_norma,
            "informes_por_tipo":  conteo_tipo,
            "racha_actual":       racha_actual,
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de {user_id}: {e}")
        return None


def _calcular_racha(fechas_ordenadas: list) -> int:
    """
    Calcula cuántos días consecutivos hacia atrás desde hoy
    el usuario generó al menos un informe.
    """
    if not fechas_ordenadas:
        return 0

    hoy       = datetime.now(timezone.utc).date()
    racha     = 0
    dia       = hoy
    fechas_set = set(fechas_ordenadas)

    if str(hoy) not in fechas_set:
        dia = hoy - timedelta(days=1)

    while str(dia) in fechas_set:
        racha += 1
        dia   -= timedelta(days=1)

    return racha


def obtener_resumen_actividad(user_id: str, dias: int = 30) -> list:
    """
    Devuelve la actividad diaria del usuario en los últimos N días.
    Retorna: [{"fecha": "2025-05-01", "cantidad": 2}, ...]
    Solo incluye días con al menos 1 informe.
    """
    if not DB_DISPONIBLE:
        return []
    try:
        desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        res = (
            supabase.table("informes")
            .select("created_at")
            .eq("user_id", user_id)
            .eq("estado", "completo")
            .gte("created_at", desde)
            .execute()
        )
        rows = res.data or []

        conteo = {}
        for r in rows:
            fecha_str = (r.get("created_at") or "")[:10]
            if fecha_str:
                conteo[fecha_str] = conteo.get(fecha_str, 0) + 1

        return [
            {"fecha": f, "cantidad": c}
            for f, c in sorted(conteo.items())
        ]
    except Exception as e:
        logger.error(f"Error obteniendo actividad de {user_id}: {e}")
        return []
