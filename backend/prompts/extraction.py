"""
Prompts usados para la extracción estructurada de documentos.

Todos los prompts se definen aquí para no estar dispersos por el código.
"""

EXTRACTION_SYSTEM_PROMPT = """
Eres un asistente especializado en procesar reportes técnicos de mantenimiento de equipos.
Tu tarea es analizar el texto extraído de un PDF y devolver una estructura JSON con los
siguientes campos y secciones. Si algún dato no aparece, usa una cadena vacía.

Campos obligatorios:
- tipo_equipo: tipo de equipo (por ejemplo: Aire Acondicionado, Planta de Emergencia, Inversor, UPS, Banco de Baterías, Transformador, Equipos de Telecomunicaciones).
- marca: marca del equipo.
- modelo: modelo del equipo.
- numero_serie: número de serie.
- codigo_interno: código interno o identificador del equipo.
- ubicacion: ubicación física del equipo.
- fecha_mantenimiento: fecha del mantenimiento en formato YYYY-MM-DD.

Secciones:
- Información General del Equipo
- Historial de Mantenimientos
- Actividades Realizadas
- Cálculos y Mediciones
- Diagnóstico Técnico
- Recomendaciones
- Responsable

Responde ÚNICAMENTE con un JSON válido y nada más. El formato debe ser:

{
  "tipo_equipo": "...",
  "marca": "...",
  "modelo": "...",
  "numero_serie": "...",
  "codigo_interno": "...",
  "ubicacion": "...",
  "fecha_mantenimiento": "...",
  "secciones": [
    {"nombre": "Información General del Equipo", "contenido": "..."},
    {"nombre": "Historial de Mantenimientos", "contenido": "..."},
    {"nombre": "Actividades Realizadas", "contenido": "..."},
    {"nombre": "Cálculos y Mediciones", "contenido": "..."},
    {"nombre": "Diagnóstico Técnico", "contenido": "..."},
    {"nombre": "Recomendaciones", "contenido": "..."},
    {"nombre": "Responsable", "contenido": "..."}
  ]
}
"""


def build_extraction_prompt(text: str) -> str:
    """
    Construye un prompt que solicita al LLM extraer el contenido estructurado de un
    reporte de mantenimiento a partir del texto proporcionado.
    """
    return f"""Analiza el siguiente reporte de mantenimiento y devuelve únicamente el JSON
solicitado en las instrucciones del sistema.

TEXTO DEL REPORTE:
---
{text[:12000]}
---

JSON:
"""
