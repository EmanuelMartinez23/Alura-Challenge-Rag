from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from documents.models import Document
from documents.indexing import DocumentIndexer, DocumentIndexingError
from api.serializers import (
    DocumentSerializer,
    ChatRequestSerializer,
)
from rag.pipeline import RAGPipeline


class DocumentViewSet(viewsets.ModelViewSet):
    """Endpoints REST para listar, cargar y eliminar documentos."""

    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        """Maneja la carga de PDF y dispara la indexación de forma síncrona."""
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"error": "No se proporcionó ningún archivo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not uploaded_file.name.lower().endswith(".pdf"):
            return Response(
                {"error": "Solo se permiten archivos PDF."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        document = Document.objects.create(
            file=uploaded_file,
            original_name=uploaded_file.name,
        )

        indexer = DocumentIndexer()
        try:
            indexer.process(document)
        except DocumentIndexingError:
            # Devuelve el documento con el estado de error al frontend
            pass

        serializer = self.get_serializer(document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Elimina el documento; el manejador de señales borra sus embeddings."""
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatView(APIView):
    """Endpoint REST para hacer preguntas sobre los documentos indexados."""

    def post(self, request, *args, **kwargs):
        """Procesa una pregunta del usuario a través del pipeline de RAG."""
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data["question"]
        pipeline = RAGPipeline()
        result = pipeline.ask(question)
        return Response(result, status=status.HTTP_200_OK)
