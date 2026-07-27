# RAG-Mant
RAG-Mant es una empresa especializada en servicios de mantenimiento preventivo, correctivo y predictivo para equipos industriales y tecnológicos. Como parte de sus operaciones, genera reportes técnicos que documentan diagnósticos, procedimientos realizados, fallas detectadas y acciones correctivas aplicadas a cada equipo.

Plataforma web basada en Python y Django que implementa una arquitectura Retrieval-Augmented Generation (RAG) para consultar información contenida en reportes técnicos de mantenimiento de equipos en formato PDF.

La aplicación permite cargar uno o varios documentos PDF, procesarlos automáticamente, generar embeddings, almacenarlos en una base de datos vectorial (Qdrant) y responder preguntas en lenguaje natural utilizando exclusivamente el contexto recuperado de los documentos.

---

## Demostración

A continuación se muestra el video del funcionamiento de la plataforma:

<video src="./video_final.mp4" controls width="100%"></video>


https://github.com/user-attachments/assets/cd0fd64f-46ec-4a69-b2a1-0a76342fe30d


Si el video no se reproduce en el navegador, puedes descargarlo directamente desde [`video_final.mp4`](./video_final.mp4).

---

## Tecnologías principales

- Python 3.13+
- Django + Django REST Framework
- Tailwind CSS + Vanilla JS
- LangChain
- Embeddings: BAAI/bge-m3 vía Ollama (configurable para usar HuggingFace/OpenAI)
- LLM: Ollama local (gemma3:4b/gemma3:1b) con soporte para Gemini/OpenAI
- Base vectorial: Qdrant
- Contenedores: Docker + Docker Compose

---

## Configuración

El archivo de variables de entorno se encuentra en `backend/.env`.

```bash
# Ollama debe estar corriendo en la máquina host
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma3:4b
OLLAMA_FALLBACK_MODEL=gemma3:1b

EMBEDDINGS_PROVIDER=ollama
EMBEDDINGS_MODEL=bge-m3:latest
EMBEDDINGS_DIMENSION=1024

LLM_PROVIDER=ollama
```

Si se desea usar un modelo en la nube, editamos el `backend/.env`:

```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=tu-api-key-aqui
```

o

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=tu-api-key-aqui
```

---

## Ejecución con Docker Compose

### Requisito previo: Ollama en la máquina host

Ollama debe estar instalado y corriendo **localmente**. Los contenedores se conectan a él mediante `host.docker.internal`.

Asegúrate de tener los modelos necesarios:

```bash
ollama pull bge-m3:latest
ollama pull gemma3:4b
# Opcional
ollama pull gemma3:1b
```

Verifica que responde:

```bash
ollama list
```

### Levantar el proyecto

Desde la raíz del proyecto ejecuta:

```bash
docker-compose up --build
```

Durante el primer arranque se realizarán las siguientes acciones:

1. Descarga de imágenes de Docker (Django, Qdrant).
2. Aplicación de migraciones de Django.
3. Indexación automática de los PDFs ubicados en `Documentos/`.

Una vez listo, abrimos el navegador en:

```text
http://localhost:8000
```

La interfaz web consiste en una única página con:

- Biblioteca de documentos: listado, subida y eliminación de PDFs.
- Área de chat: historial de la conversación, pregunta, respuesta y fuentes consultadas.

---

## API REST

Los endpoints disponibles son:

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/documents/` | Listar documentos indexados |
| POST | `/api/documents/` | Subir un nuevo PDF  |
| DELETE | `/api/documents/<id>/` | Eliminar un documento y sus embeddings |
| POST | `/api/chat/` | Enviar una pregunta (JSON `{ "question": "..." }`) |

Ejemplo de consulta desde la terminal:

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cuál es el número de serie del aire acondicionado SN7443380000 ?"}'
```

---

## Documentos precargados

Los PDFs de ejemplo se encuentran en la carpeta `Documentos/` del proyecto. Estos archivos se montan de solo lectura dentro del contenedor en `/app/media/default_documents` y se indexan automáticamente al iniciar el sistema.

Para agregar más documentos precargados, coloca los archivos PDF en `Documentos/` y reinicia los contenedores. El sistema detectará e indexará solo los archivos nuevos.

Para subir documentos de forma manual, utiliza el botón "Subir PDF" de la interfaz web o el endpoint `/api/documents/`.

---

## Comandos útiles

Ver logs de todos los servicios:

```bash
docker-compose logs -f
```

Ver logs solo del servicio web:

```bash
docker-compose logs -f web
```

Indexar documentos precargados nuevos (solo procesa los archivos que aún no tengan un registro en la base de datos):

```bash
docker-compose exec web python manage.py index_default_documents
```

Para reindexar desde cero, elimina primero los registros de documentos y la colección de Qdrant, luego reinicia los contenedores:

```bash
docker-compose exec web python manage.py shell -c "from documents.models import Document; Document.objects.all().delete()"
docker-compose exec web python manage.py shell -c "from vectorstore.qdrant_client import VectorStoreService as VS; VS().client.delete_collection(VS().collection_name)"
docker-compose restart web
```

Eliminar todos los datos y volúmenes (cuidado, esto borra la base de datos vectorial de Qdrant; los modelos de Ollama permanecen en la máquina host):

```bash
docker-compose down -v
```

---

## Solución de problemas

### El servicio web no inicia y muestra error de conexión a Qdrant

Asegúrate de que el contenedor `qdrant` esté corriendo:

```bash
docker-compose ps
```

Si no está saludable, revisa sus logs:

```bash
docker-compose logs qdrant
```

### Ollama no responde

Como Ollama corre en la máquina host, verifica que el servicio esté activo:

```bash
ollama list
```

Si no responde, inícialo:

```bash
ollama serve
```

Si faltan modelos, descárgalos en la máquina host:

```bash
ollama pull bge-m3:latest
ollama pull gemma3:4b
```

Para probar la conectividad desde dentro del contenedor web:

```bash
docker-compose exec web curl http://host.docker.internal:11434
```

Debe devolver una respuesta HTTP (normalmente `404 page not found`), lo que indica que Ollama es alcanzable.

### Los documentos quedan en estado "Error"

Revisa los logs del servicio web. El error más común es que Ollama no tenga disponible el modelo solicitado o que el texto del PDF no sea legible.

### La interfaz web no carga estilos

En modo desarrollo, Django sirve los archivos estáticos automáticamente. Si usas un entorno de producción, asegúrate de ejecutar:

```bash
python manage.py collectstatic
```

---

## Arquitectura modular

El backend sigue una arquitectura desacoplada:

- `api/`: endpoints REST, sin lógica de negocio.
- `documents/`: gestión de PDFs, extracción de texto, parseo estructurado, chunking e indexación.
- `embeddings/`: generación de embeddings a través de un adapter configurable.
- `vectorstore/`: único punto de contacto con Qdrant.
- `llm/`: comunicación con modelos de lenguaje a través de un adapter configurable.
- `prompts/`: prompts centralizados, no hardcodeados en el código.
- `rag/`: orquestación del pipeline de recuperación y generación.

---

