"""
referencias_reales.py
=====================
Módulo para obtener referencias bibliográficas REALES usando:
  1. CrossRef API  — artículos científicos con DOI verificado
  2. OpenAlex API  — libros, tesis, reportes institucionales

Flujo:
  buscar_referencias_reales(tema, norma, cantidad) → lista de dicts con metadata real
  formatear_referencias(lista, norma)              → texto final listo para el informe
"""

import requests
import logging
import re
import time
from urllib.parse import quote

logger = logging.getLogger(__name__)

CROSSREF_URL  = "https://api.crossref.org/works"
OPENALEX_URL  = "https://api.openalex.org/works"
CONTACT_EMAIL = "academicreportpro@gmail.com"   # CrossRef pide un email para la polite pool


# ──────────────────────────────────────────────────────────────
# CROSSREF: artículos científicos con DOI real
# ──────────────────────────────────────────────────────────────
def buscar_crossref(query: str, cantidad: int = 6, desde_anio: int = 2015) -> list[dict]:
    """
    Busca artículos en CrossRef y devuelve metadata estructurada.
    Solo devuelve registros que tengan DOI, título, autores y año.
    """
    params = {
        "query":              query,
        "rows":               min(cantidad * 3, 30),   # pedir más para filtrar
        "select":             "DOI,title,author,published,container-title,type,publisher,volume,issue,page",
        "filter":             f"from-pub-date:{desde_anio}-01-01,type:journal-article",
        "sort":               "relevance",
        "mailto":             CONTACT_EMAIL,
    }
    try:
        resp = requests.get(CROSSREF_URL, params=params, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"CrossRef HTTP {resp.status_code}")
            return []

        items = resp.json().get("message", {}).get("items", [])
        resultados = []

        for item in items:
            # Filtrar registros incompletos
            if not item.get("DOI"):
                continue
            titulo_list = item.get("title", [])
            if not titulo_list:
                continue
            autores_raw = item.get("author", [])
            if not autores_raw:
                continue

            # Extraer año
            pub = item.get("published", {})
            partes = pub.get("date-parts", [[None]])[0]
            anio = partes[0] if partes else None
            if not anio or anio < desde_anio:
                continue

            # Normalizar autores
            autores = []
            for a in autores_raw[:7]:
                apellido = a.get("family", "")
                nombre   = a.get("given", "")
                if apellido:
                    autores.append({"apellido": apellido, "nombre": nombre})

            revista_list = item.get("container-title", [])
            revista = revista_list[0] if revista_list else ""

            resultados.append({
                "tipo":     "articulo",
                "titulo":   titulo_list[0],
                "autores":  autores,
                "anio":     anio,
                "revista":  revista,
                "volumen":  item.get("volume", ""),
                "numero":   item.get("issue", ""),
                "paginas":  item.get("page", ""),
                "doi":      item.get("DOI", ""),
                "fuente":   "crossref",
            })

            if len(resultados) >= cantidad:
                break

        logger.info(f"CrossRef: {len(resultados)} artículos para '{query[:40]}'")
        return resultados

    except Exception as e:
        logger.error(f"Error CrossRef: {e}")
        return []


# ──────────────────────────────────────────────────────────────
# OPENALEX: libros, tesis, reportes institucionales
# ──────────────────────────────────────────────────────────────
def buscar_openalex(query: str, cantidad: int = 6,
                   tipos: list[str] = None, desde_anio: int = 2015) -> list[dict]:
    """
    Busca en OpenAlex por tipo de publicación.
    tipos puede ser: ['book', 'dissertation', 'report', 'journal-article']
    """
    if tipos is None:
        tipos = ["book", "dissertation", "report"]

    filtros = [
        f"publication_year:>{desde_anio - 1}",
        f"type:{'|'.join(tipos)}",
    ]

    params = {
        "search":     query,
        "filter":     ",".join(filtros),
        "per-page":   min(cantidad * 3, 25),
        "select":     "id,title,authorships,publication_year,type,primary_location,biblio,doi",
        "sort":       "relevance_score:desc",
        "mailto":     CONTACT_EMAIL,
    }

    try:
        resp = requests.get(OPENALEX_URL, params=params, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"OpenAlex HTTP {resp.status_code}")
            return []

        items = resp.json().get("results", [])
        resultados = []

        for item in items:
            if not item.get("title"):
                continue

            # Autores
            autores = []
            for auth in item.get("authorships", [])[:7]:
                nombre_completo = auth.get("author", {}).get("display_name", "")
                partes = nombre_completo.rsplit(" ", 1)
                if len(partes) == 2:
                    autores.append({"apellido": partes[1], "nombre": partes[0]})
                elif nombre_completo:
                    autores.append({"apellido": nombre_completo, "nombre": ""})

            if not autores:
                continue

            anio = item.get("publication_year")
            if not anio or anio < desde_anio:
                continue

            # Fuente / editorial
            loc = item.get("primary_location") or {}
            fuente_info = loc.get("source") or {}
            editorial = fuente_info.get("display_name", "")

            # DOI
            doi_raw = item.get("doi", "") or ""
            doi = doi_raw.replace("https://doi.org/", "").strip()

            # Tipo normalizado
            tipo_raw = item.get("type", "book")
            tipo_map = {
                "book":             "libro",
                "dissertation":     "tesis",
                "report":           "reporte",
                "journal-article":  "articulo",
            }
            tipo = tipo_map.get(tipo_raw, "libro")

            # biblio para libros
            biblio = item.get("biblio", {}) or {}

            resultados.append({
                "tipo":      tipo,
                "titulo":    item["title"],
                "autores":   autores,
                "anio":      anio,
                "editorial": editorial,
                "doi":       doi,
                "paginas":   str(biblio.get("last_page", "")) if biblio.get("last_page") else "",
                "fuente":    "openalex",
            })

            if len(resultados) >= cantidad:
                break

        logger.info(f"OpenAlex: {len(resultados)} resultados para '{query[:40]}'")
        return resultados

    except Exception as e:
        logger.error(f"Error OpenAlex: {e}")
        return []


# ──────────────────────────────────────────────────────────────
# BÚSQUEDA COMBINADA
# ──────────────────────────────────────────────────────────────
def buscar_referencias_reales(tema: str, cantidad_total: int = 12) -> list[dict]:
    """
    Combina CrossRef + OpenAlex para obtener un conjunto diverso:
    - 5-6 artículos de revista (CrossRef)
    - 3-4 libros/tesis (OpenAlex)
    - 2-3 reportes institucionales (OpenAlex)

    Hace búsquedas secundarias en inglés si el tema está en español
    para ampliar el corpus disponible.
    """
    referencias = []

    # ── Artículos científicos (CrossRef) ──────────────────────
    arts = buscar_crossref(tema, cantidad=6)
    referencias.extend(arts)
    time.sleep(0.3)   # respetar rate limit de CrossRef

    # Si no hay suficientes artículos, buscar en inglés
    if len(arts) < 3:
        arts_en = buscar_crossref(_traducir_query(tema), cantidad=5)
        # Evitar duplicados por DOI
        dois_existentes = {r["doi"] for r in referencias if r.get("doi")}
        for a in arts_en:
            if a.get("doi") not in dois_existentes:
                referencias.append(a)
        time.sleep(0.3)

    # ── Libros y tesis (OpenAlex) ─────────────────────────────
    libros = buscar_openalex(tema, cantidad=4, tipos=["book", "dissertation"])
    referencias.extend(libros)
    time.sleep(0.3)

    # ── Reportes institucionales (OpenAlex) ───────────────────
    reportes = buscar_openalex(tema, cantidad=3, tipos=["report"])
    referencias.extend(reportes)
    time.sleep(0.3)

    # Deduplicar por título normalizado
    vistos = set()
    unicas = []
    for ref in referencias:
        clave = re.sub(r'\W+', '', ref["titulo"].lower())[:60]
        if clave not in vistos:
            vistos.add(clave)
            unicas.append(ref)

    # Asegurar diversidad de tipos
    unicas = _balancear_tipos(unicas, cantidad_total)

    logger.info(f"Total referencias reales obtenidas: {len(unicas)}")
    return unicas[:cantidad_total]


def _traducir_query(texto: str) -> str:
    """Traducción simple de términos comunes para búsquedas en inglés."""
    traducciones = {
        "inteligencia artificial": "artificial intelligence",
        "educación":               "education",
        "tecnología":              "technology",
        "salud":                   "health",
        "economía":                "economy",
        "medio ambiente":          "environment",
        "cambio climático":        "climate change",
        "seguridad":               "security",
        "datos":                   "data",
        "aprendizaje":             "learning",
        "universidad":             "university",
        "investigación":           "research",
        "desarrollo":              "development",
        "colombia":                "colombia",
        "latinoamérica":           "latin america",
    }
    resultado = texto.lower()
    for es, en in traducciones.items():
        resultado = resultado.replace(es, en)
    return resultado


def _balancear_tipos(refs: list[dict], total: int) -> list[dict]:
    """Reordena para que haya variedad de tipos en el resultado final."""
    articulos = [r for r in refs if r["tipo"] == "articulo"]
    libros    = [r for r in refs if r["tipo"] == "libro"]
    tesis     = [r for r in refs if r["tipo"] == "tesis"]
    reportes  = [r for r in refs if r["tipo"] == "reporte"]

    resultado = []
    # Intercalar tipos para variedad
    pools = [articulos, libros, tesis, reportes]
    while len(resultado) < total and any(pools):
        for pool in pools:
            if pool and len(resultado) < total:
                resultado.append(pool.pop(0))
    return resultado


# ──────────────────────────────────────────────────────────────
# FORMATEADOR POR NORMA
# ──────────────────────────────────────────────────────────────
def _autores_apa(autores: list[dict], max_autores: int = 20) -> str:
    """Formatea lista de autores en estilo APA (Apellido, I.)"""
    if not autores:
        return "Autor desconocido"
    partes = []
    for a in autores[:max_autores]:
        apellido = a.get("apellido", "")
        nombre   = a.get("nombre", "")
        if nombre:
            inicial = nombre[0].upper() + "."
            partes.append(f"{apellido}, {inicial}")
        else:
            partes.append(apellido)
    if len(autores) > max_autores:
        partes.append("et al.")
    if len(partes) == 1:
        return partes[0]
    if len(partes) == 2:
        return f"{partes[0]} & {partes[1]}"
    return ", ".join(partes[:-1]) + f", & {partes[-1]}"


def _autores_apa_texto(autores: list[dict]) -> str:
    """Para citas en el texto: Apellido et al. o Apellido & Apellido"""
    if not autores:
        return "Autor"
    if len(autores) == 1:
        return autores[0].get("apellido", "Autor")
    if len(autores) == 2:
        return f"{autores[0].get('apellido')} & {autores[1].get('apellido')}"
    return f"{autores[0].get('apellido')} et al."


def _autores_icontec(autores: list[dict]) -> str:
    if not autores:
        return "AUTOR DESCONOCIDO"
    partes = []
    for a in autores[:3]:
        apellido = a.get("apellido", "").upper()
        nombre   = a.get("nombre", "")
        partes.append(f"{apellido}, {nombre}" if nombre else apellido)
    if len(autores) > 3:
        partes.append("et al.")
    return "; ".join(partes)


def _autores_ieee(autores: list[dict], idx: int) -> str:
    if not autores:
        return f"[{idx}] Autor desconocido"
    partes = []
    for a in autores[:6]:
        nombre   = a.get("nombre", "")
        apellido = a.get("apellido", "")
        inicial  = nombre[0].upper() + ". " if nombre else ""
        partes.append(f"{inicial}{apellido}")
    if len(autores) > 6:
        partes.append("et al.")
    return f"[{idx}] " + " and ".join(partes) if len(partes) <= 2 else f"[{idx}] " + ", ".join(partes[:-1]) + ", and " + partes[-1]


def _autores_vancouver(autores: list[dict]) -> str:
    if not autores:
        return "Anónimo"
    partes = []
    for a in autores[:6]:
        apellido = a.get("apellido", "")
        nombre   = a.get("nombre", "")
        iniciales = "".join(p[0].upper() for p in nombre.split() if p) if nombre else ""
        partes.append(f"{apellido} {iniciales}".strip())
    if len(autores) > 6:
        partes.append("et al")
    return ", ".join(partes)


def formatear_referencia(ref: dict, norma: str, indice: int = 1) -> str:
    """
    Formatea una referencia individual según la norma indicada.
    Devuelve la cadena lista para el documento.
    """
    tipo    = ref.get("tipo", "articulo")
    titulo  = ref.get("titulo", "Sin título")
    anio    = ref.get("anio", "s.f.")
    doi     = ref.get("doi", "")
    revista = ref.get("revista", "")
    vol     = ref.get("volumen", "")
    num     = ref.get("numero", "")
    pags    = ref.get("paginas", "")
    ed      = ref.get("editorial", "")
    autores = ref.get("autores", [])

    doi_url = f"https://doi.org/{doi}" if doi else ""

    # ── APA 7 ────────────────────────────────────────────────
    if norma in ("APA 7", "APA 6"):
        aut_str = _autores_apa(autores)
        if tipo == "articulo":
            partes = [f"{aut_str} ({anio}). {titulo}."]
            if revista:
                rev_part = f" *{revista}*"
                if vol:
                    rev_part += f", *{vol}*"
                    if num:
                        rev_part += f"({num})"
                if pags:
                    rev_part += f", {pags}"
                partes.append(rev_part + ".")
            if doi_url:
                partes.append(f" {doi_url}")
            return "".join(partes)
        else:  # libro, tesis, reporte
            linea = f"{aut_str} ({anio}). *{titulo}*."
            if ed:
                linea += f" {ed}."
            if doi_url:
                linea += f" {doi_url}"
            return linea

    # ── ICONTEC ──────────────────────────────────────────────
    elif norma == "ICONTEC":
        aut_str = _autores_icontec(autores)
        if tipo == "articulo":
            linea = f"{aut_str}. {titulo}."
            if revista:
                linea += f" En: *{revista}*."
                if vol:
                    linea += f" Vol. {vol}"
                if num:
                    linea += f", No. {num}"
                if pags:
                    linea += f"; p. {pags}"
                linea += f" ({anio})."
            if doi_url:
                linea += f" DOI: {doi_url}"
            return linea
        else:
            linea = f"{aut_str}. *{titulo}*."
            if ed:
                linea += f" {ed},"
            linea += f" {anio}."
            if doi_url:
                linea += f" Disponible en: {doi_url}"
            return linea

    # ── IEEE ─────────────────────────────────────────────────
    elif norma == "IEEE":
        aut_str = _autores_ieee(autores, indice)
        if tipo == "articulo":
            linea = f'{aut_str}, "{titulo},"'
            if revista:
                linea += f" *{revista}*,"
            if vol:
                linea += f" vol. {vol},"
            if num:
                linea += f" no. {num},"
            if pags:
                linea += f" pp. {pags},"
            linea += f" {anio}."
            if doi_url:
                linea += f" doi: {doi}"
            return linea
        else:
            linea = f'{aut_str}, *{titulo}*.'
            if ed:
                linea += f" {ed},"
            linea += f" {anio}."
            if doi_url:
                linea += f" doi: {doi}"
            return linea

    # ── Vancouver ────────────────────────────────────────────
    elif norma == "Vancouver":
        aut_str = _autores_vancouver(autores)
        if tipo == "articulo":
            linea = f"{indice}. {aut_str}. {titulo}."
            if revista:
                linea += f" {revista}."
            linea += f" {anio}"
            if vol:
                linea += f";{vol}"
                if num:
                    linea += f"({num})"
            if pags:
                linea += f":{pags}"
            linea += "."
            if doi_url:
                linea += f" doi:{doi}"
            return linea
        else:
            linea = f"{indice}. {aut_str}. {titulo}."
            if ed:
                linea += f" {ed};"
            linea += f" {anio}."
            if doi_url:
                linea += f" doi:{doi}"
            return linea

    # ── Chicago ──────────────────────────────────────────────
    elif norma == "Chicago":
        aut_str = _autores_apa(autores)  # mismo formato inicial
        if tipo == "articulo":
            linea = f"{aut_str} {anio}. \"{titulo}.\""
            if revista:
                linea += f" *{revista}*"
                if vol:
                    linea += f" {vol}"
                if num:
                    linea += f", no. {num}"
            if pags:
                linea += f": {pags}."
            else:
                linea += "."
            if doi_url:
                linea += f" {doi_url}."
            return linea
        else:
            linea = f"{aut_str} {anio}. *{titulo}*."
            if ed:
                linea += f" {ed}."
            if doi_url:
                linea += f" {doi_url}."
            return linea

    # ── MLA ──────────────────────────────────────────────────
    elif norma == "MLA":
        if autores:
            primero = autores[0]
            aut_str = primero.get("apellido", "")
            if primero.get("nombre"):
                aut_str += f", {primero['nombre']}"
            if len(autores) > 1:
                aut_str += ", et al."
        else:
            aut_str = "Anónimo"

        if tipo == "articulo":
            linea = f"{aut_str}. \"{titulo}.\""
            if revista:
                linea += f" *{revista}*,"
            if vol:
                linea += f" vol. {vol},"
            if num:
                linea += f" no. {num},"
            linea += f" {anio},"
            if pags:
                linea += f" pp. {pags}."
            if doi_url:
                linea += f" {doi_url}."
            return linea
        else:
            linea = f"{aut_str}. *{titulo}*. {ed + ',' if ed else ''} {anio}."
            if doi_url:
                linea += f" {doi_url}."
            return linea

    # ── Harvard ──────────────────────────────────────────────
    elif norma == "Harvard":
        aut_str = _autores_apa(autores)
        if tipo == "articulo":
            linea = f"{aut_str} ({anio}) '{titulo}',"
            if revista:
                linea += f" *{revista}*,"
            if vol:
                linea += f" vol. {vol},"
            if num:
                linea += f" no. {num},"
            if pags:
                linea += f" pp. {pags}."
            if doi_url:
                linea += f" Available at: {doi_url}"
            return linea
        else:
            linea = f"{aut_str} ({anio}) *{titulo}*."
            if ed:
                linea += f" {ed}."
            if doi_url:
                linea += f" Available at: {doi_url}"
            return linea

    # Fallback APA 7
    aut_str = _autores_apa(autores)
    return f"{aut_str} ({anio}). {titulo}. {ed or revista}. {doi_url}"


def formatear_referencias(refs: list[dict], norma: str) -> str:
    """
    Formatea toda la lista de referencias en el texto final.
    Ordena según lo requiere la norma (alfabético o por aparición).
    """
    if not refs:
        return "No se pudieron obtener referencias para este tema."

    # Normas con orden alfabético
    if norma in ("APA 7", "APA 6", "Harvard", "Chicago", "MLA"):
        refs = sorted(refs, key=lambda r: (
            r["autores"][0]["apellido"].lower() if r.get("autores") else "z"
        ))

    lineas = []
    for i, ref in enumerate(refs, 1):
        linea = formatear_referencia(ref, norma, indice=i)
        lineas.append(linea)

    return "\n\n".join(lineas)
