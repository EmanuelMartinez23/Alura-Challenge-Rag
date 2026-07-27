"use strict";

const API_BASE = "/api";

const elements = {
    documentsList: document.getElementById("documentsList"),
    fileInput: document.getElementById("fileInput"),
    uploadStatus: document.getElementById("uploadStatus"),
    chatMessages: document.getElementById("chatMessages"),
    chatForm: document.getElementById("chatForm"),
    questionInput: document.getElementById("questionInput"),
    sendButton: document.getElementById("sendButton"),
    sendText: document.getElementById("sendText"),
    sendIcon: document.getElementById("sendIcon"),
};

let isLoading = false;


function statusLabel(status) {
    const labels = {
        pending: "Pendiente",
        processing: "Procesando",
        indexed: "Indexado",
        error: "Error",
    };
    return labels[status] || status;
}

/**
 * Render de lista de documentos
 */
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE}/documents/`);
        if (!response.ok) throw new Error("Error al cargar documentos");
        const data = await response.json();
        renderDocuments(data.results || data);
    } catch (error) {
        elements.documentsList.innerHTML = `
            <div class="text-center text-red-400 py-4 text-sm">
                ${error.message}
            </div>
        `;
    }
}

function renderDocuments(documents) {
    if (!documents.length) {
        elements.documentsList.innerHTML = `
            <div class="text-center text-slate-500 py-8 text-sm">No hay documentos cargados.</div>
        `;
        return;
    }

    elements.documentsList.innerHTML = documents.map((doc) => {
        const statusClass = `status-${doc.status}`;
        return `
            <div class="border border-slate-700 rounded-lg p-3 bg-slate-800 hover:shadow-md transition-shadow">
                <div class="flex items-start justify-between gap-2">
                    <div class="min-w-0 flex-1">
                        <h3 class="text-sm font-medium text-gray-100 truncate" title="${doc.original_name}">
                            ${doc.original_name}
                        </h3>
                        <p class="text-xs text-slate-400 mt-1">
                            ${doc.tipo_equipo || "Equipo no identificado"}
                            ${doc.numero_serie ? `· S/N ${doc.numero_serie}` : ""}
                        </p>
                    </div>
                    <span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium ${statusClass}">
                        ${statusLabel(doc.status)}
                    </span>
                </div>
                ${doc.error_message ? `<p class="text-xs text-red-400 mt-2">${doc.error_message}</p>` : ""}
                <div class="mt-3 flex items-center justify-between">
                    <a href="${doc.file_url}" target="_blank" class="text-xs text-blue-400 hover:text-blue-300 hover:underline">Ver PDF</a>
                    <button
                        onclick="deleteDocument(${doc.id})"
                        class="text-xs text-red-400 hover:text-red-300 font-medium"
                    >
                        Eliminar
                    </button>
                </div>
            </div>
        `;
    }).join("");
}

/**
 * Subir nuevo pdf
 */
async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    elements.uploadStatus.textContent = "Subiendo y procesando...";
    elements.uploadStatus.classList.remove("hidden", "text-red-500", "text-green-600");
    elements.uploadStatus.classList.add("text-blue-600");

    try {
        const response = await fetch(`${API_BASE}/documents/`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || "Error al subir el documento");
        }

        elements.uploadStatus.textContent = "Documento procesado correctamente.";
        elements.uploadStatus.classList.replace("text-blue-600", "text-green-600");
        elements.fileInput.value = "";
        await loadDocuments();
    } catch (error) {
        elements.uploadStatus.textContent = error.message;
        elements.uploadStatus.classList.replace("text-blue-600", "text-red-500");
    }
}

/**
 * Borrar un documento
 */
async function deleteDocument(documentId) {
    if (!confirm("¿Eliminar este documento y sus embeddings?")) return;

    try {
        const response = await fetch(`${API_BASE}/documents/${documentId}/`, {
            method: "DELETE",
        });
        if (!response.ok) throw new Error("Error al eliminar");
        await loadDocuments();
    } catch (error) {
        alert(error.message);
    }
}

/**
 * Agregar un msj al chat
 */
function appendMessage(role, content, sources = []) {
    const isAssistant = role === "assistant";
    const container = document.createElement("div");
    container.className = "flex items-start gap-3";

    const avatar = document.createElement("div");
    avatar.className = `w-8 h-8 rounded-full flex items-center justify-center flex-none text-sm font-bold ${
        isAssistant ? "bg-blue-900 text-blue-200" : "bg-slate-700 text-slate-200"
    }`;
    avatar.textContent = isAssistant ? "A" : "T";

    const bubble = document.createElement("div");
    bubble.className = "bg-slate-800 rounded-lg shadow-sm border border-slate-700 p-4 max-w-3xl";

    const text = document.createElement("div");
    text.className = "text-sm text-gray-100 whitespace-pre-wrap";
    text.textContent = content;
    bubble.appendChild(text);

    if (sources && sources.length) {
        const sourcesHeader = document.createElement("p");
        sourcesHeader.className = "text-xs font-semibold text-slate-400 mt-3 mb-2";
        sourcesHeader.textContent = "Fuentes consultadas:";
        bubble.appendChild(sourcesHeader);

        const sourcesList = document.createElement("div");
        sourcesList.className = "space-y-2";
        sources.forEach((source, index) => {
            const parts = [
                source.tipo_equipo,
                source.numero_serie ? `S/N: ${source.numero_serie}` : "",
                source.codigo_interno ? `Código: ${source.codigo_interno}` : "",
                source.seccion ? `Sección: ${source.seccion}` : "",
                source.pagina ? `Pág. ${source.pagina}` : "",
            ].filter(Boolean);

            const card = document.createElement("div");
            card.className = "source-card bg-slate-900 rounded p-2 text-xs text-slate-300";
            card.textContent = `${index + 1}. ${parts.join(" · ")}`;
            sourcesList.appendChild(card);
        });
        bubble.appendChild(sourcesList);
    }

    container.appendChild(avatar);
    container.appendChild(bubble);
    elements.chatMessages.appendChild(container);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

/**
 * Mandar una pregunta al pipeline RAG
 */
async function askQuestion(question) {
    if (isLoading) return;
    isLoading = true;
    elements.sendText.textContent = "Pensando...";
    elements.sendButton.disabled = true;

    appendMessage("user", question);
    elements.questionInput.value = "";

    try {
        const response = await fetch(`${API_BASE}/chat/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question }),
        });

        if (!response.ok) throw new Error("Error al obtener respuesta");
        const data = await response.json();
        appendMessage("assistant", data.answer, data.sources);
    } catch (error) {
        appendMessage("assistant", `Error: ${error.message}`);
    } finally {
        isLoading = false;
        elements.sendText.textContent = "Enviar";
        elements.sendButton.disabled = false;
        elements.questionInput.focus();
    }
}

/**
 * Inicializar  event listeners.
 */
function init() {
    loadDocuments();

    elements.fileInput.addEventListener("change", (event) => {
        const file = event.target.files[0];
        if (file) uploadFile(file);
    });

    elements.chatForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const question = elements.questionInput.value.trim();
        if (question) askQuestion(question);
    });
}

init();
