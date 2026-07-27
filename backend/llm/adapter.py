"""
Adaptador de LLM.

Centraliza la comunicación con modelos de lenguaje. El proveedor se selecciona de
la configuración ``LLM_PROVIDER``. Proveedores soportados:
- ollama (local)
- gemini
- openai

Esta abstracción permite cambiar de proveedor sin modificar el pipeline de RAG.
"""
from typing import Optional, Protocol
from django.conf import settings
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


class LLMProvider(Protocol):
    """Protocolo para proveedores de LLM."""

    def invoke(self, messages: list) -> str:
        ...


class OllamaLLMProvider:
    """Proveedor de LLM basado en Ollama."""

    def __init__(self, base_url: str, model: str, fallback_model: Optional[str] = None):
        self.base_url = base_url
        self.model = model
        self.fallback_model = fallback_model
        self._llm = self._build_llm(model)

    def _build_llm(self, model: str):
        return ChatOllama(base_url=self.base_url, model=model)

    def invoke(self, messages: list) -> str:
        try:
            response = self._llm.invoke(messages)
            return response.content
        except Exception as exc:
            if self.fallback_model and self.model != self.fallback_model:
                self._llm = self._build_llm(self.fallback_model)
                self.model = self.fallback_model
                response = self._llm.invoke(messages)
                return response.content
            raise exc


class GeminiLLMProvider:
    """Proveedor de LLM basado en Google Gemini."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self._llm = ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model,
            convert_system_message_to_human=True,
        )

    def invoke(self, messages: list) -> str:
        response = self._llm.invoke(messages)
        return response.content


class OpenAILLMProvider:
    """Proveedor de LLM basado en OpenAI."""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self._llm = ChatOpenAI(api_key=api_key, model=model)

    def invoke(self, messages: list) -> str:
        response = self._llm.invoke(messages)
        return response.content


class LLMService:
    """
    Servicio que expone una única interfaz para la generación de texto.

    El proveedor se construye a partir de la configuración de Django, aislando el resto de la
    aplicación de la biblioteca subyacente.

    Se puede pasar un modelo específico para sobrescribir el modelo predeterminado configurado.
    Esto es útil, por ejemplo, para usar un modelo más ligero en la extracción estructurada
    mientras se mantiene un modelo más grande para las respuestas finales.
    """

    def __init__(self, model: Optional[str] = None):
        self._model = model
        self._provider = self._build_provider()

    def _build_provider(self) -> LLMProvider:
        provider = settings.LLM_PROVIDER.lower()
        if provider == "ollama":
            return OllamaLLMProvider(
                base_url=settings.OLLAMA_BASE_URL,
                model=self._model or settings.OLLAMA_MODEL,
                fallback_model=settings.OLLAMA_FALLBACK_MODEL,
            )
        if provider == "gemini":
            return GeminiLLMProvider(
                api_key=settings.GEMINI_API_KEY,
                model=self._model or getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash"),
            )
        if provider == "openai":
            return OpenAILLMProvider(
                api_key=settings.OPENAI_API_KEY,
                model=self._model or getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo"),
            )
        raise ValueError(f"Proveedor de LLM no soportado: {provider}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Genera una respuesta del LLM a partir de un prompt.

        Args:
            prompt: El prompt del usuario.
            system_prompt: Instrucciones del sistema opcionales.

        Returns:
            El texto generado.
        """
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        return self._provider.invoke(messages)
