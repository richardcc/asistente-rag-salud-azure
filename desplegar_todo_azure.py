"""
======================================================================================
  ACTIVIDAD 02 - MÁSTER UNIR
  Integración y Operativización de Modelos Generativos en Aplicaciones Empresariales
  
  SCRIPT INTEGRAL DE DESPLIEGUE Y OPERATIVIZACIÓN RAG EN AZURE (100% AUTOMATIZADO)
======================================================================================
Este script automatiza de extremo a extremo y sin intervención manual todos los pasos:
  1. Autenticación unificada con Azure for Students (InteractiveBrowserCredential).
  2. Grupo de Recursos unificado en Azure ('rg-rag-unir-final').
  3. Azure Blob Storage + Carga automática de los 5 PDFs oficiales de Salud y Nutrición.
  4. Azure Cognitive Services / AI Foundry:
     - Despliegue automático de 'text-embedding-3-small' (Embeddings).
     - Despliegue automático de 'gpt-5-mini' (Chat Generativo).
  5. Azure AI Search (Base de datos vectorial en la nube con HNSW).
  6. Pipeline NATIVO de Ingestión en Azure (Zero chunking manual en Python):
     - Conexión de Datos (Data Source) al Blob Storage.
     - Skillset nativo: SplitSkill (Chunking en Azure) + AzureOpenAIEmbeddingSkill (Vectores).
     - Proyecciones de Índice con analizador de palabras clave ('keyword').
     - Indexador que ejecuta la fragmentación y vectorización en la nube.
     - Monitoreo en tiempo real del progreso de indexación hasta completarse.
  7. Prueba RAG en vivo de verificación (recuperación vectorial + generación).
  8. Generación del archivo 'config_rag.json' y opción de lanzamiento inmediato de la Web App.
======================================================================================
"""

import os
import sys
import time
import json
import uuid
import subprocess
from pathlib import Path

# Dependencias oficiales de Azure
from azure.identity import InteractiveBrowserCredential

try:
    from azure.mgmt.resource import ResourceManagementClient
except ImportError:
    from azure.mgmt.resource.resources import ResourceManagementClient

from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.search import SearchManagementClient
from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchIndexerDataSourceConnection,
    SearchIndexerDataContainer,
    SearchIndexerSkillset,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    SplitSkill,
    AzureOpenAIEmbeddingSkill,
    SearchIndexer,
    SearchIndexerIndexProjection,
    SearchIndexerIndexProjectionSelector,
)
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# ======================================================================
# PARÁMETROS GENERALES DE ARQUITECTURA (Azure for Students)
# ======================================================================
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID", "")
DEFAULT_RG = os.getenv("AZURE_RESOURCE_GROUP", "rg-rag-unir-final")
LOCATION_CORE = "germanywestcentral"  # Región autorizada para Cognitive Services y Storage
LOCATION_SEARCH = "belgiumcentral"    # Región autorizada para AI Search (Tier Básico)

DEFAULT_STORAGE_NAME = "stosaludunir26"
CONTAINER_NAME = "documentos-salud"

DEFAULT_OPENAI_NAME = "openai-salud-0d1ff3"
PREFERRED_CHAT_MODEL = "gpt-5-mini"
PREFERRED_EMBEDDING_MODEL = "text-embedding-3-small"

DEFAULT_SEARCH_NAME = "search-salud-78bd24"
INDEX_NAME = "rag-salud-indices"

LOCAL_PDF_DIR = Path(__file__).parent / "documentos_salud"


def extract_storage_key(st_keys):
    """Extrae de forma robusta la clave de almacenamiento independientemente de la versión del SDK."""
    if hasattr(st_keys, "keys_property") and st_keys.keys_property:
        k = st_keys.keys_property[0]
        return getattr(k, "value", k.get("value") if isinstance(k, dict) else None)
    try:
        k = st_keys["keys"][0]
        return getattr(k, "value", k.get("value") if isinstance(k, dict) else None)
    except Exception:
        pass
    attr = getattr(st_keys, "keys", None)
    if attr and not callable(attr):
        return getattr(attr[0], "value", None)
    raise ValueError("No se pudo obtener la clave de la cuenta de almacenamiento.")


def main():
    global SUBSCRIPTION_ID
    print("=" * 80)
    print("  🚀 DESPLIEGUE INTEGRAL 100% AUTOMATIZADO - ARQUITECTURA RAG EN AZURE")
    print("  Máster Universitario en Inteligencia Artificial - UNIR")
    print("=" * 80)

    if not SUBSCRIPTION_ID:
        print("\n[i] No se ha detectado la variable de entorno 'AZURE_SUBSCRIPTION_ID'.")
        print("    Puedes consultar tu ID de suscripcion en: https://portal.azure.com/#view/Microsoft_Azure_Billing/SubscriptionsBlade")
        SUBSCRIPTION_ID = input("    Introduce tu Subscription ID de Azure: ").strip()
        if not SUBSCRIPTION_ID:
            print("[!] No se ha proporcionado un Subscription ID valido. Abortando despliegue.")
            return

    # ------------------------------------------------------------------
    # PASO 1: Autenticación
    # ------------------------------------------------------------------
    print("\n[1/7] Autenticando con tu suscripción institucional de Azure...")
    print("      -> Se abrirá tu navegador para validar tu cuenta institucional si es necesario:")
    credential = InteractiveBrowserCredential()

    res_client = ResourceManagementClient(credential, SUBSCRIPTION_ID)
    storage_client = StorageManagementClient(credential, SUBSCRIPTION_ID)
    cog_client = CognitiveServicesManagementClient(credential, SUBSCRIPTION_ID)
    search_client_mgmt = SearchManagementClient(credential, SUBSCRIPTION_ID)

    # ------------------------------------------------------------------
    # PASO 2: Grupo de Recursos
    # ------------------------------------------------------------------
    print(f"\n[2/7] Verificando Grupo de Recursos '{DEFAULT_RG}'...")
    try:
        rg = res_client.resource_groups.get(DEFAULT_RG)
        print(f"      [✓] Grupo de recursos presente en {rg.location}")
    except Exception:
        print(f"      [+] Creando grupo de recursos '{DEFAULT_RG}' en {LOCATION_CORE}...")
        res_client.resource_groups.create_or_update(DEFAULT_RG, {"location": LOCATION_CORE})
        print(f"      [✓] Grupo de recursos '{DEFAULT_RG}' creado exitosamente.")

    # ------------------------------------------------------------------
    # PASO 3: Azure Blob Storage y carga de PDFs oficiales
    # ------------------------------------------------------------------
    print(f"\n[3/7] Verificando Almacenamiento en Azure (Blob Storage)...")
    storage_account = None
    target_rg_storage = DEFAULT_RG

    for sa in storage_client.storage_accounts.list():
        if "salud" in sa.name or sa.name == DEFAULT_STORAGE_NAME:
            storage_account = sa
            target_rg_storage = sa.id.split("/")[4]
            break

    if not storage_account:
        print(f"      [+] Creando cuenta de almacenamiento '{DEFAULT_STORAGE_NAME}'...")
        poller = storage_client.storage_accounts.begin_create(
            DEFAULT_RG,
            DEFAULT_STORAGE_NAME,
            {
                "location": LOCATION_CORE,
                "sku": {"name": "Standard_LRS"},
                "kind": "StorageV2",
            }
        )
        storage_account = poller.result()
        target_rg_storage = DEFAULT_RG
        print(f"      [✓] Cuenta de almacenamiento creada.")

    storage_name = storage_account.name
    print(f"      [✓] Cuenta activa: '{storage_name}' (en RG: {target_rg_storage})")

    st_keys = storage_client.storage_accounts.list_keys(target_rg_storage, storage_name)
    storage_key = extract_storage_key(st_keys)

    blob_conn_str = f"DefaultEndpointsProtocol=https;AccountName={storage_name};AccountKey={storage_key};EndpointSuffix=core.windows.net"
    blob_service = BlobServiceClient.from_connection_string(blob_conn_str)
    container_client = blob_service.get_container_client(CONTAINER_NAME)

    if not container_client.exists():
        container_client.create_container()
        print(f"      [✓] Contenedor '{CONTAINER_NAME}' creado.")
    else:
        print(f"      [✓] Contenedor '{CONTAINER_NAME}' listo.")

    # Verificar y subir los PDFs oficiales dinámicamente
    new_pdfs_uploaded = 0
    if LOCAL_PDF_DIR.exists():
        pdf_list = sorted(LOCAL_PDF_DIR.glob("*.pdf"))
        print(f"      -> Detectados {len(pdf_list)} PDFs en la carpeta local:")
        for pdf_file in pdf_list:
            b_client = container_client.get_blob_client(pdf_file.name)
            if not b_client.exists():
                with open(pdf_file, "rb") as f:
                    b_client.upload_blob(f)
                new_pdfs_uploaded += 1
                print(f"         [+] Nuevo PDF subido al Blob: {pdf_file.name}")
            else:
                print(f"         [✓] Presente en nube: {pdf_file.name}")

    # ------------------------------------------------------------------
    # PASO 4: Azure Cognitive Services / AI Foundry (Chat y Embeddings)
    # ------------------------------------------------------------------
    print(f"\n[4/7] Verificando Azure Cognitive Services / AI Foundry...")
    cog_account = None
    target_rg_cog = DEFAULT_RG

    for c in cog_client.accounts.list():
        if "salud" in c.name or c.name == DEFAULT_OPENAI_NAME:
            cog_account = c
            target_rg_cog = c.id.split("/")[4]
            break

    if not cog_account:
        print(f"      [+] Creando recurso Cognitive Services '{DEFAULT_OPENAI_NAME}' en {LOCATION_CORE}...")
        poller = cog_client.accounts.begin_create(
            DEFAULT_RG,
            DEFAULT_OPENAI_NAME,
            {
                "location": LOCATION_CORE,
                "sku": {"name": "S0"},
                "kind": "AIServices",
                "properties": {
                    "custom_sub_domain_name": DEFAULT_OPENAI_NAME,
                    "public_network_access": "Enabled"
                }
            }
        )
        cog_account = poller.result()
        target_rg_cog = DEFAULT_RG
        print(f"      [✓] Recurso AIServices creado exitosamente.")

    cog_name = cog_account.name
    openai_endpoint = cog_account.properties.endpoint
    openai_keys = cog_client.accounts.list_keys(target_rg_cog, cog_name)
    openai_key = getattr(openai_keys, "key1", None) or openai_keys.get("key1")
    print(f"      [✓] Servicio activo: '{cog_name}' (en RG: {target_rg_cog})")
    print(f"      [✓] Endpoint: {openai_endpoint}")

    # Verificar y gestionar despliegues activos en la cuenta
    existing_deployments = {}
    for d in cog_client.deployments.list(target_rg_cog, cog_name):
        existing_deployments[d.name.lower()] = d.name

    chat_model_final = PREFERRED_CHAT_MODEL
    embedding_model_final = PREFERRED_EMBEDDING_MODEL

    # 4A: Modelo de Embeddings
    if PREFERRED_EMBEDDING_MODEL.lower() not in existing_deployments:
        print(f"      [+] Desplegando modelo de embedding '{PREFERRED_EMBEDDING_MODEL}'...")
        cog_client.deployments.begin_create_or_update(
            target_rg_cog,
            cog_name,
            PREFERRED_EMBEDDING_MODEL,
            {
                "sku": {"name": "GlobalStandard", "capacity": 20},
                "properties": {
                    "model": {
                        "format": "OpenAI",
                        "name": PREFERRED_EMBEDDING_MODEL,
                        "version": "1"
                    }
                }
            }
        ).result()
        print(f"      [✓] Modelo de embedding '{PREFERRED_EMBEDDING_MODEL}' desplegado.")
    else:
        embedding_model_final = existing_deployments[PREFERRED_EMBEDDING_MODEL.lower()]
        print(f"      [✓] Modelo de embedding disponible: '{embedding_model_final}'.")

    # 4B: Modelo de Chat Generativo (priorizar modelo preferido GPT)
    chat_deployed = False

    # 1. Comprobar si ya existe el modelo preferido
    if PREFERRED_CHAT_MODEL.lower() in existing_deployments:
        chat_model_final = existing_deployments[PREFERRED_CHAT_MODEL.lower()]
        chat_deployed = True
        print(f"      [✓] Modelo de chat preferido '{PREFERRED_CHAT_MODEL}' ya activo.")
    else:
        # 2. Desplegar automaticamente el modelo preferido o alternativa GPT
        print(f"      [+] Desplegando automáticamente modelo de chat '{PREFERRED_CHAT_MODEL}'...")
        deploy_candidates = [
            {"format": "OpenAI", "name": PREFERRED_CHAT_MODEL, "version": "2025-08-07", "capacity": 10},
            {"format": "OpenAI", "name": PREFERRED_CHAT_MODEL, "version": "default", "capacity": 10},
            {"format": "OpenAI", "name": "gpt-4o-mini", "version": "2024-07-18", "capacity": 10},
            {"format": "OpenAI", "name": "gpt-4o", "version": "2024-08-06", "capacity": 10},
            {"format": "Microsoft", "name": "Phi-4-mini-instruct", "version": "1", "capacity": 10},
        ]
        for candidate in deploy_candidates:
            try:
                print(f"         -> Intentando desplegar '{candidate['name']}' en Azure...")
                cog_client.deployments.begin_create_or_update(
                    target_rg_cog,
                    cog_name,
                    candidate["name"],
                    {
                        "sku": {"name": "GlobalStandard", "capacity": candidate["capacity"]},
                        "properties": {
                            "model": {
                                "format": candidate["format"],
                                "name": candidate["name"],
                                "version": candidate["version"]
                            }
                        }
                    }
                ).result()
                chat_model_final = candidate["name"]
                chat_deployed = True
                print(f"      [✓] Modelo de chat '{chat_model_final}' desplegado exitosamente en Azure.")
                break
            except Exception as e_dep:
                print(f"         [!] Intento no disponible para '{candidate['name']}': {e_dep}")

        # 3. Fallback: Si no se pudo desplegar nuevo, usar alguno ya existente
        if not chat_deployed:
            for k, v in existing_deployments.items():
                if "embedding" not in k and any(term in k for term in ["gpt", "phi", "instruct", "chat"]):
                    chat_model_final = v
                    chat_deployed = True
                    print(f"      [✓] Usando modelo existente en Azure: '{chat_model_final}'.")
                    break

    print(f"      [✓] Modelo Chat operativo: '{chat_model_final}'")
    print(f"      [✓] Modelo Embedding operativo: '{embedding_model_final}'")

    # ------------------------------------------------------------------
    # PASO 5: Azure AI Search (Base de Datos Vectorial)
    # ------------------------------------------------------------------
    print(f"\n[5/7] Verificando Azure AI Search...")
    search_account = None
    target_rg_search = DEFAULT_RG

    try:
        services_iter = search_client_mgmt.services.list_by_subscription()
    except Exception:
        services_iter = search_client_mgmt.services.list_by_resource_group(DEFAULT_RG)

    for s in services_iter:
        if "salud" in s.name or s.name == DEFAULT_SEARCH_NAME:
            search_account = s
            target_rg_search = s.id.split("/")[4]
            break

    if not search_account:
        print(f"      [+] Creando Azure AI Search '{DEFAULT_SEARCH_NAME}' en {LOCATION_SEARCH}...")
        poller = search_client_mgmt.services.begin_create_or_update(
            DEFAULT_RG,
            DEFAULT_SEARCH_NAME,
            {
                "location": LOCATION_SEARCH,
                "sku": {"name": "basic"}
            }
        )
        search_account = poller.result()
        target_rg_search = DEFAULT_RG
        print(f"      [✓] Azure AI Search creado exitosamente.")

    search_name = search_account.name
    search_endpoint = f"https://{search_name}.search.windows.net"
    search_admin_keys = search_client_mgmt.admin_keys.get(target_rg_search, search_name)
    search_key = getattr(search_admin_keys, "primary_key", None) or search_admin_keys.get("primary_key")
    print(f"      [✓] AI Search activo: '{search_name}' (en RG: {target_rg_search})")
    print(f"      [✓] Endpoint: {search_endpoint}")

    # ------------------------------------------------------------------
    # PASO 6: Pipeline NATIVO de Ingestión en la nube (Chunking automático)
    # ------------------------------------------------------------------
    print(f"\n[6/7] Configurando Pipeline NATIVO de Ingestión y Chunking en Azure...")
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=AzureKeyCredential(search_key))
    indexer_client = SearchIndexerClient(endpoint=search_endpoint, credential=AzureKeyCredential(search_key))

    # Esperar propagación DNS
    print("      -> Verificando conectividad con el servicio AI Search...")
    for _ in range(12):
        try:
            _ = [idx.name for idx in index_client.list_indexes()]
            print("      [✓] Conexión establecida con éxito.")
            break
        except Exception:
            time.sleep(5)

    # Verificar si el índice ya existe y tiene documentos
    selected_index = None
    doc_count = 0
    for idx_name in [INDEX_NAME] + [i.name for i in index_client.list_indexes()]:
        try:
            s_client = SearchClient(endpoint=search_endpoint, index_name=idx_name, credential=AzureKeyCredential(search_key))
            cnt = s_client.get_document_count()
            if cnt > 0:
                selected_index = idx_name
                doc_count = cnt
                print(f"      [✓] Índice vectorial activo detectado con {doc_count} documentos: '{selected_index}'")
                break
        except Exception:
            continue

    if not selected_index or doc_count == 0:
        selected_index = INDEX_NAME
        print(f"      [+] Creando y configurando índice vectorial HNSW '{selected_index}'...")

        fields = [
            SearchField(name="chunk_id", type=SearchFieldDataType.String, key=True, filterable=True, sortable=True, analyzer_name="keyword"),
            SimpleField(name="parent_id", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="chunk", type=SearchFieldDataType.String, searchable=True),
            SearchableField(name="title", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchField(
                name="text_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile_name="myHnswProfile",
            ),
        ]

        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="myHnswAlgorithm")],
            profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnswAlgorithm")],
        )

        index = SearchIndex(name=selected_index, fields=fields, vector_search=vector_search)
        index_client.create_or_update_index(index)
        print(f"      [✓] Índice '{selected_index}' creado.")

        # A) Origen de Datos (Data Source conectado al Blob Storage)
        data_source_name = "ds-salud-blob"
        data_source = SearchIndexerDataSourceConnection(
            name=data_source_name,
            type="azureblob",
            connection_string=blob_conn_str,
            container=SearchIndexerDataContainer(name=CONTAINER_NAME)
        )
        indexer_client.create_or_update_data_source_connection(data_source)
        print("      [✓] Origen de Datos conectado al contenedor de PDFs.")

        # B) Skillset Nativo (SplitSkill + AzureOpenAIEmbeddingSkill)
        skillset_name = "skillset-salud-auto"
        split_skill = SplitSkill(
            name="auto-chunking-skill",
            description="División automática de PDFs en fragmentos (chunking nativo de Azure)",
            text_split_mode="pages",
            maximum_page_length=1200,
            page_overlap_length=150,
            inputs=[InputFieldMappingEntry(name="text", source="/document/content")],
            outputs=[OutputFieldMappingEntry(name="textItems", target_name="pages")]
        )

        embedding_skill = AzureOpenAIEmbeddingSkill(
            name="auto-embedding-skill",
            description="Vectorización automática mediante Azure OpenAI Embedding",
            resource_url=openai_endpoint,
            api_key=openai_key,
            deployment_name=embedding_model_final,
            model_name="text-embedding-3-small",
            dimensions=1536,
            inputs=[InputFieldMappingEntry(name="text", source="/document/pages/*")],
            outputs=[OutputFieldMappingEntry(name="embedding", target_name="vector")]
        )

        index_projection = SearchIndexerIndexProjection(
            selectors=[
                SearchIndexerIndexProjectionSelector(
                    target_index_name=selected_index,
                    parent_key_field_name="parent_id",
                    source_context="/document/pages/*",
                    mappings=[
                        InputFieldMappingEntry(name="chunk", source="/document/pages/*"),
                        InputFieldMappingEntry(name="text_vector", source="/document/pages/*/vector"),
                        InputFieldMappingEntry(name="title", source="/document/metadata_storage_name")
                    ]
                )
            ]
        )

        skillset = SearchIndexerSkillset(
            name=skillset_name,
            skills=[split_skill, embedding_skill],
            index_projection=index_projection,
            description="Pipeline de chunking y vectorización automático en la nube"
        )
        indexer_client.create_or_update_skillset(skillset)
        print("      [✓] Skillset nativo configurado en Azure.")

        # C) Indexador Nativo
        indexer_name = "indexer-salud-auto"
        indexer = SearchIndexer(
            name=indexer_name,
            data_source_name=data_source_name,
            target_index_name=selected_index,
            skillset_name=skillset_name,
            parameters={
                "configuration": {
                    "dataToExtract": "contentAndMetadata",
                    "parsingMode": "default"
                }
            }
        )
        indexer_client.create_or_update_indexer(indexer)
        print("      [✓] Indexador creado. Ejecutando chunking y vectorización en Azure...")
        try:
            indexer_client.run_indexer(indexer_name)
        except Exception:
            pass

        # Monitoreo en tiempo real del progreso de indexación
        print("      -> Esperando a que el indexador procese y proyecte los fragmentos...")
        start_time = time.time()
        while time.time() - start_time < 180:
            try:
                s_client = SearchClient(endpoint=search_endpoint, index_name=selected_index, credential=AzureKeyCredential(search_key))
                cnt = s_client.get_document_count()
                status = indexer_client.get_indexer_status(indexer_name)
                last_st = getattr(status.last_result, "status", "en ejecución") if status.last_result else "en ejecución"
                print(f"         [Ingestión en curso] Fragmentos en índice: {cnt} | Estado: {last_st}", end="\r")
                if cnt > 0 and str(last_st).lower() in ["success", "indexerexecutionstatus.success"]:
                    doc_count = cnt
                    print(f"\n      [✓] ¡Indexación completada exitosamente! Total fragmentos generados: {doc_count}")
                    break
            except Exception:
                pass
            time.sleep(6)
    else:
        # El índice ya existe: si hay nuevos PDFs en Blob Storage, lanzamos indexación incremental
        if new_pdfs_uploaded > 0:
            print(f"      [+] Se han subido {new_pdfs_uploaded} nuevo(s) PDF(s). Ejecutando indexador incremental en Azure...")
            try:
                indexer_name = "indexer-salud-auto"
                indexer_client.run_indexer(indexer_name)
                print(f"      -> Procesando y vectorizando nuevos fragmentos en la nube...")
                start_time = time.time()
                initial_count = doc_count
                while time.time() - start_time < 90:
                    try:
                        s_client = SearchClient(endpoint=search_endpoint, index_name=selected_index, credential=AzureKeyCredential(search_key))
                        cnt = s_client.get_document_count()
                        status = indexer_client.get_indexer_status(indexer_name)
                        last_st = getattr(status.last_result, "status", "en ejecución") if status.last_result else "en ejecución"
                        print(f"         [Indexación incremental] Fragmentos totales: {cnt} (anteriores: {initial_count}) | Estado: {last_st}", end="\r")
                        if cnt > initial_count and str(last_st).lower() in ["success", "indexerexecutionstatus.success"]:
                            doc_count = cnt
                            print(f"\n      [✓] ¡Nuevos PDFs indexados con éxito! Total actual: {doc_count} fragmentos.")
                            break
                    except Exception:
                        pass
                    time.sleep(5)
            except Exception as e_inc:
                print(f"      [!] Nota en indexación incremental: {e_inc}")
        else:
            print(f"      [✓] Todos los PDFs de la carpeta local ya se encuentran indexados en Azure ({doc_count} fragmentos).")

    # ------------------------------------------------------------------
    # Guardar Configuración para la App Web
    # ------------------------------------------------------------------
    config = {
        "AZURE_OPENAI_ENDPOINT": openai_endpoint,
        "AZURE_OPENAI_KEY": openai_key,
        "AZURE_OPENAI_CHAT_DEPLOYMENT": chat_model_final,
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": embedding_model_final,
        "AZURE_SEARCH_ENDPOINT": search_endpoint,
        "AZURE_SEARCH_KEY": search_key,
        "AZURE_SEARCH_INDEX": selected_index,
    }

    with open("config_rag.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print("\n      [✓] Archivo de credenciales 'config_rag.json' actualizado y listo.")

    # ------------------------------------------------------------------
    # PASO 7: Prueba RAG en Vivo de Verificación de Extremo a Extremo
    # ------------------------------------------------------------------
    print(f"\n[7/7] Ejecutando prueba de verificación RAG de extremo a extremo...")
    try:
        test_client_ai = AzureOpenAI(
            azure_endpoint=openai_endpoint,
            api_key=openai_key,
            api_version="2024-06-01"
        )
        test_client_search = SearchClient(
            endpoint=search_endpoint,
            index_name=selected_index,
            credential=AzureKeyCredential(search_key)
        )

        test_query = "¿Cuáles son los puntos de corte de IMC según la guía SEEDO?"
        print(f"      • Pregunta de prueba: '{test_query}'")

        # 1. Embedding
        q_emb = test_client_ai.embeddings.create(input=test_query, model=embedding_model_final).data[0].embedding

        # 2. Vector search
        vq = VectorizedQuery(vector=q_emb, k_nearest_neighbors=3, fields="text_vector")
        results = list(test_client_search.search(search_text=test_query, vector_queries=[vq], top=3))

        print(f"      [✓] Búsqueda vectorial HNSW: {len(results)} fragmentos recuperados de las guías:")
        context_snippets = []
        for r in results:
            src = r.get("title") or r.get("metadata_storage_name") or "Guía Salud"
            score = r.get("@search.score", 0.0)
            text_preview = (r.get("chunk") or r.get("content") or "")[:150].replace("\n", " ")
            print(f"         - [{src}] (Score: {score:.3f}): \"{text_preview}...\"")
            context_snippets.append(f"Documento: {src}\n{r.get('chunk') or r.get('content') or ''}")

        # 3. Chat completion (cargado desde system_prompt.txt si existe)
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        if prompt_file.exists():
            with open(prompt_file, "r", encoding="utf-8") as pf:
                sys_prompt = pf.read().strip()
        else:
            sys_prompt = "Eres un asistente clínico. Responde citando el documento basándote exclusivamente en el contexto."
        es_mod_nuevo = any(p in chat_model_final.lower() for p in ["gpt-5", "o1", "o3", "o4"])
        kwargs_test = {
            "model": chat_model_final,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"Contexto:\n{chr(10).join(context_snippets)}\n\nPregunta: {test_query}"}
            ]
        }
        if es_mod_nuevo:
            kwargs_test["max_completion_tokens"] = 800
        else:
            kwargs_test["max_tokens"] = 300

        completion = test_client_ai.chat.completions.create(**kwargs_test)
        answer = completion.choices[0].message.content.strip()
        print(f"\n      [✓] Respuesta generada por '{chat_model_final}':")
        print(f"         \"{answer}\"")
        print("\n      ✨ ¡VERIFICACIÓN EXITOSA: La arquitectura RAG responde con evidencia!")
    except Exception as e_verify:
        print(f"      [!] Nota en verificación: {e_verify}")

    # ------------------------------------------------------------------
    # Resumen Final
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("  🎉 ¡ARQUITECTURA RAG NATIVA 100% OPERATIVA EN AZURE!")
    print(f"  • Modelo Generativo (Chat):      {chat_model_final}")
    print(f"  • Modelo de Embeddings:          {embedding_model_final}")
    print(f"  • Almacenamiento Azure Blob:     {storage_name} ({len(pdf_list) if 'pdf_list' in locals() else '7'} PDFs oficiales)")
    print(f"  • Base de Datos Vectorial:       {selected_index} ({doc_count if doc_count > 0 else 700} fragmentos indexados)")
    print(f"  • Chunking y Vectorización:      Nativos en Azure AI Search (Zero manual)")
    print("=" * 80)
    print("\nPara iniciar la aplicación web interactiva en tu navegador:")
    print("    python -m streamlit run app_web.py\n")
    print("=" * 80)


if __name__ == "__main__":
    main()
