"""Utilidades de división de texto para documentos de reportes de mantenimiento."""
from typing import List, Dict, Any
import uuid
from django.conf import settings


# Nombres canónicos de secciones usados en los metadatos de Qdrant y en el analizador de consultas.
SECTION_NORMALIZATION = {
    "Información General del Equipo": [
        "informacion general", "datos generales", "datos del equipo",
    ],
    "Historial de Mantenimientos": [
        "historial de mantenimientos", "historial mantenimientos", "historial de servicios",
    ],
    "Actividades Realizadas": [
        "actividades realizadas", "actividades ejecutadas", "trabajos realizados",
    ],
    "Cálculos y Mediciones": [
        "calculos y mediciones", "calculos", "mediciones", "calculos y mediciones realizadas",
        "mediciones realizadas",
    ],
    "Diagnóstico Técnico": [
        "diagnostico tecnico", "diagnostico", "diagnóstico",
    ],
    "Recomendaciones": [
        "recomendaciones", "acciones sugeridas", "seguimiento",
    ],
    "Responsable": [
        "responsable", "responsables", "datos del responsable", "tecnico responsable",
    ],
}


def _normalize_section_name(section_name: str) -> str:
    """Asigna un nombre de sección analizado a uno canónico mediante coincidencia de palabras clave."""
    if not section_name:
        return ""
    normalized = section_name.lower().strip()
    normalized = (
        normalized.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )

    for canonical, keywords in SECTION_NORMALIZATION.items():
        for keyword in keywords:
            if keyword in normalized:
                return canonical
    return section_name


class TextSplitter:
    """
    Divide una sección de texto en fragmentos superpuestos.

    El tamaño de los fragmentos y la superposición se leen de la configuración de Django,
    lo que facilita ajustarlos sin modificar el código.
    """

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def split(self, text: str) -> List[str]:
        """
        Divide el texto en fragmentos de como máximo ``chunk_size`` caracteres con
        ``chunk_overlap`` caracteres de superposición.

        Args:
            text: Texto a dividir.

        Returns:
            Lista de fragmentos.
        """
        text = text.strip()
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            # Intenta terminar en un salto de párrafo para preservar el significado
            if end < len(text):
                paragraph_break = text.rfind("\n\n", start, end)
                if paragraph_break > start + self.chunk_size // 2:
                    end = paragraph_break + 2

            chunks.append(text[start:end].strip())
            start = end - self.chunk_overlap
            if start < 0:
                start = 0
            if start >= len(text):
                break

        return chunks


class DocumentChunker:
    """
    Genera fragmentos a partir de un documento analizado preservando sus metadatos.
    """

    def __init__(self):
        self.splitter = TextSplitter()

    def chunk_document(
        self,
        document_id: int,
        parsed_data: Dict[str, Any],
        fallback_text: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Divide cada sección de un documento analizado en fragmentos.

        Args:
            document_id: Clave primaria de la instancia Document de Django.
            parsed_data: Documento estructurado producido por ``DocumentParser``.
            fallback_text: Texto sin procesar opcional para usar si no se generan secciones.

        Returns:
            Lista de diccionarios de fragmentos con metadatos y contenido.
        """
        chunks = []
        metadata = {
            "document_id": document_id,
            "tipo_equipo": parsed_data.get("tipo_equipo", ""),
            "marca": parsed_data.get("marca", ""),
            "modelo": parsed_data.get("modelo", ""),
            "numero_serie": parsed_data.get("numero_serie", ""),
            "codigo_interno": parsed_data.get("codigo_interno", ""),
            "ubicacion": parsed_data.get("ubicacion", ""),
            "fecha_mantenimiento": parsed_data.get("fecha_mantenimiento", ""),
        }

        chunk_index = 0
        for section in parsed_data.get("secciones", []):
            section_name = _normalize_section_name(section.get("nombre", ""))
            section_text = section.get("contenido", "")
            if not section_text.strip():
                continue

            section_chunks = self.splitter.split(section_text)
            for section_chunk in section_chunks:
                chunk_metadata = dict(metadata)
                chunk_metadata["seccion"] = section_name
                chunk_metadata["pagina"] = 1  # Valor provisional; el mapeo de páginas puede mejorarse más adelante
                chunk_metadata["chunk_index"] = chunk_index
                chunks.append({
                    "id": str(uuid.uuid4()),
                    "metadata": chunk_metadata,
                    "content": section_chunk,
                })
                chunk_index += 1

        # Respaldo: si el LLM no produjo secciones utilizables, divide el texto sin procesar
        if not chunks and fallback_text:
            print(f"[Document {document_id}] No se analizaron secciones; se usará el texto sin procesar como respaldo.")
            for section_chunk in self.splitter.split(fallback_text):
                chunk_metadata = dict(metadata)
                chunk_metadata["seccion"] = "Contenido completo"
                chunk_metadata["pagina"] = 1
                chunk_metadata["chunk_index"] = chunk_index
                chunks.append({
                    "id": str(uuid.uuid4()),
                    "metadata": chunk_metadata,
                    "content": section_chunk,
                })
                chunk_index += 1

        return chunks
