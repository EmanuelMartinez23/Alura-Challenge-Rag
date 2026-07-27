"""Configuración del admin de Django para la aplicación documents."""
from django.contrib import admin
from documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Vista de administración para documentos de reportes de mantenimiento."""

    list_display = (
        "original_name",
        "tipo_equipo",
        "marca",
        "modelo",
        "numero_serie",
        "codigo_interno",
        "ubicacion",
        "status",
        "created_at",
    )
    list_filter = ("status", "tipo_equipo", "created_at")
    search_fields = ("original_name", "numero_serie", "codigo_interno", "marca", "modelo")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
