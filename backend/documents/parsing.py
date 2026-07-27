"""Análisis estructurado de reportes de mantenimiento usando un LLM."""
import json
import re
from typing import Dict, Any, List
from datetime import datetime
from llm.adapter import LLMService
from prompts.extraction import EXTRACTION_SYSTEM_PROMPT, build_extraction_prompt


class DocumentParser:
    """
    Analiza el texto de un reporte de mantenimiento en una representación estructurada.

    El analizador usa un LLM para identificar secciones y metadatos. Si el LLM no
    produce un JSON válido, recurre a una estructura básica con el texto sin procesar.
    """

    KNOWN_SECTIONS = [
        "Información General del Equipo",
        "Historial de Mantenimientos",
        "Actividades Realizadas",
        "Cálculos y Mediciones",
        "Diagnóstico Técnico",
        "Recomendaciones",
        "Responsable",
    ]

    def __init__(self):
        # Usa un modelo más ligero para la extracción y acelerar la indexación.
        from django.conf import settings
        self.llm = LLMService(model=getattr(settings, "EXTRACTION_LLM_MODEL", None))

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Analiza el texto completo de un reporte de mantenimiento.

        Args:
            text: Texto extraído del PDF.

        Returns:
            Diccionario con metadatos y una lista de secciones.
        """
        prompt = build_extraction_prompt(text)
        try:
            raw_response = self.llm.generate(
                prompt=prompt,
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
            )
            return self._parse_llm_response(raw_response, text)
        except Exception as exc:
            return self._fallback_parse(text, error=str(exc))

    def _parse_llm_response(self, raw_response: str, original_text: str) -> Dict[str, Any]:
        """Intenta extraer un objeto JSON de la respuesta del LLM."""
        json_str = self._extract_json(raw_response)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            return self._fallback_parse(original_text, error=f"JSON inválido: {exc}")

        return self._normalize_data(data, original_text)

    def _extract_json(self, text: str) -> str:
        """
        Extrae el primer objeto JSON de una cadena.

        El LLM puede envolver el JSON en bloques de markdown o en texto adicional.
        """
        # Intentar bloque de código cerrado
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if match:
            return match.group(1)

        # Intentar primer objeto
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            return match.group(1)

        return text

    def _normalize_data(self, data: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """Normaliza el JSON analizado al esquema esperado."""
        normalized = {
            "tipo_equipo": self._clean_str(data.get("tipo_equipo", "")),
            "marca": self._clean_str(data.get("marca", "")),
            "modelo": self._clean_str(data.get("modelo", "")),
            "numero_serie": self._clean_str(data.get("numero_serie", "")),
            "codigo_interno": self._clean_str(data.get("codigo_interno", "")),
            "ubicacion": self._clean_str(data.get("ubicacion", "")),
            "fecha_mantenimiento": self._parse_date(data.get("fecha_mantenimiento", "")),
            "secciones": [],
        }

        sections = data.get("secciones", [])
        if isinstance(sections, list):
            for section in sections:
                if isinstance(section, dict):
                    normalized["secciones"].append({
                        "nombre": self._clean_str(section.get("nombre", "")),
                        "contenido": self._clean_str(section.get("contenido", "")),
                    })

        # Si no se extrajeron secciones, recurre a fragmentos del texto sin procesar
        if not normalized["secciones"]:
            return self._fallback_parse(original_text)

        return normalized

    def _fallback_parse(self, text: str, error: str = "") -> Dict[str, Any]:
        """
        Analizador de respaldo cuando el LLM falla.

        Intenta extraer los campos clave con expresiones regulares y devuelve
        una única sección con el texto sin procesar si no es posible extraer secciones.
        """
        metadata = self._heuristic_metadata(text)
        sections = self._heuristic_sections(text)

        if not sections:
            sections = [{"nombre": "Contenido completo", "contenido": text}]

        return {
            "tipo_equipo": metadata.get("tipo_equipo", ""),
            "marca": metadata.get("marca", ""),
            "modelo": metadata.get("modelo", ""),
            "numero_serie": metadata.get("numero_serie", ""),
            "codigo_interno": metadata.get("codigo_interno", ""),
            "ubicacion": metadata.get("ubicacion", ""),
            "fecha_mantenimiento": metadata.get("fecha_mantenimiento"),
            "secciones": sections,
            "error": error,
        }

    def _heuristic_metadata(self, text: str) -> Dict[str, Any]:
        """Extrae metadatos básicos usando expresiones regulares."""
        metadata: Dict[str, Any] = {}

        # Línea de encabezado: Fecha: ... | Código: ... | Equipo: ...
        header_match = re.search(
            r"Fecha:\s*(?P<fecha>[^|]+)\s*\|\s*C[oó]digo:\s*(?P<codigo>[^|]+)\s*\|\s*Equipo:\s*(?P<equipo>.+)",
            text,
            re.IGNORECASE,
        )
        if header_match:
            metadata["fecha_mantenimiento"] = self._parse_date(header_match.group("fecha").strip())
            metadata["codigo_interno"] = header_match.group("codigo").strip()
            metadata["tipo_equipo"] = header_match.group("equipo").strip()

        # Valores de la tabla de información general
        patterns = {
            "marca": r"Marca\s+(.+)",
            "modelo": r"Modelo\s+(.+)",
            "numero_serie": r"N[uú]mero de serie\s+(.+)",
            "codigo_interno": r"C[oó]digo interno\s+(.+)",
            "ubicacion": r"Ubicaci[oó]n\s+(.+)",
        }

        for field, pattern in patterns.items():
            if field not in metadata or not metadata[field]:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    metadata[field] = match.group(1).strip()

        return metadata

    def _heuristic_sections(self, text: str) -> List[Dict[str, str]]:
        """Extrae secciones mediante encabezados numerados cuando sea posible."""
        # Coincide con encabezados como "1. INFORMACIÓN GENERAL DEL EQUIPO"
        section_pattern = re.compile(
            r"^\s*\d+\.\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-zéíóúáñô\s]+?)(?:\n|\r|$)",
            re.MULTILINE,
        )
        matches = list(section_pattern.finditer(text))
        if not matches:
            return []

        sections: List[Dict[str, str]] = []
        for index, match in enumerate(matches):
            name = match.group(1).strip()
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            content = text[start:end].strip()

            # Elimina el encabezado "Campo Valor" de las tablas si está presente
            content = re.sub(r"^Campo\s+Valor\s*\n", "", content, flags=re.IGNORECASE)
            if content:
                sections.append({"nombre": name, "contenido": content})

        return sections

    def _clean_str(self, value: Any) -> str:
        """Convierte un valor en una cadena sin espacios en blanco al inicio ni al final."""
        if value is None:
            return ""
        return str(value).strip()

    def _parse_date(self, value: Any) -> str:
        """
        Analiza una cadena de fecha y la convierte al formato ISO YYYY-MM-DD.

        Devuelve una cadena vacía si el análisis falla.
        """
        value = self._clean_str(value)
        if not value:
            return ""
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

