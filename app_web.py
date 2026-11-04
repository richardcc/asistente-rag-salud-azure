import os
import re
import json
import streamlit as st
import openai
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

# Configuración de página
st.set_page_config(
    page_title="Asistente RAG - Guías de Salud y Nutrición",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .citation-card {
        background-color: #F8FAFC;
        border-left: 4px solid #2563EB;
        padding: 12px 16px;
        margin: 10px 0;
        border-radius: 6px;
        font-size: 0.92rem;
        line-height: 1.5;
    }
    .badge-source {
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_config():
    config_file = "config_rag.json"
    if not os.path.exists(config_file):
        return None
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_system_prompt():
    prompt_file = "system_prompt.txt"
    if os.path.exists(prompt_file):
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return (
        "Eres un asistente clínico y nutricional experto de alta rigurosidad basado en evidencia científica oficial.\n"
        "Tu misión es responder a las dudas del usuario basándote EXCLUSIVAMENTE en el contexto proporcionado de las guías oficiales (AESAN, SEEDO, SENC, Ministerio de Sanidad y AEMPS)."
    )


config = load_config()

# Barra lateral informativa
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Logo-unir.png/320px-Logo-unir.png", width=180)
    st.title("Arquitectura RAG")
    st.caption("Máster en IA - Integración y Operativización de Modelos Generativos")
    st.divider()

    if config:
        st.success("🟢 Conexión con Azure activa")
        st.markdown(f"**Modelo Chat:** `{config.get('AZURE_OPENAI_CHAT_DEPLOYMENT', 'gpt-4.1-mini')}`")
        st.markdown(f"**Embeddings:** `{config.get('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small')}`")
        st.markdown(f"**Motor Vectorial:** Azure AI Search")
        st.markdown(f"**Índice:** `{config.get('AZURE_SEARCH_INDEX', 'rag-salud-indices')}`")
        st.caption("✨ Chunking y vectorización nativos de Azure")
    else:
        st.error("🔴 Configuración no encontrada (`config_rag.json`)")
        st.info("Ejecuta primero: `python desplegar_todo_azure.py`")

    st.divider()
    st.subheader("⚙️ Parámetros de Recuperación")
    top_k = st.slider("Documentos a recuperar (Top-K):", min_value=1, max_value=8, value=3)
    temperature = st.slider("Temperatura (Creatividad):", min_value=0.0, max_value=1.0, value=0.3, step=0.05)

    st.divider()
    st.subheader("💡 Preguntas de Evaluación")
    ejemplos = [
        "¿Cuáles son los puntos de corte de IMC y clasificación según la guía SEEDO?",
        "¿Cuáles son los criterios de indicación de Wegovy (semaglutida) según la AEMPS?",
        "¿Qué mecanismo y eficacia señala la AEMPS sobre Mounjaro (tirzepatida)?",
        "Mido 175 cm y peso 95 kilos, ¿cuál es mi clasificación y qué recomendaciones debo seguir?",
        "¿Cuántas raciones de fruta y verdura recomienda la AESAN al día?",
        "¿Qué recomendaciones de actividad física hace el Ministerio de Sanidad?"
    ]
    for ej in ejemplos:
        if st.button(ej, key=ej):
            st.session_state["pregunta_ejemplo"] = ej

# Título Principal
st.markdown("<div class='main-header'>🥗 Asistente RAG Especializado en Salud y Nutrición</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Respuestas fundamentadas exclusivamente en guías científicas oficiales (AESAN, SEEDO, SENC y Ministerio de Sanidad) con trazabilidad de citas.</div>", unsafe_allow_html=True)

if not config:
    st.warning("⚠️ No se ha encontrado el archivo `config_rag.json`. Por favor, ejecuta en la terminal el script automatizado:")
    st.code("python desplegar_todo_azure.py", language="bash")
    st.stop()

# Clientes de Azure
openai_client = openai.AzureOpenAI(
    azure_endpoint=config["AZURE_OPENAI_ENDPOINT"],
    api_key=config["AZURE_OPENAI_KEY"],
    api_version="2024-02-01"
)

search_client = SearchClient(
    endpoint=config["AZURE_SEARCH_ENDPOINT"],
    index_name=config["AZURE_SEARCH_INDEX"],
    credential=AzureKeyCredential(config["AZURE_SEARCH_KEY"])
)

# Historial de conversación
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "¡Hola! Soy tu asistente clínico y nutricional basado en evidencia. He sido indexado directamente desde los documentos en Azure Blob Storage. Pregúntame sobre pautas dietéticas, actividad física o clasificación del IMC según las guías oficiales.",
            "citations": []
        }
    ]

# Renderizar mensajes anteriores
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("citations"):
            with st.expander(f"📚 Ver {len(msg['citations'])} citas y evidencias documentales"):
                for idx, c in enumerate(msg["citations"], 1):
                    st.markdown(
                        f"<div class='citation-card'><span class='badge-source'>Cita {idx}: {c['title']}</span> (Score: {c['score']:.3f})<br/><br/><em>\"{c['chunk']}\"</em></div>",
                        unsafe_allow_html=True
                    )

# Entrada de usuario
user_query = st.chat_input("Escribe tu pregunta sobre nutrición o guías de salud...")
if "pregunta_ejemplo" in st.session_state:
    user_query = st.session_state.pop("pregunta_ejemplo")

if user_query:
    # 1. Agregar mensaje de usuario
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # 2. Guardrail de entrada (filtro de dominio para consultas no medicas/matematicas)
    if re.match(r"^[\d\+\-\*\/\^\(\)\=\.\,\s]+$", user_query.strip()):
        with st.chat_message("assistant"):
            msg_guardrail = (
                "Soy un asistente especializado exclusivamente en **salud, nutrición y hábitos saludables**.\n\n"
                "No estoy diseñado para resolver operaciones matemáticas generales ni consultas ajenas a este ámbito.\n\n"
                "¿En qué puedo ayudarte respecto a tu alimentación, ejercicio físico o control de peso?"
            )
            st.markdown(msg_guardrail)
            st.session_state.messages.append({
                "role": "assistant",
                "content": msg_guardrail,
                "citations": []
            })
        st.stop()

    # 3. Pipeline RAG
    with st.chat_message("assistant"):
        try:
            # Paso A y B: Búsqueda Vectorial (spinner solo durante la búsqueda rápida)
            with st.spinner("🔍 Consultando evidencias en Azure AI Search..."):
                emb_res = openai_client.embeddings.create(
                    input=user_query,
                    model=config["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]
                )
                query_vector = emb_res.data[0].embedding

                # Búsqueda Vectorial HNSW en Azure AI Search
                vector_field_name = "text_vector"
                vector_query = VectorizedQuery(
                    vector=query_vector,
                    k_nearest_neighbors=top_k,
                    fields=vector_field_name
                )

                try:
                    search_results = search_client.search(
                        search_text=user_query,
                        vector_queries=[vector_query],
                        top=top_k
                    )
                except Exception:
                    vector_query.fields = "vector"
                    search_results = search_client.search(
                        search_text=user_query,
                        vector_queries=[vector_query],
                        top=top_k
                    )

                retrieved_chunks = []
                context_texts = []
                for res in search_results:
                    title = res.get("title") or res.get("metadata_storage_name") or "Guía Oficial"
                    chunk = res.get("chunk") or res.get("content") or res.get("text") or ""
                    score = res.get("@search.score", 0.0)

                    if "/" in title:
                        title = title.split("/")[-1]
                    if "\\" in title:
                        title = title.split("\\")[-1]

                    if chunk:
                        retrieved_chunks.append({"title": title, "chunk": chunk[:1500], "score": score})
                        context_texts.append(f"Fuente: {title}\nTexto: {chunk.strip()}")

                context_str = "\n\n---\n\n".join(context_texts)

            # Paso C: Generación de respuesta con LLM (cargado desde system_prompt.txt)
            system_prompt = load_system_prompt()

            messages_for_llm = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Información de contexto disponible:\n{context_str}\n\nPregunta del usuario: {user_query}"}
            ]

            llm_kwargs = {
                "model": config["AZURE_OPENAI_CHAT_DEPLOYMENT"],
                "messages": messages_for_llm,
                "stream": True
            }
            if not config["AZURE_OPENAI_CHAT_DEPLOYMENT"].startswith("o"):
                llm_kwargs["temperature"] = temperature
                llm_kwargs["max_tokens"] = 600
                llm_kwargs["frequency_penalty"] = 0.3

            stream = openai_client.chat.completions.create(**llm_kwargs)

            def response_generator():
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            full_response = st.write_stream(response_generator())

            # Desplegable con fuentes y fragmentos recuperados (solo si aplica al dominio)
            es_fuera_de_dominio = any(
                frase in full_response.lower()
                for frase in [
                    "fuera de este ámbito", "fuera de este ambito",
                    "fuera de mi ámbito", "fuera de mi ambito",
                    "especializado exclusivamente", "no estoy capacitado para",
                    "no estoy diseñado para", "mi especialidad es"
                ]
            )

            if retrieved_chunks and not es_fuera_de_dominio:
                with st.expander(f"📚 Ver {len(retrieved_chunks)} citas y evidencias documentales"):
                    for idx, c in enumerate(retrieved_chunks, 1):
                        st.markdown(
                            f"<div class='citation-card'><span class='badge-source'>Cita {idx}: {c['title']}</span> (Score: {c['score']:.3f})<br/><br/><em>\"{c['chunk']}\"</em></div>",
                            unsafe_allow_html=True
                        )

            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response,
                "citations": retrieved_chunks if not es_fuera_de_dominio else []
            })

        except Exception as e:
            st.error(f"Error procesando la solicitud: {str(e)}")
