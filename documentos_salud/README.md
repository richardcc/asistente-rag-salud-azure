# Corpus Documental Oficial - Asistente RAG de Salud, Nutricion y Control de Peso

Este directorio contiene las fuentes oficiales y guias clinicas contrastadas que constituyen la base de conocimiento indexada en **Azure AI Search** mediante el pipeline RAG en **Azure AI Foundry**.

---

## 1. Relacion de Documentos

### [01_AESAN_Recomendaciones_Dieteticas_y_Actividad_Fisica.pdf](./01_AESAN_Recomendaciones_Dieteticas_y_Actividad_Fisica.pdf)
* **Organismo emisor:** Agencia Espanola de Seguridad Alimentaria y Nutricion (AESAN) / Ministerio de Consumo.
* **Tamano:** 8.79 MB.
* **Tematica:** Guia divulgativa con recomendaciones dieteticas saludables y sostenibles complementadas con pautas de actividad fisica para la poblacion espanola ("Come sano, muevete y cuida tu planeta").
* **Uso en el asistente:** Responder sobre pautas de alimentacion diaria, frecuencias de consumo de alimentos, grupos nutricionales e impacto en la sostenibilidad.

---

### [02_AESAN_Informe_Cientifico_Pautas_Dieteticas.pdf](./02_AESAN_Informe_Cientifico_Pautas_Dieteticas.pdf)
* **Organismo emisor:** Comite Cientifico de la AESAN.
* **Tamano:** 0.58 MB.
* **Tematica:** Informe tecnico-cientifico con la justificacion y evidencia medica rigurosa de las recomendaciones nutricionales y los requerimientos caloricos/nutricionales.
* **Uso en el asistente:** Aportar el soporte cientifico ante consultas sobre macronutrientes, micronutrientes, ultraprocesados y evidencia clinica de las pautas.

---

### [03_SENC_Guia_Alimentacion_Saludable.pdf](./03_SENC_Guia_Alimentacion_Saludable.pdf)
* **Organismo emisor:** Sociedad Espanola de Nutricion Comunitaria (SENC).
* **Tamano:** 0.37 MB.
* **Tematica:** Guia de la Alimentacion Saludable para atencion primaria y ciudadanos: piramide alimentaria, balance energetico, equilibrio emocional y tecnicas culinarias saludables.
* **Uso en el asistente:** Resolver dudas sobre raciones por persona, piramide nutricional, hidratacion y estilos de vida saludables integrales.

---

### [04_SEEDO_Guia_GIRO_Manejo_Obesidad_Adultos.pdf](./04_SEEDO_Guia_GIRO_Manejo_Obesidad_Adultos.pdf)
* **Organismo emisor:** Sociedad Espanola para el Estudio de la Obesidad (SEEDO).
* **Edicion:** 2a Edicion Oficial (Actualizada).
* **Tamano:** 3.61 MB.
* **Tematica:** Guia Espanola del Manejo Integral y Multidisciplinar de la Obesidad en Personas Adultas (Guia GIRO). Consenso clinico de referencia entre multiples sociedades medicas.
* **Uso en el asistente:** Consultas sobre control y reduccion de peso, clasificacion del IMC, riesgos comorbidos del sobrepeso, objetivos realistas de perdida ponderal, abordaje conductual y tratamiento farmacologico general.

---

### [05_Sanidad_Actividad_Fisica_para_la_Salud.pdf](./05_Sanidad_Actividad_Fisica_para_la_Salud.pdf)
* **Organismo emisor:** Ministerio de Sanidad (Estrategia de Promocion de la Salud y Prevencion en el SNS).
* **Tamano:** 4.86 MB.
* **Tematica:** Recomendaciones para la poblacion sobre actividad fisica para la salud y reduccion del sedentarismo (adaptacion nacional de las directrices de la OMS).
* **Uso en el asistente:** Responder a consultas sobre tiempos minimos de ejercicio aerobico, fuerza muscular, pasos recomendados al dia y mitigacion del sedentarismo en el ambito laboral y personal.

---

### [06_AEMPS_IPT_Wegovy_Semaglutida_Obesidad.pdf](./06_AEMPS_IPT_Wegovy_Semaglutida_Obesidad.pdf)
* **Organismo emisor:** Agencia Espanola de Medicamentos y Productos Sanitarios (AEMPS) / Ministerio de Sanidad.
* **Codigo oficial:** IPT-148/2023.
* **Tamano:** 0.44 MB.
* **Tematica:** Informe de Posicionamiento Terapeutico de **semaglutida (Wegovy)** como complemento a una dieta baja en calorias y aumento de la actividad fisica para el control del peso en adultos y adolescentes.
* **Uso en el asistente:** Criterios oficiales de indicacion (IMC >= 30 kg/m2 o IMC >= 27 kg/m2 con comorbilidades), mecanismo de accion (analogo GLP-1), posologia, eficacia en ensayos clinicos STEP, efectos adversos frecuentes (gastrointestinales) y precauciones.

---

### [07_AEMPS_IPT_Mounjaro_Tirzepatida_Control_Peso.pdf](./07_AEMPS_IPT_Mounjaro_Tirzepatida_Control_Peso.pdf)
* **Organismo emisor:** Agencia Espanola de Medicamentos y Productos Sanitarios (AEMPS) / Ministerio de Sanidad.
* **Codigo oficial:** IPT-305/2024.
* **Tamano:** 0.72 MB.
* **Tematica:** Informe de Posicionamiento Terapeutico de **tirzepatida (Mounjaro)** para el control de peso en adultos. Coagonista dual de los receptores GIP y GLP-1.
* **Uso en el asistente:** Criterios de prescripcion, mecanismo dual GIP/GLP-1, resultados en reduccion ponderal (ensayos SURMOUNT), titulacion de dosis, perfil de seguridad y advertencias regulatorias.

---

## 2. Ventajas del Corpus para el Asistente RAG

1. **Rigor e inmunidad ante alucinaciones:** Todas las fuentes provienen directamente de agencias reguladoras estatales (AEMPS, AESAN, Ministerio de Sanidad) y sociedades medicas de referencia (SEEDO, SENC).
2. **Cobertura integral (Estilo de Vida + Farmacoterapia):** Permite al asistente responder tanto a consultas sobre habitos naturales (dieta mediterranea, ejercicio, deficit calorico) como a preguntas frecuentes sobre los nuevos medicamentos para la obesidad (Wegovy, Mounjaro, analogos GLP-1/GIP) con datos clinicos y regulatorios oficiales.
3. **Citas verificables y precisas:** Los documentos cuentan con numeracion y tablas claras, permitiendo al LLM citar paginas, tablas y apartados concretos (requisito indispensable de la practica).
