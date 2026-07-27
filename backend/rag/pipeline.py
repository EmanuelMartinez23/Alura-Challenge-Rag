"""Implementación del pipeline de RAG."""
from typing import List, Dict, Any
from django.conf import settings
from embeddings.adapter import EmbeddingService
from vectorstore.qdrant_client import VectorStoreService
from llm.adapter import LLMService
from prompts.rag import RAG_SYSTEM_PROMPT, build_rag_prompt
from rag.query_analyzer import analyze_query


class RAGPipeline:
    """
    Orquesta el proceso de recuperación y generación.

    Dada una pregunta, la convierte en embedding, recupera los fragmentos más relevantes de
    Qdrant, construye un prompt y le pide al LLM que responda usando únicamente el contexto.
    """

    def __init__(self):
        self.embeddings = EmbeddingService()
        self.vectorstore = VectorStoreService()
        self.llm = LLMService()
        self.top_k = settings.TOP_K

    def ask(self, question: str) -> Dict[str, Any]:
        """
        Responde una pregunta basándose en los documentos indexados.

        Args:
            question: Pregunta del usuario en lenguaje natural.

        Returns:
            Diccionario con la respuesta generada y una lista de fuentes.
        """
        filters = analyze_query(question)
        query_embedding = self.embeddings.embed_query(question)
        results = self.vectorstore.search(
            embedding=query_embedding,
            top_k=self.top_k,
            filters=filters if filters else None,
        )

        if not results:
            return {
                "answer": "No encontré información relevante en los documentos indexados.",
                "sources": [],
            }

        context = self._build_context(results)
        prompt = build_rag_prompt(
            context=context,
            question=question,
            filters=filters,
        )
        answer = self.llm.generate(prompt=prompt, system_prompt=RAG_SYSTEM_PROMPT)

        sources = self._build_sources(results)
        return {
            "answer": answer,
            "sources": sources,
        }

    def _build_context(self, results: List[Dict[str, Any]]) -> str:
        """Concatena los fragmentos recuperados en una única cadena de contexto."""
        parts = []
        for index, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})
            header = self._format_context_header(index, metadata)
            parts.append(f"{header}\n{result['content']}")
        return "\n\n".join(parts)

    def _build_sources(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Construye una lista limpia de fuentes para el frontend."""
        sources = []
        for result in results:
            metadata = result.get("metadata", {})
            sources.append({
                "tipo_equipo": metadata.get("tipo_equipo", ""),
                "marca": metadata.get("marca", ""),
                "modelo": metadata.get("modelo", ""),
                "numero_serie": metadata.get("numero_serie", ""),
                "codigo_interno": metadata.get("codigo_interno", ""),
                "ubicacion": metadata.get("ubicacion", ""),
                "seccion": metadata.get("seccion", ""),
                "pagina": metadata.get("pagina", 1),
                "score": result.get("score", 0.0),
            })
        return sources

    def _format_context_header(self, index: int, metadata: Dict[str, Any]) -> str:
        """Formatea un encabezado detallado para un fragmento en el contexto del LLM."""
        tipo = metadata.get("tipo_equipo", "Equipo")
        marca = metadata.get("marca", "")
        modelo = metadata.get("modelo", "")
        serie = metadata.get("numero_serie", "")
        codigo = metadata.get("codigo_interno", "")
        ubicacion = metadata.get("ubicacion", "")
        seccion = metadata.get("seccion", "")
        pagina = metadata.get("pagina", 1)

        parts = [f"Documento {index}", f"Tipo: {tipo}"]
        if marca:
            parts.append(f"Marca: {marca}")
        if modelo:
            parts.append(f"Modelo: {modelo}")
        if serie:
            parts.append(f"S/N: {serie}")
        if codigo:
            parts.append(f"Código: {codigo}")
        if ubicacion:
            parts.append(f"Ubicación: {ubicacion}")
        if seccion:
            parts.append(f"Sección: {seccion}")
        parts.append(f"Página: {pagina}")
        return " | ".join(parts)

    def _format_source_line(self, metadata: Dict[str, Any]) -> str:
        """Formatea una única línea de fuente para el contexto."""
        tipo = metadata.get("tipo_equipo", "Equipo")
        serie = metadata.get("numero_serie", "")
        codigo = metadata.get("codigo_interno", "")
        seccion = metadata.get("seccion", "")
        pagina = metadata.get("pagina", 1)

        parts = [tipo]
        if serie:
            parts.append(f"S/N: {serie}")
        if codigo:
            parts.append(f"Código: {codigo}")
        if seccion:
            parts.append(f"Sección: {seccion}")
        parts.append(f"Página: {pagina}")
        return " | ".join(parts)
