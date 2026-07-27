from django.core.management.base import BaseCommand
from documents.indexing import DocumentIndexer


class Command(BaseCommand):
    """Indexa todos los PDFs de reportes de mantenimiento predeterminados almacenados en la carpeta media."""

    help = "Indexa todos los documentos PDF predeterminados en media/default_documents"

    def handle(self, *args, **options):
        indexer = DocumentIndexer()
        self.stdout.write("Indexando documentos predeterminados...")
        indexer.index_default_documents()
        self.stdout.write(self.style.SUCCESS("Documentos predeterminados indexados correctamente."))
