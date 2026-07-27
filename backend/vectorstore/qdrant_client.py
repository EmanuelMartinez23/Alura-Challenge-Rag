"""
Store de vectores Qdrant.

Este módulo permite la comunicación directa con Qdrant.
"""
from typing import List, Dict, Any, Optional
from django.conf import settings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue


class VectorStoreService:
    """
    Servicio para crear colecciones, insertar, borrar y buscar vectores en Qdrant.
    """

    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.vector_size = int(getattr(settings, "EMBEDDINGS_DIMENSION", "1024"))
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Crea una colección si no existe."""
        collections = self.client.get_collections().collections
        names = {collection.name for collection in collections}
        if self.collection_name not in names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )

    def add_documents(
        self,
        ids: List[str],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        """
        Inserta o actualiza fragmentos en Qdrant.

        Args:
            ids: Identificador para cada fragmento.
            texts: Texto de cada fragmento.
            metadatas: Metadatos para cada fragmento.
            embeddings: Embeddings para cada fragmento.
        """
        points = []
        for idx, text, metadata, embedding in zip(ids, texts, metadatas, embeddings):
            payload = dict(metadata)
            payload["content"] = text
            points.append(
                PointStruct(
                    id=idx,
                    vector=embedding,
                    payload=payload,
                )
            )
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    def delete_by_document_id(self, document_id: int) -> None:
        """Borra todos los fragmentos y embeddings relacionados con el documento."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
        )

    def search(
        self,
        embedding: List[float],
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Busca los fragmentos más similares en Qdrant.

        Args:
            embedding: Vector de consulta.
            top_k: Número máximo de fragmentos a recuperar.
            filters: Filtros de metadatos opcionales (actualmente soporta igualdad simple).

        Returns:
            Lista de diccionarios con el texto del fragmento, metadatos y puntaje.
        """
        query_filter = None
        if filters:
            conditions = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in filters.items()
            ]
            query_filter = Filter(must=conditions)

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            limit=top_k,
            query_filter=query_filter,
        )

        return [
            {
                "id": result.id,
                "score": result.score,
                "content": result.payload.get("content", ""),
                "metadata": {
                    key: value for key, value in result.payload.items() if key != "content"
                },
            }
            for result in response.points
        ]

    def count(self) -> int:
        """Regresa el número total de vectores en una colección."""
        return self.client.count(collection_name=self.collection_name).count

    def collection_exists(self) -> bool:
        """Verifica que la colección exista."""
        collections = self.client.get_collections().collections
        return any(collection.name == self.collection_name for collection in collections)
