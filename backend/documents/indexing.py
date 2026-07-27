"""Servicio de indexación que orquesta el pipeline completo de procesamiento de documentos."""
from pathlib import Path
from typing import List, Dict, Any
from django.conf import settings
from documents.models import Document, DocumentStatus
from documents.extraction import PDFExtractor
from documents.parsing import DocumentParser
from documents.chunking import DocumentChunker
from embeddings.adapter import EmbeddingService
from vectorstore.qdrant_client import VectorStoreService


class DocumentIndexingError(Exception):
    """Se lanza cuando falla la indexación de un documento."""


class DocumentIndexer:
    """
    Servicio responsable de procesar un archivo PDF de principio a fin.

    El pipeline es:
    1. Extraer el texto del PDF.
    2. Analizar el texto en secciones estructuradas con un LLM.
    3. Dividir cada sección en fragmentos.
    4. Generar embeddings para cada fragmento.
    5. Almacenar los fragmentos y embeddings en Qdrant.
    """

    def __init__(self):
        self.extractor = PDFExtractor()
        self.parser = DocumentParser()
        self.chunker = DocumentChunker()
        self.embeddings = EmbeddingService()
        self.vectorstore = VectorStoreService()

    def process(self, document: Document) -> None:
        """
        Procesa e indexa un único documento.

        Args:
            document: Una instancia de ``Document`` cuyo archivo ya está guardado.
        """
        document.status = DocumentStatus.PROCESSING
        document.save(update_fields=["status"])

        try:
            file_path = Path(document.file.path)
            print(f"[Document {document.pk}] Extrayendo texto de {document.original_name}...")
            full_text = self.extractor.extract_full_text(file_path)

            print(f"[Document {document.pk}] Analizando contenido estructurado con LLM...")
            parsed = self.parser.parse(full_text)

            # Actualiza los metadatos del documento a partir de los campos analizados
            document.tipo_equipo = parsed.get("tipo_equipo", "")
            document.marca = parsed.get("marca", "")
            document.modelo = parsed.get("modelo", "")
            document.numero_serie = parsed.get("numero_serie", "")
            document.codigo_interno = parsed.get("codigo_interno", "")
            document.ubicacion = parsed.get("ubicacion", "")
            fecha = parsed.get("fecha_mantenimiento") or None
            document.fecha_mantenimiento = fecha if fecha else None
            document.error_message = parsed.get("error", "")
            document.save()

            chunks = self.chunker.chunk_document(document.pk, parsed, fallback_text=full_text)
            if not chunks:
                raise DocumentIndexingError("No se generaron fragmentos de texto a partir del documento.")

            print(f"[Document {document.pk}] Generando embeddings para {len(chunks)} fragmentos...")
            self._index_chunks(chunks)

            document.status = DocumentStatus.INDEXED
            document.save(update_fields=["status"])
            print(f"[Document {document.pk}] Indexado correctamente.")

        except Exception as exc:
            document.status = DocumentStatus.ERROR
            document.error_message = str(exc)
            document.save(update_fields=["status", "error_message"])
            print(f"[Document {document.pk}] ERROR: {exc}")
            raise DocumentIndexingError(f"Error al indexar el documento {document.pk}: {exc}") from exc

    def _index_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """Genera embeddings y almacena los fragmentos en el almacén de vectores."""
        ids = [chunk["id"] for chunk in chunks]
        texts = [chunk["content"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]

        embeddings = self.embeddings.embed_documents(texts)

        self.vectorstore.add_documents(
            ids=ids,
            texts=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        print(f"[Almacén de vectores] Almacenados {len(chunks)} fragmentos.")

    def reindex(self, document: Document) -> None:
        """Elimina los embeddings existentes y vuelve a procesar un documento."""
        self.vectorstore.delete_by_document_id(document.pk)
        self.process(document)

    def index_default_documents(self) -> None:
        """Indexa todos los archivos PDF encontrados en el directorio de documentos predeterminados."""
        default_dir = Path(settings.DEFAULT_DOCUMENTS_DIR)
        if not default_dir.exists():
            print(f"[Indexer] Directorio de documentos predeterminados no encontrado: {default_dir}")
            return

        pdf_files = sorted(default_dir.glob("*.pdf"))
        print(f"[Indexer] Encontrados {len(pdf_files)} PDF(s) predeterminados para procesar.")

        for pdf_path in pdf_files:
            # Omitir archivos ya indexados
            if Document.objects.filter(original_name=pdf_path.name).exists():
                print(f"[Indexer] Omitiendo archivo ya indexado: {pdf_path.name}")
                continue

            print(f"[Indexer] Creando registro de documento para {pdf_path.name}...")
            document = Document.objects.create(
                file=str(pdf_path.relative_to(settings.MEDIA_ROOT)),
                original_name=pdf_path.name,
                status=DocumentStatus.PENDING,
            )
            try:
                self.process(document)
            except DocumentIndexingError:
                # Registra el error pero continúa con el siguiente archivo
                continue
