"""Análisis de consultas para recuperación consciente de metadatos.

Este módulo extrae filtros estructurados de una pregunta en lenguaje natural para
que el recuperador de RAG pueda acotar la búsqueda a los fragmentos más relevantes.

"""
import re
from typing import Dict, Any, List, Optional


# Valores normalizados usados tanto en los metadatos de Qdrant como en el analizador de consultas.
SECTION_NAMES = [
    "Información General del Equipo",
    "Historial de Mantenimientos",
    "Actividades Realizadas",
    "Cálculos y Mediciones",
    "Diagnóstico Técnico",
    "Recomendaciones",
    "Responsable",
]

EQUIPMENT_TYPES = [
    "Aire Acondicionado",
    "Planta de Emergencia",
    "Inversor",
]

SECTION_KEYWORDS = {
    "Información General del Equipo": [
        "informacion general", "datos generales", "marca", "modelo",
        "año fabricacion", "estado del equipo",
    ],
    "Responsable": [
        "responsable", "responsables", "tecnico", "tecnico responsable", "quien realizo",
        "quien atendio", "quien ejecuto", "quien lidero", "encargado",
    ],
    "Historial de Mantenimientos": [
        "historial", "mantenimientos", "servicios", "fecha", "tipo de mantenimiento",
        "estado del mantenimiento", "ultimo servicio",
    ],
    "Actividades Realizadas": [
        "actividades", "trabajos", "trabajos ejecutados", "componentes revisados",
        "componentes reemplazados", "repuestos", "ajustes",
    ],
    "Cálculos y Mediciones": [
        "calculos", "mediciones", "calculos y mediciones", "parametros", "voltaje",
        "corriente", "potencia", "frecuencia", "temperatura", "presion", "horometro",
        "consumo electrico", "eficiencia",
    ],
    "Diagnóstico Técnico": [
        "diagnostico", "diagnostico tecnico", "estado general", "condiciones de operacion",
        "fallas", "fallas detectadas",
    ],
    "Recomendaciones": [
        "recomendaciones", "acciones sugeridas", "proximos mantenimientos", "seguimiento",
    ],
}

# Normaliza variaciones de plural/sinónimos al tipo de equipo canónico.
EQUIPMENT_KEYWORDS = {
    "Aire Acondicionado": [
        "aire acondicionado", "aires acondicionados", "mini split", "split",
    ],
    "Planta de Emergencia": [
        "planta de emergencia", "plantas de emergencia", "planta emergencia",
        "generador", "generadores",
    ],
    "Inversor": [
        "inversor", "inversores",
    ],
    "UPS": [
        "ups", "sai", "no break",
    ],
    "Banco de Baterías": [
        "banco de baterias", "baterias", "bateria",
    ],
    "Transformador": [
        "transformador", "transformadores",
    ],
    "Equipos de Telecomunicaciones": [
        "telecomunicaciones", "equipo de telecomunicaciones", "radio", "switch",
    ],
}


def _normalize_text(text: str) -> str:
    """Devuelve una versión en minúsculas y sin tildes del texto."""
    text = text.lower()
    accents = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n", "ü": "u",
    }
    for accented, plain in accents.items():
        text = text.replace(accented, plain)
    return text


class QueryAnalyzer:
    """
    Extrae filtros de una pregunta del usuario.

    Filtros soportados:
    - numero_serie
    - codigo_interno
    - tipo_equipo
    - seccion
    """

    def analyze(self, question: str) -> Dict[str, Any]:
        """
        Analiza la pregunta y devuelve un diccionario de filtros compatibles con Qdrant.

        Solo se devuelven filtros de igualdad. Si no se encuentra un valor, la clave
        se omite.
        """
        filters: Dict[str, Any] = {}
        normalized = _normalize_text(question)

        numero_serie = self._extract_numero_serie(question)
        if numero_serie:
            filters["numero_serie"] = numero_serie

        codigo_interno = self._extract_codigo_interno(question)
        if codigo_interno:
            filters["codigo_interno"] = codigo_interno

        tipo_equipo = self._extract_tipo_equipo(normalized)
        # Un número de serie o código interno explícito es un identificador más fuerte que el
        # tipo de equipo mencionado en la pregunta. Incluir un filtro de tipo incorrecto
        # (por ejemplo, el usuario dice "UPS" pero el código pertenece a un aire acondicionado) puede
        # producir cero resultados, así que omitimos el tipo cuando hay un identificador presente.
        if tipo_equipo and not (numero_serie or codigo_interno):
            filters["tipo_equipo"] = tipo_equipo

        seccion = self._extract_seccion(normalized)
        if seccion:
            filters["seccion"] = seccion

        return filters

    def _extract_numero_serie(self, text: str) -> Optional[str]:
        """Extrae un número de serie como SN1399635851."""
        match = re.search(r"SN\d+", text, re.IGNORECASE)
        if match:
            return match.group(0).upper()
        return None

    def _extract_codigo_interno(self, text: str) -> Optional[str]:
        """Extrae un código interno como EQ-366-WZY."""
        match = re.search(r"EQ-[A-Z0-9-]+", text, re.IGNORECASE)
        if match:
            return match.group(0).upper()
        return None

    def _extract_tipo_equipo(self, normalized: str) -> Optional[str]:
        """Asigna palabras clave de equipo al tipo canónico."""
        for canonical, keywords in EQUIPMENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in normalized:
                    return canonical
        return None

    def _extract_seccion(self, normalized: str) -> Optional[str]:
        """Asigna palabras clave de sección al nombre canónico de sección."""
        for canonical, keywords in SECTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in normalized:
                    return canonical
        return None


# Función de conveniencia para uso directo.
def analyze_query(question: str) -> Dict[str, Any]:
    """Devuelve los filtros de metadatos extraídos de una pregunta del usuario."""
    return QueryAnalyzer().analyze(question)
