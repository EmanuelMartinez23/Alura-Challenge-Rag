from django.db import models
from django.utils import timezone


class DocumentStatus(models.TextChoices):
    """Posibles estados de procesamiento de un documento."""

    PENDING = "pending", "Pendiente"
    PROCESSING = "processing", "Procesando"
    INDEXED = "indexed", "Indexado"
    ERROR = "error", "Error"


class Document(models.Model):
    """
    Representa un PDF de reporte de mantenimiento cargado en el sistema.

    El archivo real se almacena en disco. Los embeddings y los fragmentos se
    guardan en Qdrant, mientras que este modelo conserva los metadatos y el estado de procesamiento.
    """

    file = models.FileField(
        upload_to="uploads/",
        help_text="Archivo PDF cargado por el usuario.",
    )
    original_name = models.CharField(
        max_length=255,
        help_text="Nombre original del archivo antes de renombrarlo.",
    )

    # Metadatos extraídos del reporte
    tipo_equipo = models.CharField(max_length=100, blank=True, default="")
    marca = models.CharField(max_length=100, blank=True, default="")
    modelo = models.CharField(max_length=100, blank=True, default="")
    numero_serie = models.CharField(max_length=100, blank=True, default="")
    codigo_interno = models.CharField(max_length=100, blank=True, default="")
    ubicacion = models.CharField(max_length=200, blank=True, default="")
    fecha_mantenimiento = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
    )
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"

    def __str__(self) -> str:
        return f"{self.original_name} ({self.status})"
