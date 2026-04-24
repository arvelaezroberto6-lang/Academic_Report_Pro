"""
referencias_reales.py
=====================
Módulo para obtener referencias bibliográficas REALES usando:
  1. CrossRef API  — artículos científicos con DOI verificado
  2. OpenAlex API  — libros, tesis, reportes institucionales
"""

import requests
import logging
import re
import time
from urllib.parse import quote

logger = logging.getLogger(__name__)

CROSSREF_URL  = "https://api.crossref.org/works"
OPENALEX_URL  = "https://api.openalex.org/works"
CONTACT_EMAIL = "academicreportpro@gmail.com"


# ──────────────────────────────────────────────────────────────
# CROSSREF
# ──────────────────────────────────────────────────────────────
def buscar_crossref(query: str, cantidad: int = 6, desde_anio: int = 2021) -> list:
    params = {
        "query":   query,
        "rows":    min(cantidad * 3, 30),
        "select":  "DOI,title,author,published,container-title,type,publisher,volume,issue,page",
        "filter":  f"from-pub-date:{desde_anio}-01-01,type:journal-article",
        "sort":    "relevance",
        "mailto":  CONTACT_EMAIL,
    }
    try:
        resp = requests.get(CROSSREF_URL, params=params, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"CrossRef HTTP {resp.status_code}")
            return []

        items = resp.json().get("message", {}).get("items", [])
        resultados = []

        for item in items:
            if not item.get("DOI"):
                continue
            titulo_list = item.get("title", [])
            if not titulo_list:
                continue
            autores_raw = item.get("author", [])
            if not autores_raw:
                continue

            pub    = item.get("published", {})
            partes = pub.get("date-parts", [[None]])[0]
            anio   = partes[0] if partes else None
            if not anio or anio < desde_anio:
                continue

            autores = []
            for a in autores_raw[:7]:
                apellido = a.get("family", "")
                nombre   = a.get("given", "")
                if apellido:
                    autores.append({"apellido": apellido, "nombre": nombre})

            revista_list = item.get("container-title", [])
            revista = revista_list[0] if revista_list else ""

            resultados.append({
                "tipo":    "articulo",
                "titulo":  titulo_list[0],
                "autores": autores,
                "anio":    anio,
                "revista": revista,
                "volumen": item.get("volume", ""),
                "numero":  item.get("issue", ""),
                "paginas": item.get("page", ""),
                "doi":     item.get("DOI", ""),
                "fuente":  "crossref",
            })

            if len(resultados) >= cantidad:
                break

        logger.info(f"CrossRef: {len(resultados)} artículos para '{query[:40]}'")
        return resultados

    except Exception as e:
        logger.error(f"Error CrossRef: {e}")
        return []


# ──────────────────────────────────────────────────────────────
# OPENALEX
# ──────────────────────────────────────────────────────────────
def buscar_openalex(query: str, cantidad: int = 6,
                   tipos: list = None, desde_anio: int = 2021) -> list:
    if tipos is None:
        tipos = ["book", "dissertation", "report"]

    filtros = [
        f"publication_year:>{desde_anio - 1}",
        f"type:{'|'.join(tipos)}",
    ]

    params = {
        "search":   query,
        "filter":   ",".join(filtros),
        "per-page": min(cantidad * 3, 25),
        "select":   "id,title,authorships,publication_year,type,primary_location,biblio,doi",
        "sort":     "relevance_score:desc",
        "mailto":   CONTACT_EMAIL,
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

            loc        = item.get("primary_location") or {}
            fuente_inf = loc.get("source") or {}
            editorial  = fuente_inf.get("display_name", "")

            doi_raw = item.get("doi", "") or ""
            doi     = doi_raw.replace("https://doi.org/", "").strip()

            tipo_raw = item.get("type", "book")
            tipo_map = {
                "book":            "libro",
                "dissertation":    "tesis",
                "report":          "reporte",
                "journal-article": "articulo",
            }
            tipo = tipo_map.get(tipo_raw, "libro")

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
def buscar_referencias_reales(tema: str, cantidad_total: int = 12) -> list:
    referencias = []

    # Artículos (CrossRef)
    arts = buscar_crossref(tema, cantidad=6, desde_anio=2021)
    referencias.extend(arts)
    time.sleep(0.3)

    if len(arts) < 3:
        arts_en = buscar_crossref(_traducir_query(tema), cantidad=5, desde_anio=2021)
        dois_existentes = {r["doi"] for r in referencias if r.get("doi")}
        for a in arts_en:
            if a.get("doi") not in dois_existentes:
                referencias.append(a)
        time.sleep(0.3)

    # Libros/tesis (OpenAlex)
    libros = buscar_openalex(tema, cantidad=4, tipos=["book", "dissertation"], desde_anio=2021)
    referencias.extend(libros)
    time.sleep(0.3)

    # Si pocos libros, buscar en inglés
    if len(libros) < 2:
        libros_en = buscar_openalex(_traducir_query(tema), cantidad=3, tipos=["book"], desde_anio=2021)
        titulos_existentes = {r["titulo"].lower()[:40] for r in referencias}
        for l in libros_en:
            if l["titulo"].lower()[:40] not in titulos_existentes:
                referencias.append(l)
        time.sleep(0.3)

    # Reportes (OpenAlex)
    reportes = buscar_openalex(tema, cantidad=3, tipos=["report"], desde_anio=2021)
    referencias.extend(reportes)
    time.sleep(0.3)

    # Deduplicar por título
    vistos = set()
    unicas = []
    for ref in referencias:
        clave = re.sub(r'\W+', '', ref["titulo"].lower())[:60]
        if clave not in vistos:
            vistos.add(clave)
            unicas.append(ref)

    # Filtrar por relevancia temática ANTES de balancear
    unicas = _filtrar_por_relevancia(unicas, tema, umbral=0.15)

    unicas = _balancear_tipos(unicas, cantidad_total)
    logger.info(f"Total referencias reales: {len(unicas)}")
    return unicas[:cantidad_total]


def _traducir_query(texto: str) -> str:
    traducciones = {
        "inteligencia artificial": "artificial intelligence",
        "educación":    "education",
        "tecnología":   "technology",
        "salud":        "health",
        "economía":     "economy",
        "medio ambiente": "environment",
        "cambio climático": "climate change",
        "seguridad":    "security",
        "datos":        "data",
        "aprendizaje":  "learning",
        "universidad":  "university",
        "investigación": "research",
        "desarrollo":   "development",
        "colombia":     "colombia",
        "latinoamérica": "latin america",
        "sociedad":     "society",
        "política":     "policy",
        "cultura":      "culture",
        "historia":     "history",
        "ciencia":      "science",
        "matemáticas":  "mathematics",
        "física":       "physics",
        "química":      "chemistry",
        "biología":     "biology",
        "medicina":     "medicine",
        "derecho":      "law",
        "psicología":   "psychology",
        "sociología":   "sociology",
        "comunicación": "communication",
        "arte":         "art",
        "literatura":   "literature",
        "filosofía":    "philosophy",
    }
    resultado = texto.lower()
    for es, en in traducciones.items():
        resultado = resultado.replace(es, en)
    return resultado


def _balancear_tipos(refs: list, total: int) -> list:
    articulos = [r for r in refs if r["tipo"] == "articulo"]
    libros    = [r for r in refs if r["tipo"] == "libro"]
    tesis     = [r for r in refs if r["tipo"] == "tesis"]
    reportes  = [r for r in refs if r["tipo"] == "reporte"]

    resultado = []
    pools = [articulos, libros, tesis, reportes]
    while len(resultado) < total and any(pools):
        for pool in pools:
            if pool and len(resultado) < total:
                resultado.append(pool.pop(0))
    return resultado



def _puntaje_relevancia(titulo: str, tema: str) -> float:
    """
    Puntúa qué tan relevante es un título respecto al tema buscado.
    Devuelve 0.0 (irrelevante) a 1.0 (muy relevante).
    """
    titulo_lower = titulo.lower()
    tema_lower   = tema.lower()

    # Palabras clave del tema (ignorar stopwords)
    stopwords = {"de", "del", "la", "el", "los", "las", "en", "y", "a", "para",
                 "con", "por", "que", "una", "un", "su", "se", "es", "al"}
    palabras_tema = [p for p in re.split(r'\W+', tema_lower) if p and p not in stopwords and len(p) > 2]

    if not palabras_tema:
        return 0.5  # sin info suficiente, aceptar

    coincidencias = sum(1 for p in palabras_tema if p in titulo_lower)
    score = coincidencias / len(palabras_tema)

    # Bonus si coincide el tema completo o fragmentos de 2+ palabras
    for i in range(len(palabras_tema) - 1):
        bigram = palabras_tema[i] + " " + palabras_tema[i+1]
        if bigram in titulo_lower:
            score += 0.3

    return min(score, 1.0)


def _filtrar_por_relevancia(refs: list, tema: str, umbral: float = 0.15) -> list:
    """
    Descarta referencias cuyo título no tenga relación con el tema.
    Ordena por relevancia descendente.
    """
    puntuadas = []
    for ref in refs:
        score = _puntaje_relevancia(ref.get("titulo", ""), tema)
        puntuadas.append((score, ref))
        logger.debug(f"  Relevancia {score:.2f} — {ref['titulo'][:60]}")

    # Filtrar las que no llegan al umbral
    relevantes = [(s, r) for s, r in puntuadas if s >= umbral]

    # Si quedan menos de 5, bajar el umbral a la mitad para no quedarse sin refs
    if len(relevantes) < 5:
        umbral_bajo = umbral / 2
        relevantes = [(s, r) for s, r in puntuadas if s >= umbral_bajo]
        logger.warning(f"Pocas referencias relevantes, bajando umbral a {umbral_bajo:.2f}")

    # Ordenar por score desc
    relevantes.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in relevantes]


# ──────────────────────────────────────────────────────────────
# FORMATEADORES POR NORMA
# ──────────────────────────────────────────────────────────────
def _autores_apa(autores: list, max_autores: int = 20) -> str:
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


def _autores_icontec(autores: list) -> str:
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


def _autores_ieee(autores: list, idx: int) -> str:
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
    prefijo = f"[{idx}] "
    if len(partes) <= 2:
        return prefijo + " and ".join(partes)
    return prefijo + ", ".join(partes[:-1]) + ", and " + partes[-1]


def _autores_vancouver(autores: list) -> str:
    if not autores:
        return "Anónimo"
    partes = []
    for a in autores[:6]:
        apellido  = a.get("apellido", "")
        nombre    = a.get("nombre", "")
        iniciales = "".join(p[0].upper() for p in nombre.split() if p) if nombre else ""
        partes.append(f"{apellido} {iniciales}".strip())
    if len(autores) > 6:
        partes.append("et al.")
    return ", ".join(partes)


def _sentence_case(titulo: str) -> str:
    """
    APA 7 requiere sentence case en títulos de artículos:
    solo primera letra en mayúscula y nombres propios.
    Preserva mayúsculas después de ':' (subtítulos).
    """
    if not titulo:
        return titulo
    # Capitalizar después de ': ' para subtítulos
    partes = re.split(r'(:\s+)', titulo)
    resultado = []
    for i, parte in enumerate(partes):
        if re.match(r':\s+', parte):
            resultado.append(parte)
        elif i == 0 or (i > 0 and re.match(r':\s+', partes[i-1])):
            # Primera letra mayúscula, resto minúscula (excepto siglas de 2+ mayúsculas)
            if len(parte) > 1:
                resultado.append(parte[0].upper() + parte[1:].lower())
            else:
                resultado.append(parte.upper())
        else:
            resultado.append(parte)
    return "".join(resultado)


def formatear_referencia(ref: dict, norma: str, indice: int = 1) -> str:
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

    # APA 7 / APA 6
    if norma in ("APA 7", "APA 6"):
        aut_str = _autores_apa(autores)
        if tipo == "articulo":
            # APA 7: título en sentence case (sin cursiva), revista en cursiva
            titulo_fmt = _sentence_case(titulo)
            partes = [f"{aut_str} ({anio}). {titulo_fmt}."]
            if revista:
                rev_part = f" {revista}"  # revista en cursiva (se aplica en PDF/Word)
                if vol:
                    rev_part += f", {vol}"
                    if num:
                        rev_part += f"({num})"
                if pags:
                    rev_part += f", {pags}"
                partes.append(rev_part + ".")
            if doi_url:
                partes.append(f" {doi_url}")
            return "".join(partes)
        else:
            titulo_fmt = _sentence_case(titulo)
            linea = f"{aut_str} ({anio}). {titulo_fmt}."
            if ed:
                linea += f" {ed}."
            if doi_url:
                linea += f" {doi_url}"
            return linea

    # ICONTEC
    elif norma == "ICONTEC":
        aut_str = _autores_icontec(autores)
        if tipo == "articulo":
            linea = f"{aut_str}. {titulo}."
            if revista:
                linea += f" En: {revista}."
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
            linea = f"{aut_str}. {titulo}."
            if ed:
                linea += f" {ed},"
            linea += f" {anio}."
            if doi_url:
                linea += f" Disponible en: {doi_url}"
            return linea

    # IEEE
    elif norma == "IEEE":
        aut_str = _autores_ieee(autores, indice)
        if tipo == "articulo":
            linea = f'{aut_str}, "{titulo},"'
            if revista:
                linea += f" {revista},"
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
            linea = f'{aut_str}, {titulo}.'
            if ed:
                linea += f" {ed},"
            linea += f" {anio}."
            if doi_url:
                linea += f" doi: {doi}"
            return linea

    # Vancouver
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

    # Chicago
    elif norma == "Chicago":
        aut_str = _autores_apa(autores)
        if tipo == "articulo":
            titulo_fmt = _sentence_case(titulo)
            linea = f'{aut_str} {anio}. "{titulo_fmt}."'
            if revista:
                linea += f" {revista}"
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
            titulo_fmt = _sentence_case(titulo)
            linea = f"{aut_str} {anio}. {titulo_fmt}."
            if ed:
                linea += f" {ed}."
            if doi_url:
                linea += f" {doi_url}."
            return linea

    # MLA
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
            linea = f'{aut_str}. "{titulo}."'
            if revista:
                linea += f" {revista},"
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
            linea = f"{aut_str}. {titulo}. {ed + ',' if ed else ''} {anio}."
            if doi_url:
                linea += f" {doi_url}."
            return linea

    # Harvard
    elif norma == "Harvard":
        aut_str = _autores_apa(autores)
        if tipo == "articulo":
            linea = f"{aut_str} ({anio}) '{titulo}',"
            if revista:
                linea += f" {revista},"
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
            linea = f"{aut_str} ({anio}) {titulo}."
            if ed:
                linea += f" {ed}."
            if doi_url:
                linea += f" Available at: {doi_url}"
            return linea

    # Fallback APA
    aut_str = _autores_apa(autores)
    return f"{aut_str} ({anio}). {titulo}. {ed or revista}. {doi_url}"


def formatear_referencias(refs: list, norma: str) -> str:
    if not refs:
        return "No se pudieron obtener referencias para este tema."

    if norma in ("APA 7", "APA 6", "Harvard", "Chicago", "MLA"):
        refs = sorted(refs, key=lambda r: (
            r["autores"][0]["apellido"].lower() if r.get("autores") else "z"
        ))

    lineas = []
    for i, ref in enumerate(refs, 1):
        linea = formatear_referencia(ref, norma, indice=i)
        lineas.append(linea)

    return "\n\n".join(lineas)
