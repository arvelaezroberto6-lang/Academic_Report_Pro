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

# ── Año mínimo dinámico: siempre los últimos 5 años ──────────
from datetime import datetime as _dt
_ANIO_MINIMO = _dt.now().year - 5   # e.g. 2026 - 5 = 2021, se recalcula al iniciar


# ──────────────────────────────────────────────────────────────
# CROSSREF
# ──────────────────────────────────────────────────────────────
def buscar_crossref(query: str, cantidad: int = 6, desde_anio: int = None) -> list:
    if desde_anio is None:
        desde_anio = _ANIO_MINIMO
    params = {
        "query":   query,
        "rows":    min(cantidad * 5, 50),   # más candidatos para filtrar mejor
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
                   tipos: list = None, desde_anio: int = None) -> list:
    if desde_anio is None:
        desde_anio = _ANIO_MINIMO
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
def buscar_referencias_reales(tema: str, cantidad_total: int = 12,
                              contenido_informe: str = "") -> list:
    """
    Busca referencias reales en CrossRef y OpenAlex.

    Args:
        tema: Tema principal del informe.
        cantidad_total: Número máximo de referencias a devolver.
        contenido_informe: Texto generado del informe (introducción + desarrollo +
                           marco teórico). Si se proporciona, se usa para extraer
                           conceptos clave adicionales y re-puntuar la relevancia
                           de las referencias contra el contenido real.
    """
    referencias = []
    tema_en = _traducir_query(tema)
    mismo_idioma = tema_en.strip() == tema.lower().strip()

    # Enriquecer el query con términos de contexto según el tema detectado
    tema_enriquecido_es = _enriquecer_query(tema)
    tema_en = _traducir_query(tema)
    tema_enriquecido_en = _enriquecer_query_en(tema, tema_en)

    # ── Si hay contenido del informe, enriquecer el query con sus conceptos clave ──
    query_contenido_es = tema_enriquecido_es
    query_contenido_en = tema_enriquecido_en
    if contenido_informe and contenido_informe.strip():
        conceptos_extra = _extraer_conceptos_de_contenido(contenido_informe, tema)
        if conceptos_extra:
            query_contenido_es = f"{tema_enriquecido_es} {' '.join(conceptos_extra[:4])}"
            conceptos_en = [_traducir_query(c) for c in conceptos_extra[:4]]
            query_contenido_en = f"{tema_enriquecido_en} {' '.join(conceptos_en)}"
            logger.info(f"Query enriquecido con contenido: '{query_contenido_es[:80]}'")

    # Paso 1: Artículos en español (query enriquecido con contenido)
    arts_es = buscar_crossref(query_contenido_es, cantidad=8)
    referencias.extend(arts_es)
    time.sleep(0.3)

    # Paso 2: Artículos en inglés
    arts_en = buscar_crossref(query_contenido_en, cantidad=8)
    dois_existentes = {r["doi"] for r in referencias if r.get("doi")}
    for a in arts_en:
        if a.get("doi") not in dois_existentes:
            referencias.append(a)
    time.sleep(0.3)

    # Paso 3: Libros/tesis en español
    libros_es = buscar_openalex(query_contenido_es, cantidad=4, tipos=["book", "dissertation"])
    referencias.extend(libros_es)
    time.sleep(0.3)

    # Paso 4: Libros en inglés
    if not mismo_idioma:
        titulos_existentes = {r["titulo"].lower()[:40] for r in referencias}
        libros_en = buscar_openalex(query_contenido_en, cantidad=4, tipos=["book"])
        for l in libros_en:
            if l["titulo"].lower()[:40] not in titulos_existentes:
                referencias.append(l)
        time.sleep(0.3)

    # Paso 5: Reportes
    reportes = buscar_openalex(query_contenido_en, cantidad=3, tipos=["report"])
    referencias.extend(reportes)
    time.sleep(0.3)

    # Deduplicar
    vistos = set()
    unicas = []
    for ref in referencias:
        clave = re.sub(r'\W+', '', ref["titulo"].lower())[:60]
        if clave not in vistos:
            vistos.add(clave)
            unicas.append(ref)

    # ── Filtrar por relevancia ──────────────────────────────────
    # Si hay contenido del informe, puntuar contra él (más preciso).
    # Si no, puntuar solo contra el tema (comportamiento anterior).
    # Umbral 0.35: exige que el título comparta al menos 2 conceptos
    # con el informe, descartando referencias temáticamente ajenas.
    texto_referencia = contenido_informe if contenido_informe.strip() else tema
    unicas = _filtrar_por_relevancia(unicas, texto_referencia, umbral=0.35)
    unicas = _balancear_tipos(unicas, cantidad_total)
    logger.info(f"Total referencias reales: {len(unicas)}")
    return unicas[:cantidad_total]


def _extraer_conceptos_de_contenido(contenido: str, tema: str) -> list:
    """
    Extrae los conceptos más frecuentes y relevantes del contenido generado
    del informe, excluyendo stopwords y términos genéricos.
    Devuelve lista de hasta 6 términos clave adicionales al tema.
    """
    stopwords = {
        "de", "del", "la", "el", "los", "las", "en", "y", "a", "para", "con",
        "por", "que", "una", "un", "su", "se", "es", "al", "lo", "como", "más",
        "sus", "desde", "hacia", "entre", "sobre", "este", "esta", "estos",
        "estas", "hay", "son", "fue", "han", "ser", "sido", "también", "donde",
        "cuando", "pero", "sin", "bien", "así", "ante", "bajo", "cada", "durante",
        "mientras", "tanto", "muy", "puede", "pueden", "debe", "deben", "tiene",
        "tienen", "the", "and", "for", "with", "from", "into", "that", "this",
        "are", "was", "has", "have", "been", "its", "their", "which", "however",
        "therefore", "although", "according", "through", "within", "between",
        "informe", "según", "mediante", "través", "través", "además",
    }
    _GENERICOS = {
        "colombia", "colombian", "nacional", "general", "social", "public",
        "analysis", "study", "review", "research", "impact", "effect", "results",
        "impacto", "efectos", "estudio", "análisis", "revisión", "caso",
        "primer", "segundo", "tercero", "primero", "objetivo", "desarrollo",
        "conclusion", "introducción", "marco", "teórico", "metodología",
    }

    # Tomar solo los primeros 3000 chars para eficiencia
    muestra = contenido[:3000].lower()
    # Eliminar citas y números
    muestra = re.sub(r'\([^)]{0,50}\d{4}[^)]{0,20}\)', ' ', muestra)
    muestra = re.sub(r'\d+', ' ', muestra)

    palabras = re.split(r'\W+', muestra)
    palabras = [p for p in palabras if p and len(p) > 4
                and p not in stopwords and p not in _GENERICOS]

    # Palabras del tema para no repetirlas
    tema_palabras = set(re.split(r'\W+', tema.lower()))

    # Contar frecuencias
    freq: dict = {}
    for p in palabras:
        if p not in tema_palabras:
            freq[p] = freq.get(p, 0) + 1

    # Ordenar por frecuencia y devolver los más comunes
    ordenados = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [p for p, _ in ordenados[:6] if freq[p] >= 2]



# ──────────────────────────────────────────────────────────────
# ENRIQUECIMIENTO DE QUERY
# ──────────────────────────────────────────────────────────────
# Mapa de palabras clave del tema → términos de contexto adicionales
# que hacen el query más específico y mejoran la relevancia
_CONTEXTO_POR_TEMA = {
    "invasora":         "biodiversidad ecosistema impacto ecológico",
    "invasive":         "biodiversity ecosystem ecological impact",
    "biodiversidad":    "conservación especies ecosistema",
    "biodiversity":     "conservation species ecosystem",
    "deforestación":    "bosque cobertura vegetal amazonia",
    "deforestation":    "forest cover vegetation loss",
    "cambio climático": "temperatura emisiones carbono",
    "climate change":   "temperature emissions carbon",
    "salud pública":    "epidemiología enfermedad prevención",
    "public health":    "epidemiology disease prevention",
    "inteligencia artificial": "machine learning algoritmo datos",
    "artificial intelligence": "machine learning algorithm deep learning",
    "educación":        "aprendizaje pedagógico enseñanza",
    "education":        "learning pedagogical teaching",
    "economía":         "crecimiento mercado productividad",
    "economy":          "growth market productivity",
    "contaminación":    "residuos tóxicos ambiente agua",
    "pollution":        "waste toxic environment water",
    "genética":         "ADN genoma secuenciación",
    "genetics":         "DNA genome sequencing",
    "minería":          "extracción recursos impacto ambiental",
    "mining":           "extraction resources environmental impact",
    "agua":             "recurso hídrico cuenca calidad",
    "water":            "resource basin quality hydrological",
}


def _enriquecer_query(tema: str) -> str:
    """
    Añade términos de contexto al query según el tema para mejorar
    la especificidad de las búsquedas en CrossRef / OpenAlex.
    """
    tema_lower = tema.lower()
    extras = []
    for clave, contexto in _CONTEXTO_POR_TEMA.items():
        if clave in tema_lower and contexto not in tema_lower:
            extras.append(contexto)
            break  # un solo bloque de contexto es suficiente
    if extras:
        return f"{tema} {' '.join(extras)}"
    return tema


def _enriquecer_query_en(tema_original: str, tema_traducido: str) -> str:
    """
    Detecta el contexto desde el tema en español y añade términos EN al query traducido.
    Así el query inglés queda limpio sin mezcla de idiomas.
    """
    tema_lower = tema_original.lower()
    # Mapa ES → contexto EN (solo las claves en español)
    contexto_en = {
        "invasora":         "biodiversity ecosystem ecological impact",
        "invasoras":        "biodiversity ecosystem ecological impact",
        "biodiversidad":    "conservation species ecosystem",
        "deforestación":    "forest cover vegetation loss",
        "cambio climático": "temperature emissions carbon",
        "salud pública":    "epidemiology disease prevention",
        "inteligencia artificial": "machine learning algorithm deep learning",
        "educación":        "learning pedagogical teaching",
        "economía":         "growth market productivity",
        "contaminación":    "waste toxic environment water",
        "genética":         "DNA genome sequencing",
        "minería":          "extraction resources environmental impact",
        "agua":             "resource basin quality hydrological",
    }
    for clave_es, ctx_en in contexto_en.items():
        if clave_es in tema_lower and ctx_en not in tema_traducido:
            return f"{tema_traducido} {ctx_en}"
    return tema_traducido


def _traducir_query(texto: str) -> str:
    """Traduce palabras clave del español al inglés para búsquedas en CrossRef/OpenAlex."""
    traducciones = {
        # Medio ambiente / biología
        "especies invasoras": "invasive species",
        "especie invasora": "invasive species",
        "invasión biológica": "biological invasion",
        "invasiones biológicas": "biological invasions",
        "biodiversidad": "biodiversity",
        "ecosistema": "ecosystem",
        "ecosistemas": "ecosystems",
        "deforestación": "deforestation",
        "cambio climático": "climate change",
        "medio ambiente": "environment",
        "ecología": "ecology",
        "conservación": "conservation",
        "contaminación": "pollution",
        "sostenibilidad": "sustainability",
        "recursos naturales": "natural resources",
        "agua": "water",
        "energía renovable": "renewable energy",
        "servicios ecosistémicos": "ecosystem services",
        "servicios ambientales": "environmental services",
        "flora": "flora",
        "fauna": "fauna",
        "bosque": "forest",
        "selva": "rainforest",
        "páramo": "paramo",
        "humedal": "wetland",
        "cuenca": "watershed",
        "biodiversidad marina": "marine biodiversity",
        # Salud
        "salud pública": "public health",
        "salud": "health",
        "medicina": "medicine",
        "pandemia": "pandemic",
        "vacuna": "vaccine",
        "epidemia": "epidemic",
        "enfermedad": "disease",
        "nutrición": "nutrition",
        "psicología": "psychology",
        "meningitis": "meningitis",
        "zoonosis": "zoonosis",
        # Tecnología
        "inteligencia artificial": "artificial intelligence",
        "aprendizaje automático": "machine learning",
        "aprendizaje profundo": "deep learning",
        "tecnología": "technology",
        "ciberseguridad": "cybersecurity",
        "blockchain": "blockchain",
        "datos": "data",
        "automatización": "automation",
        "robótica": "robotics",
        "computación": "computing",
        "redes": "networks",
        "nube": "cloud",
        "algoritmo": "algorithm",
        "red neuronal": "neural network",
        # Educación
        "educación superior": "higher education",
        "educación universitaria": "university education",
        "educación": "education",
        "aprendizaje": "learning",
        "enseñanza": "teaching",
        "pedagogía": "pedagogy",
        "universidad": "university",
        "estudiante": "student",
        "currículo": "curriculum",
        # Economía / finanzas / derecho
        "aseguradoras": "insurance companies",
        "aseguradora": "insurer",
        "seguros": "insurance",
        "seguro": "insurance",
        "responsabilidad civil": "civil liability",
        "responsabilidad": "liability",
        "regalías": "royalties",
        "tributario": "tax",
        "fiscal": "fiscal",
        "financiero": "financial",
        "finanzas": "finance",
        "economía": "economy",
        "mercado": "market",
        "empresa": "enterprise",
        "inflación": "inflation",
        "desempleo": "unemployment",
        "pobreza": "poverty",
        "desigualdad": "inequality",
        "migración": "migration",
        "conflicto": "conflict",
        "paz": "peace",
        "derechos humanos": "human rights",
        "contrato": "contract",
        "indemnización": "indemnity",
        "siniestro": "claim",
        "activos": "assets",
        "inversión": "investment",
        "banca": "banking",
        # Minería / extracción
        "minería ilegal": "illegal mining",
        "minería artesanal": "artisanal mining",
        "minería": "mining",
        "extracción minera": "mineral extraction",
        "extracción": "extraction",
        "petróleo": "oil",
        "hidrocarburos": "hydrocarbons",
        "carbón": "coal",
        "oro": "gold",
        "comunidades indígenas": "indigenous communities",
        "pueblos indígenas": "indigenous peoples",
        "indígenas": "indigenous",
        "campesinos": "peasants",
        "territorio": "territory",
        "territorios": "territories",
        # Ciencias / derecho / otros
        "química": "chemistry",
        "física": "physics",
        "biología": "biology",
        "laboratorio": "laboratory",
        "genética": "genetics",
        "genómica": "genomics",
        "derecho ambiental": "environmental law",
        "derecho": "law",
        "política pública": "public policy",
        "sociedad": "society",
        "cultura": "culture",
        "historia": "history",
        "ciencia": "science",
        "matemáticas": "mathematics",
        "filosofía": "philosophy",
        "comunicación": "communication",
        "arte": "art",
        "literatura": "literature",
        "investigación": "research",
        "desarrollo sostenible": "sustainable development",
        "desarrollo": "development",
        "colombia": "colombia",
        "latinoamérica": "latin america",
        "seguridad alimentaria": "food security",
        "seguridad": "security",
        "política": "policy",
        "sociología": "sociology",
        "trabajo": "labor",
        "género": "gender",
        "violencia": "violence",
        "corrupción": "corruption",
        "gobernanza": "governance",
        "participación": "participation",
        "derechos": "rights",
    }
    resultado = texto.lower()
    # Reemplazar frases primero (más específicas), luego palabras sueltas
    for es, en in sorted(traducciones.items(), key=lambda x: -len(x[0])):
        resultado = resultado.replace(es, en)
    return resultado



# Sinónimos y variantes por término — permiten que títulos con vocabulario
# relacionado (pero no idéntico) también obtengan score de relevancia.
# Clave = palabra del tema (EN) → lista de variantes aceptadas en títulos.
_SINONIMOS_EN = {
    "invasive":     ["invasion", "invasions", "invasiveness", "invader", "invaders", "introduced", "exotic", "alien"],
    "species":      ["species", "organism", "organisms", "taxa", "taxon", "flora", "fauna"],
    "biodiversity": ["biodiversity", "diversity", "richness", "biota", "wildlife"],
    "ecosystem":    ["ecosystem", "ecosystems", "habitat", "habitats", "ecology", "ecological"],
    "colombia":     ["colombia", "colombian", "andean", "neotropical"],
    "deforestation":["deforestation", "forest loss", "forest cover", "deforested", "logging"],
    "climate":      ["climate", "climatic", "temperature", "warming", "greenhouse"],
    "health":       ["health", "disease", "epidemiology", "medical", "clinical", "public health"],
    "education":    ["education", "educational", "learning", "teaching", "academic", "university", "school"],
    "artificial":   ["artificial", "machine learning", "deep learning", "neural", "algorithmic", "automated"],
    "intelligence": ["intelligence", "intelligent", "cognitive", "computational"],
    "water":        ["water", "aquatic", "hydrological", "watershed", "river", "lake"],
    "insurance":    ["insurance", "insurer", "liability", "indemnity", "underwriting", "actuarial", "claim", "siniestro"],
    "financial":    ["financial", "finance", "fiscal", "monetary", "economic", "banking"],
    "pollution":    ["pollution", "contamination", "pollutant", "emissions", "waste"],
    "mining":       ["mining", "extraction", "mineral", "quarry", "excavation", "gold", "coal", "oil"],
    "genetics":     ["genetics", "genomics", "genome", "dna", "rna", "sequence"],
    "agriculture":  ["agriculture", "agricultural", "farming", "crop", "cultivation", "agronomy"],
    "security":     ["security", "cybersecurity", "cyber", "threat", "vulnerability", "attack"],
    "conflict":     ["conflict", "war", "violence", "peace", "armed", "dispute"],
    "migration":    ["migration", "migrant", "immigrant", "displacement", "refugee"],
    "poverty":      ["poverty", "inequality", "socioeconomic", "deprivation", "marginalization"],
    "indigenous":   ["indigenous", "native", "tribal", "community", "territory", "ancestral"],
    "liability":    ["liability", "insurance", "indemnity", "actuarial", "claim", "underwriting"],
}

# Lo mismo para palabras en español
_SINONIMOS_ES = {
    "invasora":      ["invasora", "invasoras", "invasión", "invasiones", "exótica", "exóticas", "introducida"],
    "especie":       ["especie", "especies", "organismo", "organismos", "taxa", "flora", "fauna"],
    "biodiversidad": ["biodiversidad", "diversidad", "riqueza", "biota", "vida silvestre"],
    "ecosistema":    ["ecosistema", "ecosistemas", "hábitat", "ecología", "ecológico"],
    "colombia":      ["colombia", "colombiano", "colombiana", "andino", "neotropical"],
    "deforestación": ["deforestación", "tala", "cobertura forestal", "pérdida bosque"],
    "clima":         ["clima", "climático", "temperatura", "calentamiento", "emisiones"],
    "salud":         ["salud", "enfermedad", "epidemiología", "médico", "clínico", "sanitario"],
    "educación":     ["educación", "educativo", "aprendizaje", "enseñanza", "académico", "universitario"],
    "inteligencia":  ["inteligencia", "machine learning", "aprendizaje automático", "red neuronal"],
    "agua":          ["agua", "acuático", "hidrológico", "cuenca", "río", "lago"],
    "seguros":       ["seguros", "aseguradoras", "asegurador", "responsabilidad", "indemnización", "siniestro", "póliza", "riesgo asegurado"],
    "financiero":    ["financiero", "finanzas", "fiscal", "monetario", "bancario", "tributario", "regalías"],
    "contaminación": ["contaminación", "contaminante", "emisiones", "residuos", "vertimiento"],
    "minería":       ["minería", "extracción", "mineral", "canteras", "excavación", "oro", "carbón", "petróleo", "hidrocarburos"],
    "genética":      ["genética", "genómica", "genoma", "adn", "arn", "secuenciación"],
    "agricultura":   ["agricultura", "agrícola", "cultivo", "cosecha", "agronomía", "campesino"],
    "seguridad":     ["seguridad", "ciberseguridad", "amenaza", "vulnerabilidad", "ataque"],
    "conflicto":     ["conflicto", "guerra", "violencia", "paz", "armado", "disputa"],
    "migración":     ["migración", "migrante", "inmigrante", "desplazamiento", "refugiado"],
    "pobreza":       ["pobreza", "desigualdad", "socioeconómico", "marginación"],
    "indígenas":     ["indígenas", "indígena", "comunidades", "pueblos", "territorio", "ancestral", "étnico"],
    "responsabilidad": ["responsabilidad", "seguros", "aseguradoras", "indemnización", "siniestro", "póliza"],
}


def _palabras_clave_tema(tema: str) -> tuple[list, list]:
    """
    Devuelve (palabras_es, palabras_en) — términos del tema en ambos idiomas,
    sin stopwords, longitud > 3, expandidos con sinónimos y variantes.
    Esto permite que títulos con vocabulario relacionado también obtengan
    score de relevancia, sin depender de coincidencias exactas de palabras.
    """
    stopwords_es = {"de", "del", "la", "el", "los", "las", "en", "y", "a", "para",
                    "con", "por", "que", "una", "un", "su", "se", "es", "al", "lo",
                    "como", "más", "sus", "desde", "hacia", "entre", "sobre"}
    stopwords_en = {"the", "and", "for", "with", "from", "into", "that", "this",
                    "are", "was", "has", "have", "been", "its", "their"}

    tema_es = tema.lower()
    tema_en = _traducir_query(tema_es)

    palabras_es_base = [p for p in re.split(r'\W+', tema_es)
                        if p and p not in stopwords_es and len(p) > 3]
    palabras_en_base = [p for p in re.split(r'\W+', tema_en)
                        if p and p not in stopwords_en and len(p) > 3]

    # Expandir con sinónimos
    palabras_es = list(palabras_es_base)
    for p in palabras_es_base:
        for clave, variantes in _SINONIMOS_ES.items():
            if p in variantes or p == clave:
                palabras_es.extend(variantes)
                break

    palabras_en = list(palabras_en_base)
    for p in palabras_en_base:
        for clave, variantes in _SINONIMOS_EN.items():
            if p in variantes or p == clave:
                palabras_en.extend(variantes)
                break

    # Deduplicar manteniendo orden
    palabras_es = list(dict.fromkeys(palabras_es))
    palabras_en = list(dict.fromkeys(palabras_en))

    return palabras_es, palabras_en


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
    Puntúa la relevancia de un título respecto al tema del informe.

    Funciona en dos modos:
    - Texto corto (tema ≤ 200 chars): usa todas las palabras del tema como conceptos.
    - Texto largo (contenido del informe): extrae los conceptos más frecuentes
      para no generar ruido con palabras irrelevantes del cuerpo del texto.
    """
    titulo_lower = titulo.lower()

    # ── Modo contenido largo: extraer conceptos del texto ──────
    if len(tema) > 200:
        # Reusar _extraer_conceptos_de_contenido si está disponible,
        # o hacer una extracción rápida aquí mismo
        stopwords_ext = {
            "de", "del", "la", "el", "los", "las", "en", "y", "a", "para", "con",
            "por", "que", "una", "un", "su", "se", "es", "al", "lo", "como", "más",
            "sus", "desde", "hacia", "entre", "sobre", "este", "esta", "estos",
            "estas", "hay", "son", "fue", "han", "ser", "sido", "también", "donde",
            "cuando", "pero", "sin", "bien", "así", "ante", "bajo", "cada",
            "mientras", "tanto", "muy", "puede", "pueden", "debe", "deben", "tiene",
            "tienen", "the", "and", "for", "with", "from", "into", "that", "this",
            "are", "was", "has", "have", "been", "its", "their", "which",
            "informe", "según", "mediante", "además", "objetivo", "desarrollo",
            "conclusion", "introducción", "marco", "metodología", "general",
            "análisis", "estudio", "revisión", "impacto", "efectos", "caso",
        }
        muestra = re.sub(r'\([^)]{0,60}\)', ' ', tema[:4000]).lower()
        muestra = re.sub(r'\d+', ' ', muestra)
        palabras = re.split(r'\W+', muestra)
        freq: dict = {}
        for p in palabras:
            if p and len(p) > 4 and p not in stopwords_ext:
                freq[p] = freq.get(p, 0) + 1
        # Tomar los 12 términos más frecuentes como conceptos del informe
        conceptos_tema = [p for p, c in sorted(freq.items(), key=lambda x: -x[1])
                         if c >= 2][:12]
        if not conceptos_tema:
            return 0.5

        # Score: fracción de conceptos del informe presentes en el título
        cubiertos = 0
        for c in conceptos_tema:
            vars_es = []
            vars_en = []
            for clave, variantes in _SINONIMOS_ES.items():
                if c == clave or c in variantes:
                    vars_es = [clave] + variantes
                    break
            for clave, variantes in _SINONIMOS_EN.items():
                if c == clave or c in variantes:
                    vars_en = [clave] + variantes
                    break
            todas_vars = set(vars_es + vars_en + [c])
            if any(v in titulo_lower for v in todas_vars):
                cubiertos += 1

        score = cubiertos / len(conceptos_tema)

        # Penalty: si el título no comparte ningún término con los conceptos
        if cubiertos == 0:
            return 0.0

        # Bonus por bigramas
        conceptos_list = conceptos_tema
        for i in range(len(conceptos_list) - 1):
            if conceptos_list[i] + " " + conceptos_list[i+1] in titulo_lower:
                score += 0.2

        return min(score, 1.0)

    # ── Modo tema corto: lógica original ───────────────────────

    # Conceptos = palabras base del tema (sin sinónimos aún), > 4 chars
    # Excluir términos geográficos/genéricos que no discriminan el área temática
    _TERMINOS_GENERICOS = {
        "colombia", "colombian", "latin", "america", "american", "global",
        "nacional", "regional", "local", "general", "social", "public",
        "analysis", "study", "review", "research", "impact", "effect",
        "impacto", "efectos", "estudio", "análisis", "revisión", "caso",
    }
    conceptos_es = [p for p in re.split(r'\W+', tema.lower())
                    if p and len(p) > 4 and p not in {
                        "de", "del", "la", "el", "los", "las", "en", "y",
                        "para", "con", "por", "que", "una", "un", "su", "se",
                        "como", "más", "sus", "desde", "hacia", "entre", "sobre"}
                    and p not in _TERMINOS_GENERICOS]
    tema_en_base = _traducir_query(tema.lower())
    conceptos_en = [p for p in re.split(r'\W+', tema_en_base)
                    if p and len(p) > 4 and p not in {
                        "the", "and", "for", "with", "from", "into", "that",
                        "this", "are", "was", "has", "have", "been", "its"}
                    and p not in _TERMINOS_GENERICOS]

    todos_conceptos = list(dict.fromkeys(conceptos_es + conceptos_en))
    if not todos_conceptos:
        return 0.5

    # Para cada concepto, construir su grupo de variantes aceptables
    def variantes_de(concepto: str, sinonimos: dict) -> list:
        for clave, vars_ in sinonimos.items():
            if concepto == clave or concepto in vars_:
                return [clave] + vars_
        return [concepto]

    # Score: fracción de conceptos del tema cubiertos en el título
    cubiertos = 0
    for c in todos_conceptos:
        vars_es = variantes_de(c, _SINONIMOS_ES)
        vars_en = variantes_de(c, _SINONIMOS_EN)
        todas_variantes = set(vars_es + vars_en + [c])
        if any(v in titulo_lower for v in todas_variantes):
            cubiertos += 1

    score = cubiertos / len(todos_conceptos)

    # Bonus por bigramas exactos del tema en el título
    for i in range(len(conceptos_en) - 1):
        if conceptos_en[i] + " " + conceptos_en[i + 1] in titulo_lower:
            score += 0.25
    for i in range(len(conceptos_es) - 1):
        if conceptos_es[i] + " " + conceptos_es[i + 1] in titulo_lower:
            score += 0.25

    # Penalty por extrañeza: si casi todas las palabras del título son ajenas
    todas_variantes_tema = set()
    for c in todos_conceptos:
        todas_variantes_tema.update(variantes_de(c, _SINONIMOS_ES))
        todas_variantes_tema.update(variantes_de(c, _SINONIMOS_EN))

    palabras_titulo = [p for p in re.split(r'\W+', titulo_lower) if p and len(p) > 4]
    if palabras_titulo:
        ajenas = sum(1 for p in palabras_titulo if p not in todas_variantes_tema)
        ratio_ajenas = ajenas / len(palabras_titulo)
        if ratio_ajenas > 0.85:
            score *= max(0.1, 1 - (ratio_ajenas - 0.85) * 3)

    return min(score, 1.0)


def _filtrar_por_relevancia(refs: list, tema: str, umbral: float = 0.25) -> list:
    """
    Filtra referencias por relevancia respecto al tema del informe.

    Sin blacklists estáticas — funciona para cualquier tema.
    Umbral 0.25: exige que el título comparta al menos 1 concepto con el tema
    (con sinónimos incluidos). CrossRef ya pre-ordena por relevancia semántica,
    así que los primeros resultados suelen ser los más pertinentes.

    Si hay pocas referencias con umbral principal, baja gradualmente hasta 0.10.
    Score 0.0 = ningún concepto del tema aparece → siempre descartado.
    """
    puntuadas = []
    for ref in refs:
        titulo = ref.get("titulo", "")
        score = _puntaje_relevancia(titulo, tema)
        puntuadas.append((score, ref))
        logger.debug(f"  Relevancia {score:.2f} — {titulo[:60]}")

    # Score 0.0 = ningún concepto del tema en el título → siempre descartar
    puntuadas = [(s, r) for s, r in puntuadas if s > 0.0]

    relevantes = [(s, r) for s, r in puntuadas if s >= umbral]

    # Si quedan pocas, bajar gradualmente — pero nunca por debajo de 0.15
    # para no incluir referencias sin relación real con el tema
    if len(relevantes) < 6:
        for umbral_reducido in (0.25, 0.15):
            relevantes = [(s, r) for s, r in puntuadas if s >= umbral_reducido]
            if len(relevantes) >= 4:
                logger.warning(f"Umbral reducido a {umbral_reducido} — {len(relevantes)} refs")
                break

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
