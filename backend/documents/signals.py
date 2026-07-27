from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from documents.models import Document
from vectorstore.qdrant_client import VectorStoreService


@receiver(pre_delete, sender=Document)
def delete_document_file(sender, instance: Document, **kwargs) -> None:
    """Elimina el archivo PDF físico antes de borrar la fila de la base de datos."""
    try:
        if instance.file and instance.file.storage.exists(instance.file.name):
            instance.file.delete(save=False)
    except Exception:
        pass


@receiver(post_delete, sender=Document)
def delete_document_embeddings(sender, instance: Document, **kwargs) -> None:
    """Elimina todos los fragmentos de Qdrant asociados a un documento borrado."""
    try:
        vectorstore = VectorStoreService()
        vectorstore.delete_by_document_id(instance.pk)
    except Exception:
        # Evita que fallos en la señal interrumpan las eliminaciones
        pass
