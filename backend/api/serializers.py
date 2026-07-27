"""Serializadores para la aplicación API."""
from rest_framework import serializers
from documents.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    """Serializador para el modelo Document."""

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "file",
            "file_url",
            "original_name",
            "tipo_equipo",
            "marca",
            "modelo",
            "numero_serie",
            "codigo_interno",
            "ubicacion",
            "fecha_mantenimiento",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "file_url",
            "original_name",
            "tipo_equipo",
            "marca",
            "modelo",
            "numero_serie",
            "codigo_interno",
            "ubicacion",
            "fecha_mantenimiento",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        ]

    def get_file_url(self, obj: Document) -> str:
        """Devuelve la URL absoluta del archivo del documento."""
        request = self.context.get("request")
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else ""


class ChatRequestSerializer(serializers.Serializer):
    """Serializador para el endpoint de chat/preguntas."""

    question = serializers.CharField(required=True, max_length=2000)


