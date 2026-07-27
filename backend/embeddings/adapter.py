"""
Adaptador de embeddings.

Centraliza la generación de embeddings. El proveedor concreto se selecciona
a partir de la configuración ``EMBEDDINGS_PROVIDER``. Proveedores soportados:
- ollama
- huggingface
- openai

Cambiar el modelo de embeddings debería requerir solo modificar las variables de entorno.
"""
import time
from typing import List, Protocol
from django.conf import settings
from langchain_ollama import OllamaEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings


class EmbeddingProvider(Protocol):
    """Protocolo para proveedores de embeddings."""

    def embed_query(self, text: str) -> List[float]:
        ...

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        ...


class OllamaEmbeddingProvider:
    """Proveedor de embeddings basado en Ollama."""

    def __init__(self, base_url: str, model: str):
        self._embeddings = OllamaEmbeddings(base_url=base_url, model=model)

    def embed_query(self, text: str) -> List[float]:
        return self._embeddings.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embeddings.embed_documents(texts)


class HuggingFaceEmbeddingProvider:
    """Proveedor de embeddings basado en HuggingFace."""

    def __init__(self, model: str):
        self._embeddings = HuggingFaceEmbeddings(model_name=model)

    def embed_query(self, text: str) -> List[float]:
        return self._embeddings.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embeddings.embed_documents(texts)


class OpenAIEmbeddingProvider:
    """Proveedor de embeddings basado en OpenAI."""

    def __init__(self, model: str, api_key: str):
        self._embeddings = OpenAIEmbeddings(model=model, api_key=api_key)

    def embed_query(self, text: str) -> List[float]:
        return self._embeddings.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embeddings.embed_documents(texts)


class EmbeddingService:
    """
    Servicio que expone una única interfaz para la generación de embeddings.

    El proveedor se construye a partir de la configuración de Django, aislando el resto del
    código de la biblioteca subyacente.
    """

    MAX_RETRIES = 5
    BASE_DELAY = 2

    def __init__(self):
        self._provider = self._build_provider()

    def _build_provider(self) -> EmbeddingProvider:
        provider = settings.EMBEDDINGS_PROVIDER.lower()
        if provider == "ollama":
            return OllamaEmbeddingProvider(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.EMBEDDINGS_MODEL,
            )
        if provider == "huggingface":
            return HuggingFaceEmbeddingProvider(model=settings.EMBEDDINGS_MODEL)
        if provider == "openai":
            return OpenAIEmbeddingProvider(
                model=settings.EMBEDDINGS_MODEL,
                api_key=settings.OPENAI_API_KEY,
            )
        raise ValueError(f"Proveedor de embeddings no soportado: {provider}")

    def _retry(self, operation, description: str):
        """Ejecuta una operación de embeddings con reintentos y espera exponencial."""
        last_exception = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return operation()
            except Exception as exc:
                last_exception = exc
                if attempt == self.MAX_RETRIES:
                    break
                delay = self.BASE_DELAY * (2 ** (attempt - 1))
                print(f"[Embeddings] {description} falló (intento {attempt}/{self.MAX_RETRIES}): {exc}. Reintentando en {delay}s...")
                time.sleep(delay)
        raise last_exception

    def embed_query(self, text: str) -> List[float]:
        return self._retry(lambda: self._provider.embed_query(text), "embed_query")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._retry(lambda: self._provider.embed_documents(texts), "embed_documents")
