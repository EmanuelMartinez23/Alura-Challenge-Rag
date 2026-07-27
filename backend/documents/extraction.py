"""Utilidades para extraer texto de archivos PDF."""
from typing import List, Dict, Any
from pathlib import Path
import pdfplumber


class PDFExtractionError(Exception):
    """Se lanza cuando no se puede procesar un PDF."""


class PDFExtractor:
    """
    Extrae texto de archivos PDF preservando la información de las páginas.

    Esta clase es independiente de la lógica de análisis, siguiendo el principio de
    responsabilidad única.
    """

    def extract(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Extrae texto de cada página del PDF.

        Args:
            file_path: Ruta al archivo PDF.

        Returns:
            Lista de diccionarios con las claves ``page`` y ``text``.
        """
        if not file_path.exists():
            raise PDFExtractionError(f"Archivo no encontrado: {file_path}")

        pages = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for index, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    pages.append({
                        "page": index,
                        "text": text or "",
                    })
        except Exception as exc:
            raise PDFExtractionError(f"Error al extraer texto de {file_path}: {exc}") from exc

        return pages

    def extract_full_text(self, file_path: Path) -> str:
        """
        Extrae y concatena todo el texto del PDF.

        Args:
            file_path: Ruta al archivo PDF.

        Returns:
            Texto concatenado del documento.
        """
        pages = self.extract(file_path)
        return "\n\n".join(page["text"] for page in pages)
