# ========== GENERACIÓN CON DEEPSEEK (reemplaza Groq) ==========
def generar_informe_con_ia(tema, tipo_informe="academico", info_extra="", norma="apa7"):
    """Genera informe usando DeepSeek API (estable y económico)"""
    
    if not DEEPSEEK_API_KEY:
        logger.warning("❌ No hay API key de DeepSeek configurada, usando contenido genérico")
        return None

    logger.info(f"🤖 Generando informe con DeepSeek - tipo '{tipo_informe}' sobre: {tema[:80]}...")
    
    # Construir prompt según tipo de informe (igual que lo tienes, no lo cambio)
    prompts = {
        "laboratorio": f"""Genera un INFORME DE LABORATORIO completo, profesional y detallado sobre: "{tema}"

Información adicional del usuario: {info_extra if info_extra else 'No se proporcionaron datos específicos'}

⚠️ ESTRUCTURA OBLIGATORIA (debe seguirse exactamente):

**1. INTRODUCCIÓN**
- Objetivo del experimento (2-3 párrafos)
- Fundamento teórico detallado
- Hipótesis planteada

**2. MATERIALES Y REACTIVOS**
- Lista completa de materiales de laboratorio
- Reactivos químicos utilizados con concentraciones
- Equipos e instrumentos de medición

**3. PROCEDIMIENTO EXPERIMENTAL**
- Descripción paso a paso (mínimo 8 pasos)
- Precauciones de seguridad
- Controles positivos y negativos
- Tiempo y temperatura de cada etapa

**4. RESULTADOS**
- Tabla de resultados observados
- Datos cuantitativos (si aplica)
- Fotografías o esquemas descriptivos (mencionar)

**5. DISCUSIÓN**
- Análisis detallado de resultados
- Comparación con valores teóricos
- Explicación de reacciones químicas o procesos
- Errores y factores que afectaron resultados

**6. CONCLUSIONES**
- Mínimo 5 conclusiones específicas y numeradas
- Relacionar con los objetivos planteados
- Validación o rechazo de hipótesis

**7. RECOMENDACIONES**
- 3-4 sugerencias para mejorar el experimento
- Aplicaciones prácticas

**8. REFERENCIAS**
- 5-6 fuentes bibliográficas en formato {NORMAS_CONFIG.get(norma, NORMAS_CONFIG['apa7'])['nombre']}

IMPORTANTE: Escribe en español con tono técnico-profesional. Usa **negritas** para títulos y subtítulos.""",

        "empresarial": f"""Genera un INFORME EJECUTIVO completo y profesional sobre: "{tema}"

Contexto adicional: {info_extra if info_extra else 'Sin información adicional'}

**ESTRUCTURA OBLIGATORIA:**

**RESUMEN EJECUTIVO**
- Síntesis de hallazgos clave (1 página)
- Recomendaciones principales

**1. INTRODUCCIÓN**
- Contexto empresarial
- Propósito del informe
- Alcance y limitaciones

**2. ANÁLISIS DE SITUACIÓN**
- Análisis FODA (Fortalezas, Oportunidades, Debilidades, Amenazas)
- Análisis de mercado
- Análisis de competencia
- Indicadores clave de desempeño (KPIs)

**3. OPORTUNIDADES Y AMENAZAS**
- Identificación de oportunidades de negocio
- Riesgos y amenazas potenciales
- Análisis de tendencias del sector

**4. RECOMENDACIONES ESTRATÉGICAS**
- Estrategias a corto plazo (0-6 meses)
- Estrategias a mediano plazo (6-12 meses)
- Estrategias a largo plazo (1-3 años)
- Plan de implementación

**5. PROYECCIONES FINANCIERAS**
- Estimaciones de inversión
- Retorno de inversión esperado (ROI)
- Análisis costo-beneficio

**6. CONCLUSIONES**
- 5 conclusiones principales
- Próximos pasos

**7. REFERENCIAS**
- Fuentes consultadas en formato {NORMAS_CONFIG.get(norma, NORMAS_CONFIG['apa7'])['nombre']}

Escribe en español con tono ejecutivo profesional.""",

        "tesis": f"""Genera una estructura completa de TESIS/MONOGRAFÍA sobre: "{tema}"

Información adicional: {info_extra if info_extra else 'Sin información adicional'}

**ESTRUCTURA OBLIGATORIA:**

**RESUMEN**
- Abstract en español (250 palabras)
- Palabras clave (5-7 términos)

**1. INTRODUCCIÓN**
- Contextualización del tema
- Justificación de la investigación
- Antecedentes relevantes

**2. PLANTEAMIENTO DEL PROBLEMA**
- Descripción del problema
- Formulación del problema (pregunta de investigación)
- Delimitación espacial y temporal

**3. OBJETIVOS**
- Objetivo general (1)
- Objetivos específicos (4-5)

**4. HIPÓTESIS**
- Hipótesis general
- Hipótesis específicas
- Variables: dependientes e independientes

**5. MARCO TEÓRICO**
- Bases teóricas fundamentales
- Teorías relacionadas
- Definición de términos básicos
- Marco conceptual

**6. METODOLOGÍA**
- Tipo y diseño de investigación
- Población y muestra
- Técnicas e instrumentos de recolección
- Procedimiento de investigación
- Análisis de datos

**7. RESULTADOS ESPERADOS**
- Descripción de resultados anticipados
- Posibles hallazgos
- Limitaciones del estudio

**8. CRONOGRAMA**
- Fases de la investigación
- Tiempos estimados

**9. PRESUPUESTO**
- Recursos humanos
- Recursos materiales
- Costos estimados

**10. CONCLUSIONES PRELIMINARES**
- 5 conclusiones basadas en el marco teórico

**11. REFERENCIAS**
- Mínimo 15 fuentes en formato {NORMAS_CONFIG.get(norma, NORMAS_CONFIG['apa7'])['nombre']}

Escribe en español académico formal."""
    }
    
    # Prompt por defecto (académico)
    prompt_default = f"""Genera un INFORME ACADÉMICO completo, riguroso y profesional sobre: "{tema}"

Información adicional proporcionada: {info_extra if info_extra else 'Sin información adicional'}

**ESTRUCTURA OBLIGATORIA:**

**INTRODUCCIÓN**
- Contextualización del tema (2-3 párrafos)
- Justificación e importancia
- Planteamiento inicial

**OBJETIVOS**
- 1 objetivo general claro y específico
- 4-5 objetivos específicos medibles

**MARCO TEÓRICO**
- Fundamentos teóricos detallados
- Conceptos clave explicados
- Antecedentes y estado del arte
- Teorías relacionadas

**METODOLOGÍA**
- Tipo de investigación y diseño
- Población y muestra (con números específicos)
- Técnicas de recolección de datos
- Procedimiento detallado
- Análisis de datos

**DESARROLLO**
- Presentación de resultados con datos
- Análisis e interpretación
- Tablas o gráficos (describir en texto)
- Discusión de hallazgos

**CONCLUSIONES**
- Mínimo 5 conclusiones específicas y numeradas
- Relacionadas con los objetivos
- Basadas en evidencia del desarrollo

**RECOMENDACIONES**
- 3-4 recomendaciones prácticas y específicas
- Para investigadores futuros
- Para aplicación práctica

**REFERENCIAS**
- 6-8 fuentes bibliográficas académicas
- Formato: {NORMAS_CONFIG.get(norma, NORMAS_CONFIG['apa7'])['nombre']}
- Incluir libros, artículos y fuentes digitales

REQUISITOS:
- Escribe en español académico formal
- Usa **negritas** para todos los títulos y subtítulos
- Proporciona contenido sustancial (no solo títulos)
- Incluye datos específicos cuando sea posible
- Mantén coherencia y cohesión entre secciones"""

    prompt = prompts.get(tipo_informe, prompt_default)
    
    # Headers para DeepSeek
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",  # DeepSeek V3.2
        "messages": [
            {
                "role": "system",
                "content": "Eres un asistente académico experto en redactar informes profesionales. Generas contenido detallado, riguroso y bien estructurado en español."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 6000,
        "temperature": 0.7,
        "top_p": 0.9
    }
    
    try:
        logger.info("📡 Enviando solicitud a DeepSeek API...")
        response = requests.post(
            DEEPSEEK_URL,
            headers=headers,
            json=data,
            timeout=120
        )
        
        if response.status_code == 200:
            resultado = response.json()
            contenido = resultado['choices'][0]['message']['content']
            contenido = limpiar_texto(contenido)
            
            logger.info(f"✅ Contenido generado exitosamente ({len(contenido)} caracteres)")
            
            # Extraer secciones según tipo de informe
            if tipo_informe == "laboratorio":
                secciones = {
                    'introduccion': extraer_seccion(contenido, '1. INTRODUCCIÓN') or extraer_seccion(contenido, 'INTRODUCCIÓN'),
                    'materiales': extraer_seccion(contenido, '2. MATERIALES Y REACTIVOS') or extraer_seccion(contenido, 'MATERIALES'),
                    'procedimiento': extraer_seccion(contenido, '3. PROCEDIMIENTO EXPERIMENTAL') or extraer_seccion(contenido, 'PROCEDIMIENTO'),
                    'resultados': extraer_seccion(contenido, '4. RESULTADOS'),
                    'discusion': extraer_seccion(contenido, '5. DISCUSIÓN') or extraer_seccion(contenido, 'DISCUSIÓN'),
                    'conclusiones': extraer_seccion(contenido, '6. CONCLUSIONES') or extraer_seccion(contenido, 'CONCLUSIONES'),
                    'recomendaciones': extraer_seccion(contenido, '7. RECOMENDACIONES') or extraer_seccion(contenido, 'RECOMENDACIONES'),
                    'referencias': extraer_seccion(contenido, '8. REFERENCIAS') or extraer_seccion(contenido, 'REFERENCIAS')
                }
            else:
                secciones = {
                    'introduccion': extraer_seccion(contenido, 'INTRODUCCIÓN'),
                    'objetivos': extraer_seccion(contenido, 'OBJETIVOS'),
                    'marco_teorico': extraer_seccion(contenido, 'MARCO TEÓRICO'),
                    'metodologia': extraer_seccion(contenido, 'METODOLOGÍA'),
                    'desarrollo': extraer_seccion(contenido, 'DESARROLLO') or extraer_seccion(contenido, 'RESULTADOS'),
                    'conclusiones': extraer_seccion(contenido, 'CONCLUSIONES'),
                    'recomendaciones': extraer_seccion(contenido, 'RECOMENDACIONES'),
                    'referencias': extraer_seccion(contenido, 'REFERENCIAS')
                }
            
            # Validar y completar secciones vacías
            contenido_respaldo = contenido_local_generico(tema, tipo_informe)
            for key in secciones:
                if not secciones[key] or len(secciones[key]) < 50:
                    logger.warning(f"⚠️ Sección '{key}' vacía o muy corta, usando contenido genérico")
                    secciones[key] = contenido_respaldo.get(key, "")
            
            logger.info(f"✅ Informe tipo '{tipo_informe}' generado correctamente con DeepSeek")
            return secciones
            
        else:
            logger.error(f"❌ Error con DeepSeek: HTTP {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("⏱️ Timeout: DeepSeek tardó más de 120 segundos")
        return None
    except Exception as e:
        logger.error(f"❌ Error con DeepSeek: {str(e)}")
        return None
