# Asistente RAG Especializado en Salud, Nutricion y Control de Peso
### Master Universitario en Inteligencia Artificial - UNIR
**Asignatura:** Integracion y Operativizacion de Modelos Generativos en Aplicaciones Empresariales (Actividad 02)

---

## 1. Descripcion del Proyecto

Este repositorio implementa un **asistente conversacional especializado en salud, habitos saludables, nutricion y control de peso** siguiendo una arquitectura **RAG (Retrieval-Augmented Generation)** desplegada en **Microsoft Azure**.

El sistema responde preguntas en lenguaje natural de manera exacta y **citando rigurosamente las fuentes** oficiales indexadas (AESAN, SEEDO, SENC, Ministerio de Sanidad y AEMPS).

El proyecto se opera y ejecuta mediante dos componentes principales:
1. **`desplegar_todo_azure.py`**: Script de despliegue integral automatizado que aprovisiona todos los recursos en Azure, sube los documentos, crea el indice vectorial con chunking nativo y genera el archivo de configuracion.
2. **`app_web.py`**: Aplicacion web interactiva en **Streamlit** que implementa la interfaz conversacional, recuperacion vectorial y visualizacion de citas a los documentos oficiales.

---

## 2. Estructura del Repositorio

```text
.
|-- desplegar_todo_azure.py    # Script integral de despliegue automatico en Azure
|-- app_web.py                 # Interfaz Web interactiva (Streamlit) del Asistente RAG
|-- probar_gpt.py              # Script de prueba e integracion de modelos GPT por consola
|-- system_prompt.txt          # Directivas y reglas de comportamiento del Asistente (Prompt externo)
|-- requirements.txt           # Dependencias de Python necesarias
|-- config_rag.json.example    # Plantilla de configuracion (sin claves) para despliegues
|-- config_rag.json            # Configuracion generada automaticamente con claves privadas (ignorado en Git)
|-- .gitignore                 # Exclusion de credenciales privadas y temporales de Python
|-- documentos_salud/          # Corpus documental oficial en PDF (7 documentos)
|   |-- 01_AESAN_Recomendaciones_Dieteticas_y_Actividad_Fisica.pdf
|   |-- 02_AESAN_Informe_Cientifico_Pautas_Dieteticas.pdf
|   |-- 03_SENC_Guia_Alimentacion_Saludable.pdf
|   |-- 04_SEEDO_Guia_GIRO_Manejo_Obesidad_Adultos.pdf
|   |-- 05_Sanidad_Actividad_Fisica_para_la_Salud.pdf
|   |-- 06_AEMPS_IPT_Wegovy_Semaglutida_Obesidad.pdf
|   |-- 07_AEMPS_IPT_Mounjaro_Tirzepatida_Control_Peso.pdf
|   \-- README.md              # Descripcion detallada y justificacion clinica del corpus
\-- README.md                  # Este manual de instalacion y uso
```

---

## 3. Requisitos Previos

Cualquier persona que vaya a desplegar o evaluar este proyecto necesita:
1. **Suscripcion de Azure activa**: Cuenta de estudiante (*Azure for Students*) o suscripcion estandar con permisos de Colaborador o Propietario.
2. **Python 3.9 o superior** instalado en el sistema.
3. Conexion a Internet y navegador web.

---

## 4. Instalacion y Configuracion del Entorno

### Paso 1: Clonar o descargar el repositorio
Descarga el codigo o clona el repositorio en una carpeta local de tu equipo.

### Paso 2: Crear y activar un entorno virtual de Python
* **En Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```
* **En macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Paso 3: Instalar dependencias de Python
Instala todas las librerias necesarias con un unico comando:
```bash
pip install -r requirements.txt
```
*(Incluye Streamlit, Azure SDK, Azure Search, Azure Management y OpenAI).*

---

## 5. Es necesario instalar el cliente de Azure CLI?

* **Para ejecutar el proyecto con los scripts (`desplegar_todo_azure.py` y `app_web.py`):**  
  **NO es obligatorio tener instalado Azure CLI**, ya que el script utiliza la libreria oficial `azure-identity` (`InteractiveBrowserCredential`), la cual abre automaticamente una ventana del navegador web para autenticar tu cuenta de Azure de forma transparente.
* **Si prefieres gestionar recursos o autenticarte desde tu terminal:**  
  Es recomendable instalar **Azure CLI (`az`)**:
  * **Windows:** Abre PowerShell y ejecuta `winget install -e --id Microsoft.AzureCLI` (o descarga el instalador MSI en https://aka.ms/installazurecliwindows).
  * **macOS:** Ejecuta `brew install azure-cli`.
  * **Linux (Ubuntu/Debian):** Ejecuta `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash`.
  * **Comando para iniciar sesion:** `az login`

---

## 6. Guia de Ejecucion Paso a Paso

### Paso 1: Configurar la suscripcion de Azure
Por defecto, el script intentara usar el ID de suscripcion configurado o el que indiques en la variable de entorno:
* **Windows (PowerShell):**
  ```powershell
  $env:AZURE_SUBSCRIPTION_ID = "tu-subscription-id-aqui"
  ```
* **macOS / Linux:**
  ```bash
  export AZURE_SUBSCRIPTION_ID="tu-subscription-id-aqui"
  ```
*(Si no defines la variable, se utilizara la suscripcion configurada por defecto en el script).*

### Paso 2: Ejecutar el despliegue automatico en Azure (`desplegar_todo_azure.py`)
Ejecuta el script de aprovisionamiento:
```bash
python desplegar_todo_azure.py
```

#### Que hace este script de forma 100% automatizada?
1. **Autenticacion:** Abre el navegador mediante `InteractiveBrowserCredential` para iniciar sesion con tu cuenta de Azure.
2. **Grupo de Recursos:** Crea o verifica el grupo de recursos unificado (`rg-rag-unir-final`).
3. **Blob Storage y Carga de PDFs:** Crea la cuenta de almacenamiento en Azure y sube dinamicamente todos los archivos `.pdf` de la carpeta `documentos_salud/`.
4. **Cognitive Services / AI Foundry:** Despliega el modelo de embeddings (`text-embedding-3-small`) y el modelo generativo (`Phi-4-mini-instruct` o `gpt-4o-mini`).
5. **Azure AI Search:** Aprovisiona el servicio de busqueda vectorial en la nube (con algoritmo HNSW).
6. **Pipeline Nativo de Ingestion RAG:**
   * Crea el Data Source apuntando al Blob Storage.
   * Configura el Skillset nativo de Azure (`SplitSkill` para chunking + `AzureOpenAIEmbeddingSkill` para vectorizacion).
   * Crea y ejecuta el Indexador, monitoreando el progreso hasta indexar todos los documentos.
7. **Prueba en vivo:** Realiza una consulta RAG de prueba validando la recuperacion y generacion.
8. **Configuracion local:** Genera el archivo `config_rag.json` con los endpoints y claves necesarias para la aplicacion web.

---

### Paso 3: Lanzar la Interfaz Web (`app_web.py`)
Una vez finalizado el despliegue y generado `config_rag.json`, inicia la aplicacion web interactiva en Streamlit:
```bash
streamlit run app_web.py
```
Se abrira automaticamente en tu navegador (por defecto en `http://localhost:8501`).

#### Caracteristicas de la Web App:
* **Busqueda Vectorial Hibrida:** Recupera los fragmentos mas relevantes de los documentos oficiales con control de Top-K y Temperatura.
* **Citas rigurosas a las fuentes:** Muestra badges y tarjetas desplegables con el nombre del documento, seccion exacta y fragmento de texto original.
* **Bateria de preguntas de evaluacion predefinidas:** Permite probar con un solo clic consultas de IMC, pautas dieteticas de AESAN, recomendaciones de ejercicio de Sanidad y criterios oficiales de farmacos para la obesidad (Wegovy y Mounjaro).

---

## 7. Corpus Documental Incluido

El directorio [`documentos_salud/`](./documentos_salud) contiene los 7 documentos oficiales que sustentan las respuestas:
* `01_AESAN_Recomendaciones_Dieteticas_y_Actividad_Fisica.pdf` (AESAN)
* `02_AESAN_Informe_Cientifico_Pautas_Dieteticas.pdf` (Comite Cientifico AESAN)
* `03_SENC_Guia_Alimentacion_Saludable.pdf` (Sociedad Espanola de Nutricion Comunitaria)
* `04_SEEDO_Guia_GIRO_Manejo_Obesidad_Adultos.pdf` (Sociedad Espanola de Obesidad)
* `05_Sanidad_Actividad_Fisica_para_la_Salud.pdf` (Ministerio de Sanidad)
* `06_AEMPS_IPT_Wegovy_Semaglutida_Obesidad.pdf` (AEMPS - Semaglutida / Wegovy)
* `07_AEMPS_IPT_Mounjaro_Tirzepatida_Control_Peso.pdf` (AEMPS - Tirzepatida / Mounjaro)

---

