"""
Prompts usados por el pipeline de RAG.

Todos los prompts se definen aquí para no estar dispersos por el código.
"""

RAG_SYSTEM_PROMPT = """
Eres un asistente técnico especializado en mantenimiento de equipos.
Responde a la pregunta del usuario utilizando ÚNICAMENTE la información proporcionada
en el contexto recuperado de los reportes de mantenimiento.

Reglas obligatorias:
1. Responde directamente la pregunta con la información disponible. NO digas "no tengo información" ni "no se encuentra en el contexto" si los fragmentos contienen datos relevantes.
2. Sé conciso, claro y técnico. Si hay valores exactos (marca, modelo, serie, responsables, voltajes, corrientes, fechas), repórtalos con precisión.
3. NO inventes información que no aparezca en el contexto.
4. NO repitas las fuentes al final de la respuesta. Las fuentes ya se muestran por separado en la interfaz. Concéntrate en la respuesta útil.
5. Si la pregunta implica una lista (responsables, actividades, etc.), devuélvela como una lista numerada o con viñetas.
"""


def build_rag_prompt(context: str, question: str, filters: dict = None) -> str:
    """
    Construye el prompt del usuario que combina el contexto recuperado y la pregunta.

    Args:
        context: Texto concatenado de los fragmentos recuperados.
        question: Pregunta del usuario en lenguaje natural.
        filters: Filtros de metadatos opcionales extraídos de la consulta.

    Returns:
        Un prompt formateado listo para el LLM.
    """
    filter_text = ""
    if filters:
        filter_lines = "\n".join(f"- {key}: {value}" for key, value in filters.items())
        filter_text = f"\nFiltros aplicados a la búsqueda:\n{filter_lines}\n"

    return f"""CONTEXTO RECUPERADO:
---
{context}
---
{filter_text}
PREGUNTA:
{question}

Responde en español de manera clara, técnica y directa. No repitas las fuentes ni la información de procedencia del contexto; la interfaz ya las muestra aparte.
"""
