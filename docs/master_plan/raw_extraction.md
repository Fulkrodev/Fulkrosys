# Master Plan — Extraccion bruta del spec v2.1

**Fecha**: 2026-04-13
**Fuente**: ENS_PLATFORM_MASTER_SPEC_v2.1
**Proposito**: datos en crudo para analisis de dependencias y orden optimo

---

## Motor 1 — Categorization Engine

**Seccion spec**: 5.1 (linea 2347)
**Descripcion**: Implementacion Python pura del Anexo I + CCN-STIC 803. Sin LLM en la decision. El consultor y el cliente responden preguntas guiadas de valoracion por dimension DICAT, el motor calcula la categoria (BASICA/MEDIA/ALTA) por regla del maximo, genera el acta E-012.
**Entregables**: E-012 (Acta de categorizacion)
**Dependencias declaradas**: ninguna (foundation)
**Motores que dependen de este**: Motor 3 (DdA necesita la categoria), Motor 5 (Obligations), Motor 22 (Technical Discovery alimenta categorizacion)
**Usa LLM/AI**: No — determinista puro
**Categoria**: foundation / operacion
**Complejidad declarada**: simple (codigo pseudocodigo incluido en spec)
**Estado actual en repo**: COMPLETO (cerrado al 100%, 16 endpoints, 2490 lineas test)

---

## Motor 2 — MAGERIT Risk Engine

**Seccion spec**: 5.1 (linea 2371)
**Descripcion**: Implementacion completa de MAGERIT v3 en Python. Catalogos precargados (activos, amenazas, salvaguardas mapeadas a 73 medidas Anexo II). Calculo intrinseco, efectivo, residual. Simulacion what-if. Versionado (spec dice versionado, implementacion usa freeze/unfreeze — ver ADR). Exportacion XML (spec decia PILAR .mgr, implementacion genera XML nativo — ver docs/limitations/pilar_export.md).
**Entregables**: Informe MAGERIT completo (PDF/DOCX/XML/XLSX), E-020 a E-026 (entregables individuales XLSX)
**Dependencias declaradas**: ninguna directa (foundation), pero spec dice "catalogos precargados" y "salvaguardas mapeadas a las 73 medidas del Anexo II"
**Motores que dependen de este**: Motor 4 (Gap Analysis compara estado actual vs MAGERIT), Motor 5 (Obligations convierte gaps en acciones), Motor 19 (Risk Mgmt del proyecto es diferente del AR MAGERIT pero coexiste)
**Usa LLM/AI**: No — determinista puro (simulacion is determinista)
**Categoria**: foundation / operacion
**Complejidad declarada**: complejo (spec incluye detalle extenso de formulas)
**Estado actual en repo**: COMPLETO (cerrado al 100%, 27 endpoints, 4269 lineas test, 191/191)

---

## Motor 3 — DdA Engine

**Seccion spec**: 5.1 (linea 2383)
**Descripcion**: Genera la Declaracion de Aplicabilidad completa con las 73 medidas. Itera las 73 medidas del Anexo II, consulta si aplica a la categoria del sistema, marca refuerzos aplicables segun categoria y dimensiones, rellena estado actual desde tabla controls, redacta justificacion de no-aplicabilidad con LLM groundeado en CCN-STIC 819. Versiona y deja lista para firma del RSEG via magic link.
**Entregables**: E-040 (DdA completa firmable)
**Dependencias declaradas**: Spec dice literal: "A partir del output del Motor 1 (categoria) y del estado de implantacion de los controles". Tambien: "consulta el grafo Cypher" (corpus ENS).
**Motores que dependen de este**: Motor 4 (Gap Analysis compara DdA vs estado actual), Motor 5 (Obligations), Motor 9 (Audit Prep verifica que DdA esta aprobada)
**Usa LLM/AI**: Si — para justificaciones de no-aplicabilidad (grounding CCN-STIC 819)
**Categoria**: operacion
**Complejidad declarada**: medio (6 pasos definidos en spec)
**Estado actual en repo**: STUB (solo __init__.py, tablas DB existen: dda_entries, controls, evidence, ens_measures con 0 filas, ens_reinforcements con 0 filas)

---

## Motor 4 — Gap Analysis Engine

**Seccion spec**: 5.1 (linea 2394)
**Descripcion**: Compara estado actual de cada control vs estado objetivo segun DdA. Genera lista priorizada de gaps con: medida afectada, severidad, esfuerzo estimado en horas, dependencias con otros gaps, quick win si/no. Priorizacion combina reglas deterministas con LLM para contexto del cliente.
**Entregables**: Lista priorizada de gaps (no tiene codigo E-XXX explicito en spec)
**Dependencias declaradas**: Spec dice literal: "Compara estado actual de cada control vs estado objetivo segun DdA" — depende de Motor 3 (DdA)
**Motores que dependen de este**: Motor 5 (Obligations convierte cada gap en obligaciones)
**Usa LLM/AI**: Si — para priorizacion contextual por sector del cliente
**Categoria**: operacion
**Complejidad declarada**: medio
**Estado actual en repo**: STUB (solo __init__.py, tablas DB: findings, remediation_plans)

---

## Motor 5 — Obligations & Planning Engine

**Seccion spec**: 5.1 (linea 2400)
**Descripcion**: CRITICO, ANTI-ALUCINACION. Convierte cada gap en obligaciones concretas ejecutables con entregable cerrado. Obligaciones vienen de biblioteca de plantillas JSON inmutables (~250 plantillas). 4 modos de ejecucion: consultor_genera_entregable, cliente_aporta_evidencia_via_link, accion_tecnica_remota_autorizada, accion_manual_cliente. Genera Plan de Ejecucion Gantt exportable.
**Entregables**: E-050 (Plan de Adecuacion), backlog de obligaciones ejecutables
**Dependencias declaradas**: Spec dice literal: "Convierte cada gap en obligaciones concretas" — depende de Motor 4 (Gap). Tambien usa Motor 12 (magic links para ejecucion), Motor 6 (Document Factory para generar entregables).
**Motores que dependen de este**: Motor 7 (Evidence recolecta evidencias de obligaciones), Motor 9 (Audit Prep verifica completitud)
**Usa LLM/AI**: Si parcial — LLM solo personaliza lenguaje, jamas inventa obligaciones ni criterios de aceptacion
**Categoria**: operacion / critico
**Complejidad declarada**: complejo (spec dice "motor mas diferenciador", incluye esquema JSON detallado)
**Estado actual en repo**: STUB (solo __init__.py, tabla DB: obligations)

---

## Motor 6 — Document Factory

**Seccion spec**: 5.1 (linea 2439)
**Descripcion**: Biblioteca de plantillas DOCX (docxtpl) para los ~110 entregables documentales. Pipeline: cargar plantilla, rellenar con datos cliente, LLM rellena huecos con grounding RAG, docxtpl produce .docx, LibreOffice CLI convierte a PDF, hash SHA-256 + firma Ed25519, envio via magic link para firma.
**Entregables**: ~110 entregables documentales (E-001 a E-500+, politicas E-100 a E-126, procedimientos E-200 a E-234)
**Dependencias declaradas**: Spec dice: "Los campos personalizados se rellenan con datos del cliente" — necesita datos de clients, projects, nominations. Tambien: "LLM con grounding RAG sobre el corpus" — necesita corpus ENS (semanas 3-5).
**Motores que dependen de este**: Motor 5 (genera entregables de obligaciones), Motor 7 (genera formularios de evidencia), Motor 9 (Audit Prep necesita entregables aprobados), Motor 13 (extiende Motor 6 para docs comerciales)
**Usa LLM/AI**: Si — para justificaciones, adaptacion por sector, resumenes ejecutivos
**Categoria**: transversal
**Complejidad declarada**: complejo (110 plantillas, pipeline de 7 pasos)
**Estado actual en repo**: STUB (solo __init__.py, tablas DB: documents, document_versions)

---

## Motor 7 — Evidence Collection Engine

**Seccion spec**: 5.1 (linea 2467)
**Descripcion**: Para cada control esperando evidencia: consulta plantilla de evidencia, genera magic link tipo evidencia_tecnica, envia email, valida formato al subir, calcula hash SHA-256, firma Ed25519, vincula a evidence con measure_id y control_id, programa fecha de caducidad, programa re-recoleccion al vencer.
**Entregables**: Evidence Vault con cadena de custodia verificable
**Dependencias declaradas**: Necesita Motor 12 (magic links para recoleccion), Motor 5 (obligaciones generan controles esperando evidencia), Motor 6 (plantillas de evidencia)
**Motores que dependen de este**: Motor 9 (Audit Prep verifica evidencias vigentes), Motor 10 (Audit Sim busca evidencias)
**Usa LLM/AI**: No — determinista
**Categoria**: operacion
**Complejidad declarada**: medio (8 pasos definidos)
**Estado actual en repo**: STUB (solo __init__.py, tabla DB: evidence)

---

## Motor 8 — Pentesting & Red Team Engine

**Seccion spec**: 5.1 (linea 2480)
**Descripcion**: CRITICO. Orquestador inteligente de herramientas open source de pentest y red team. Detecta sistema del cliente, planifica test segun categoria ENS, pide autorizacion via magic link, orquesta herramientas en red Docker aislada (pentest-net), normaliza resultados, mapea a medidas Anexo II + MITRE ATT&CK, genera informes ejecutivo + tecnico. 11 herramientas: Nmap, Nuclei, OpenVAS, ZAP, Metasploit, Prowler, CLARA, Lynis, Trivy, Semgrep, testssl.sh. LLM (Opus) interpreta resultados y redacta informe.
**Entregables**: E-702 (informe ejecutivo pentest), E-703 (informe tecnico pentest), E-704 (Red Team para Alta con Caldera)
**Dependencias declaradas**: Motor 12 (magic link autorizacion pentest), Motor 22 (Technical Discovery para detectar sistema). Spec dice que usa Temporal para pipeline asincrono.
**Motores que dependen de este**: Motor 9 (Audit Prep incluye informe pentest), Motor 23 (Retainer ejecuta pentest periodico modo ligero)
**Usa LLM/AI**: Si — Opus interpreta resultados y redacta informe. Ejecucion tecnica es determinista.
**Categoria**: operacion / critico
**Complejidad declarada**: critico (spec dice "una de las piezas mas diferenciadoras", 3 semanas dedicadas en plan)
**Estado actual en repo**: STUB (solo __init__.py, tablas DB: pentest_runs, pentest_findings, vulnerabilities)

---

## Motor 9 — Audit Preparation Engine

**Seccion spec**: 5.1 (linea 2707)
**Descripcion**: Genera dossier final automaticamente. Verifica entregables E-XXX presentes y aprobados, evidencias vigentes, registros de operacion cubren 6 meses, genera tareas urgentes si falta algo. Monta ZIP con estructura exacta, genera matriz cruzada del 99 (Excel), genera PDF maestro navegable.
**Entregables**: Dossier final de auditoria (ZIP), E-500 (matriz cruzada del 99)
**Dependencias declaradas**: Necesita TODO lo anterior: Motor 1 (categorizacion), Motor 3 (DdA), Motor 5 (obligaciones completadas), Motor 6 (entregables aprobados), Motor 7 (evidencias vigentes), Motor 8 (informe pentest)
**Motores que dependen de este**: Motor 10 (Audit Sim verifica dossier), Motor 23 (Retainer coordina re-certificacion)
**Usa LLM/AI**: No — determinista (verificacion de completitud)
**Categoria**: operacion
**Complejidad declarada**: medio (8 pasos definidos)
**Estado actual en repo**: STUB (solo __init__.py, tablas DB: audit_sessions)

---

## Motor 10 — Audit Simulation Engine

**Seccion spec**: 5.1 (linea 2720)
**Descripcion**: Agente IA que se hace pasar por auditor ENAC. Para cada medida aplicable: pregunta tipo auditor, busca evidencia, evalua suficiencia/vigencia/coherencia, detecta contradicciones, genera informe de auditoria interna. Coaching del personal del cliente via magic link.
**Entregables**: Informe de auditoria interna (formato ENAC), preguntas de coaching por rol
**Dependencias declaradas**: Motor 7 (evidence), Motor 3 (DdA), Motor 9 (dossier)
**Motores que dependen de este**: ninguno explicito (es el ultimo paso del pipeline ENS)
**Usa LLM/AI**: Si — agente IA principal (auditor virtual)
**Categoria**: operacion
**Complejidad declarada**: complejo (LLM intensivo)
**Estado actual en repo**: STUB (solo __init__.py, tablas DB: audit_findings)

---

## Motor 11 — Copiloto LLM Conversacional ENS

**Seccion spec**: 5.1 (linea 2733)
**Descripcion**: "El motor que mas usa Marcos dia a dia". Chat conversacional con Claude (Sonnet 4.5 default, Opus 4 para preguntas complejas) groundeado en: corpus normativo ENS completo, contexto del cliente activo, estado actual del proyecto. Anti-alucinacion: RAG obligatorio, citas obligatorias, modo "no encontrado en corpus", validacion cruzada con motores deterministas, temperatura baja (0.1-0.2).
**Entregables**: no genera entregables formales, es herramienta de asistencia diaria
**Dependencias declaradas**: Corpus ENS (semanas 3-5), datos de todos los motores (lee estado del proyecto). Spec dice: "validacion cruzada con los motores deterministas"
**Motores que dependen de este**: Spec dice Motor 24 (IDMS) integra "chat con el repositorio" via Motor 11
**Usa LLM/AI**: Si — es LLM puro (Claude Sonnet/Opus con RAG)
**Categoria**: transversal
**Complejidad declarada**: complejo (RAG + multi-modelo + anti-alucinacion)
**Estado actual en repo**: STUB (solo __init__.py, tablas DB: knowledge_documents, knowledge_chunks)

---

## Motor 12 — Magic Link Engine

**Seccion spec**: 5.1 (linea 2756)
**Descripcion**: Sistema de tokens efimeros firmados criptograficamente (JWT Ed25519 + OTP). 9 tipos de magic link definidos: onboarding_inicial, firma_documento, aporte_evidencia, aprobacion_acta, respuesta_requerimiento_auditor, autorizacion_pentest, autorizacion_accion_tecnica_remota, aprobacion_obligacion, descarga_dossier_final. TTL 24h-7d, revocable, rate limiting, geo-bloqueo opcional, audit trail inmutable.
**Entregables**: no genera entregables, es infraestructura transversal
**Dependencias declaradas**: ninguna (foundation)
**Motores que dependen de este**: Motor 5 (ejecucion de obligaciones), Motor 7 (recoleccion evidencias), Motor 8 (autorizacion pentest), Motor 13 (firma propuestas), Motor 14 (firma contratos), Motor 16 (onboarding), Motor 20 (workspace), Motor 23 (retainer)
**Usa LLM/AI**: No — criptografia pura
**Categoria**: foundation / transversal
**Complejidad declarada**: medio (criptografia + 9 tipos de link)
**Estado actual en repo**: STUB (solo __init__.py, tabla DB: magic_links)

---

## Motor 13 — Commercial Document Factory

**Seccion spec**: 5.1 (linea 2792)
**Descripcion**: Nuevo en v2.0. Generacion automatica de documentos comerciales. Extiende Motor 6. Plantillas: P-001 (propuesta 10-20 pag), P-002 (resumen ejecutivo), C-001 a C-005 (contratos y NDAs). Flujo: Agente 19 + Agente 20 toman datos de exploratory_meeting, rellenan plantilla docxtpl, generan diagramas Gantt con Mermaid, compilan PDF con LibreOffice. Anti-alucinacion: importes del pricing_model, clausulas de biblioteca validada, estimaciones del effort_estimator (Motor 17).
**Entregables**: P-001, P-002, C-001 a C-005
**Dependencias declaradas**: Motor 6 (Document Factory base), Motor 17 (effort_estimator para estimaciones)
**Motores que dependen de este**: Motor 14 (Contracts toma contratos generados por Motor 13)
**Usa LLM/AI**: Si — Agentes 19, 20 personalizan. Importes y clausulas son deterministas.
**Categoria**: comercial
**Complejidad declarada**: medio
**Estado actual en repo**: STUB (solo __init__.py)

---

## Motor 14 — Contracts Engine

**Seccion spec**: 5.1 (linea 2814)
**Descripcion**: Nuevo en v2.0. Ciclo de vida completo de contratos. Generacion desde Motor 13, envio via magic link con firma electronica avanzada eIDAS, archivo en Evidence Vault, tracking vencimientos, change requests, adendas, tracker cumplimiento cliente (client_commitments), facturas de paron por incumplimiento (coord. Motor 15). Agente 6 analiza contratos de proveedores del cliente.
**Entregables**: Contratos firmados, adendas, tracker de cumplimiento
**Dependencias declaradas**: Motor 13 (genera contratos), Motor 12 (magic links para firma), Motor 15 (facturacion de parones)
**Motores que dependen de este**: Motor 25 (Lifecycle verifica facturacion cerrada antes de archivar)
**Usa LLM/AI**: Si — Agente 6 (Analista de Contratos) analiza contratos de proveedores
**Categoria**: comercial
**Complejidad declarada**: medio
**Estado actual en repo**: STUB (solo __init__.py, tablas DB: contracts, vendor_contracts)

---

## Motor 15 — Billing Engine

**Seccion spec**: 5.1 (linea 2832)
**Descripcion**: Nuevo en v2.0. Facturacion fiscal espanola: numero correlativo, IVA 21%, retencion IRPF 15%, facturacion recurrente retainer, por hitos, parones por incumplimiento. Integracion Verifactu/TicketBAI/SII (requisito legal 2026). Recordatorios impago (dia 15, 30, 45, 60). Dashboard tesoreria. Exportacion contable (Holded/Contasimple/Quipu).
**Entregables**: Facturas PDF firmadas
**Dependencias declaradas**: Motor 14 (contratos definen importes), pricing_model
**Motores que dependen de este**: Motor 25 (Lifecycle verifica facturas cobradas antes de archivar), Motor 23 (Retainer facturacion recurrente)
**Usa LLM/AI**: No — determinista (fiscal puro)
**Categoria**: comercial
**Complejidad declarada**: complejo (normativa fiscal espanola, Verifactu)
**Estado actual en repo**: STUB (solo __init__.py, tabla DB: invoices)

---

## Motor 16 — Adaptive Onboarding Engine

**Seccion spec**: 5.1 (linea 2851)
**Descripcion**: Nuevo en v2.0. Onboardings personalizados por sector (10) y rol (7) = 70 combinaciones. 15-40 preguntas cada uno con bloques opcionales desbloqueables. Conectores OAuth: M365/Entra ID, Google Workspace, AWS, Azure, GCP, GitHub/GitLab, Okta, etc. Servidor MCP local para queries agregadas. Magic links individuales por interlocutor.
**Entregables**: Cuestionario de onboarding completado, datos de discovery OAuth
**Dependencias declaradas**: Motor 12 (magic links para onboarding)
**Motores que dependen de este**: Motor 21 (Diagnosis usa datos onboarding), Motor 22 (Discovery usa conectores OAuth)
**Usa LLM/AI**: Si parcial — preguntas adaptativas pueden usar LLM
**Categoria**: operacion
**Complejidad declarada**: complejo (70 plantillas, conectores OAuth)
**Estado actual en repo**: STUB (solo __init__.py, tabla DB: onboarding_sessions)

---

## Motor 17 — Project Planning Engine

**Seccion spec**: 5.1 (linea 2882)
**Descripcion**: Nuevo en v2.0. WBS determinista por categoria (B ~150, M ~250, A ~350 tareas). Cronograma Gantt con ruta critica. Estimador determinista de esfuerzo (effort_estimator) calibrado por tipo tarea x categoria x tamano cliente x complejidad. Seguimiento avance, deteccion retrasos, replan automatico, change management.
**Entregables**: Plan de proyecto (WBS + Gantt), exportable MS Project XML / CSV / PDF
**Dependencias declaradas**: Motor 19 (Risk Mgmt alimenta replanning). Spec dice coord con Motor 14 (cambios de alcance).
**Motores que dependen de este**: Motor 13 (usa effort_estimator para estimaciones en propuestas)
**Usa LLM/AI**: No — determinista
**Categoria**: operacion
**Complejidad declarada**: medio
**Estado actual en repo**: STUB (solo __init__.py, tablas DB: project_plans, wbs_tasks)

---

## Motor 18 — Communication & Reporting Engine

**Seccion spec**: 5.1 (linea 2899)
**Descripcion**: Nuevo en v2.0. Reportes automatizados: status semanal (1 pag), mensual (3-5 pag), trimestral (1 pag semaforo RAG), cumplimiento recursos cliente, quick wins. Canales: email, feed magic link, chat asincrono (Motor 20), SMS alertas criticas. Plantillas uniformes comms_templates.
**Entregables**: Status reports automatizados (DOCX/PDF)
**Dependencias declaradas**: Motor 20 (chat asincrono), Motor 12 (magic links para feed)
**Motores que dependen de este**: ninguno explicito
**Usa LLM/AI**: Si parcial — generacion de resumenes
**Categoria**: operacion
**Complejidad declarada**: medio
**Estado actual en repo**: STUB (solo __init__.py, tablas DB: status_reports, videocall_sessions)

---

## Motor 19 — Project Risk Management Engine

**Seccion spec**: 5.1 (linea 2920)
**Descripcion**: Nuevo en v2.0. Gestion riesgos del PROYECTO consultor (diferente del AR MAGERIT del sistema del cliente). Catalogo precargado ~30 riesgos tipicos. Instanciacion automatica al iniciar proyecto. Dashboard de riesgos con semaforo. Disparo automatico de planes de contingencia cuando trigger se activa.
**Entregables**: Plan de riesgos del proyecto, dashboard semaforo
**Dependencias declaradas**: Agente 21 (Detector de Discrepancias) contextualiza riesgos
**Motores que dependen de este**: Motor 17 (replan cuando riesgo se materializa)
**Usa LLM/AI**: Si parcial — Agente 21 contextualiza
**Categoria**: operacion
**Complejidad declarada**: medio
**Estado actual en repo**: STUB (solo __init__.py, tablas DB: project_risks, risk_treatments)

---

## Motor 20 — Collaborative Workspace Engine

**Seccion spec**: 5.1 (linea 2941)
**Descripcion**: Nuevo en v2.0. Entorno colaborativo efimero por proyecto. 4 componentes: A) Gestor documental minimalista (subcarpetas por fase, versionado, firma hash, busqueda full-text), B) Videollamadas bajo demanda con LiveKit self-hosted, C) Feed de notificaciones del proyecto, D) Chat asincrono. Ciclo de vida: creado al firmar contrato, 90 dias retencion post-cierre, destruido o archivado.
**Entregables**: no genera entregables formales, es infraestructura
**Dependencias declaradas**: Motor 12 (magic links para acceso), Motor 14 (contrato activa workspace)
**Motores que dependen de este**: Motor 18 (usa chat asincrono), Motor 24 (IDMS subsume parte del gestor documental)
**Usa LLM/AI**: No
**Categoria**: transversal
**Complejidad declarada**: medio (LiveKit es complejo pero no ENS-critico)
**Estado actual en repo**: STUB (solo __init__.py, tablas DB: client_workspaces, workspace_files, collaborative_workspaces)

---

## Motor 21 — Organizational Diagnosis Engine

**Seccion spec**: 5.1 (linea 2976)
**Descripcion**: Nuevo en v2.0. Ejecuta 4 sub-diagnosticos organizativos de Fase 1: mapa de stakeholders (grafo Apache AGE), inventario procesos de negocio (BPMN Mermaid), inventario obligaciones legales cruzadas (RGPD, NIS2, DORA, AI Act), inventario proyectos en curso del cliente.
**Entregables**: E-090 (Informe de Diagnostico Inicial, 30-80 paginas)
**Dependencias declaradas**: Datos del onboarding (Motor 16), Agentes 22/23/24
**Motores que dependen de este**: Motor 2 (MAGERIT usa inventario activos), Motor 4 (Gap usa diagnostico)
**Usa LLM/AI**: Si — agentes 22/23/24 son LLM
**Categoria**: diagnostico
**Complejidad declarada**: complejo (4 sub-diagnosticos, Apache AGE)
**Estado actual en repo**: STUB (solo __init__.py)

---

## Motor 22 — Technical Discovery Engine

**Seccion spec**: 5.1 (linea 2988)
**Descripcion**: Nuevo en v2.0. "La otra gran innovacion". 8 sub-motores: Asset Discovery (Nmap, conectores cloud), Identity Discovery (AD/Entra ID), Data Discovery (patrones regex), Configuration Discovery (CLARA, Lynis, CIS-CAT), Vulnerability Discovery (OpenVAS, Nuclei, Trivy, Semgrep), Log & Monitoring Assessment, Data Flow Mapping (Agente 25), Continuity Assessment. Outputs al project knowledge graph.
**Entregables**: Inventario completo (activos, identidades, configuraciones, vulnerabilidades)
**Dependencias declaradas**: Motor 16 (datos onboarding + conectores OAuth)
**Motores que dependen de este**: Motor 1 (categorizacion usa inventario), Motor 2 (MAGERIT usa activos), Motor 4 (Gap), Motor 5 (Obligations)
**Usa LLM/AI**: Si parcial — Agente 25 genera DFD, pero herramientas son deterministas
**Categoria**: diagnostico / critico
**Complejidad declarada**: critico (11+ herramientas, 8 sub-motores, 2 semanas dedicadas)
**Estado actual en repo**: STUB (solo __init__.py, tablas DB: discovered_assets, discovered_identities)

---

## Motor 23 — Retainer Management Engine

**Seccion spec**: 5.1 (linea 3008)
**Descripcion**: Nuevo en v2.0. Mantenimiento post-certificacion de 20-40 clientes simultaneos. Calendarizacion automatica actividades anuales obligatorias, periodicidad comites, simulacros phishing, pruebas continuidad, vigilancia normativa (Agente 15), vigilancia vulnerabilidades (Motor 8 modo ligero), onboarding proveedores, gestion cambios significativos, reporting trimestral, coordinacion auditorias seguimiento, facturacion recurrente (Motor 15).
**Entregables**: Dashboard multi-cliente con semaforo RAG
**Dependencias declaradas**: Motor 8 (pentest periodico), Motor 15 (facturacion), Motor 10 (auditoria interna), todos los motores de contenido para mantener estado actualizado
**Motores que dependen de este**: ninguno (es el motor de fase final post-certificacion)
**Usa LLM/AI**: Si parcial — Agente 15 para vigilancia normativa
**Categoria**: operacion / post-certificacion
**Complejidad declarada**: complejo (multi-cliente, 12+ funcionalidades)
**Estado actual en repo**: STUB (solo __init__.py, tablas DB: retainer_contracts, retainer_activities)

---

## Motor 24 — Intelligent Document Management Engine (IDMS)

**Seccion spec**: 5.1 (linea 3034)
**Descripcion**: Nuevo en v2.1 (revision abril 2026). Gestor documental inteligente de primera clase, comparable a SharePoint/Drive pero especializado en ENS con LLM integrado. Vista de arbol por cliente, drag & drop inteligente, busqueda hibrida lexico-semantica (tsvector + pgvector + embeddings multilingual-e5-large), etiquetado automatico por medida ENS (Agente 27), preview embebido (PDF.js), historial versiones con diffs, chat con repositorio (via Motor 11). Microservicio doc-extractor multi-formato con cola Celery.
**Entregables**: no genera entregables, es infraestructura documental
**Dependencias declaradas**: Spec seccion 9.13 dice literal: "Depende de Motor 6, Motor 7, Motor 11, Motor 20"
**Motores que dependen de este**: Spec seccion 9.13 dice literal: "Lo usa Motor 9 (Audit Prep), Motor 10 (Audit Sim), Motor 25"
**Usa LLM/AI**: Si — Agente 27 clasificacion automatica, embeddings, chat con repositorio
**Categoria**: transversal
**Complejidad declarada**: critico (spec le dedica seccion 9.13 con plan de 7 semanas: semanas 14-20)
**Estado actual en repo**: STUB (solo __init__.py)

---

## Motor 25 — Project Lifecycle & Archival Engine

**Seccion spec**: 5.1 (linea 3218)
**Descripcion**: Nuevo en v2.1. Ciclo de vida completo del proyecto: DRAFT->NEGOTIATING->SIGNED->ACTIVE->CERTIFIED->RETAINER->ENDED->ARCHIVED->PURGED. Wizard de archivado 5 pasos (verificacion, generacion ZIP, firma Ed25519, migracion frio, purga BD). Export puntual sin archivar. Restauracion desde frio. Filtros de estado en sidebar.
**Entregables**: ZIP firmado de archivado, certificado de archivado
**Dependencias declaradas**: Spec seccion 9.13 dice literal: "Depende de Motor 14, Motor 15, Motor 24, Motor 26"
**Motores que dependen de este**: Sidebar multi-cliente, dashboard Operaciones
**Usa LLM/AI**: No — determinista
**Categoria**: operacion / transversal
**Complejidad declarada**: medio (5 pasos de wizard + maquina de estados)
**Estado actual en repo**: STUB (solo __init__.py, tabla DB: project_lifecycle_states, archived_projects)

---

## Motor 26 — Backup & Disaster Recovery Engine

**Seccion spec**: 5.1 (linea 3305)
**Descripcion**: Nuevo en v2.1. Consolida estrategia de backups de la plataforma. 4 tipos: A) Backup continuo PostgreSQL (pgBackRest, WAL, PITR), B) Backup MinIO (mc mirror + rclone snapshot), C) Backup config/secretos (Terraform, Ansible, Vault), D) Backup logs inmutables (hash chain, WORM). Pruebas periodicas restauracion: semanal parcial, mensual completo, trimestral DR drill (RTO 4h, RPO 1h). Panel en dashboard Operaciones.
**Entregables**: Panel estado backups, registro pruebas restauracion
**Dependencias declaradas**: Spec seccion 9.13 dice literal: "Depende de Ninguno — construccion base"
**Motores que dependen de este**: Spec seccion 9.13 dice literal: "Toda la plataforma desde el dia 1". Motor 25 depende de Motor 26.
**Usa LLM/AI**: No — operaciones puras
**Categoria**: foundation / operacion
**Complejidad declarada**: medio-alto (pgBackRest, DR drills, integridad)
**Estado actual en repo**: PARCIAL-DESACTIVADO (584 lineas codigo, 6 endpoints, 0 tests, router desactivado en Bloque 11, ver TODO-M26-CIERRE)

---

## TABLA RESUMEN DE DEPENDENCIAS DECLARADAS EN SPEC

(Solo dependencias EXPLICITAS encontradas en el texto del spec)

| Motor | Depende de (input) | Es input de |
|---|---|---|
| M1 Categorization | ninguno | M3, M5, M22 |
| M2 MAGERIT | ninguno | M4, M5, M19 |
| M3 DdA | M1 | M4, M5, M9 |
| M4 Gap | M3 | M5 |
| M5 Obligations | M4, M6, M12 | M7, M9 |
| M6 Document Factory | corpus ENS | M5, M7, M9, M13, M24 |
| M7 Evidence | M5, M6, M12 | M9, M10, M24 |
| M8 Pentesting | M12, M22 | M9, M23 |
| M9 Audit Prep | M1, M3, M5, M6, M7, M8 | M10, M23 |
| M10 Audit Sim | M3, M7, M9 | ninguno explicito |
| M11 Copiloto | corpus ENS, todos (lee) | M24 |
| M12 Magic Link | ninguno | M5, M7, M8, M13, M14, M16, M18, M20, M23 |
| M13 Commercial Doc | M6, M17 | M14 |
| M14 Contracts | M12, M13, M15 | M25 |
| M15 Billing | M14 | M23, M25 |
| M16 Onboarding | M12 | M21, M22 |
| M17 Planning | M19 | M13 |
| M18 Communication | M12, M20 | ninguno |
| M19 Risk Mgmt | ninguno | M17 |
| M20 Workspace | M12, M14 | M18, M24 |
| M21 Diagnosis | M16 | M2, M4 |
| M22 Discovery | M16 | M1, M2, M4, M5, M8 |
| M23 Retainer | M8, M10, M15 | ninguno |
| M24 IDMS | M6, M7, M11, M20 | M9, M10, M25 |
| M25 Lifecycle | M14, M15, M24, M26 | ninguno |
| M26 Backup | ninguno | M25, toda la plataforma |

## PLAN DE SEMANAS DEL SPEC (orden propuesto en spec v2.1)

| Semanas | Motores | Nota |
|---|---|---|
| 1-2 | Fundamentos (no motores) | Stack base, auth, modelo datos |
| 3-5 | Corpus ENS + RAG | Ingesta normativa, no motores |
| 4-6 | M26 Backup (en paralelo) | Spec 9.13: "se construye lo primero" |
| 6-7 | M16 Onboarding + M20 Workspace | |
| 8-9 | M13 Commercial + M14 Contracts + M15 Billing | |
| 8-10 | Tenant virtual reforzado (en paralelo) | |
| 10-11 | M17 Planning + M18 Communication + M19 Risk | |
| 12-13 | M1 Categorization + M3 DdA + M6 Doc Factory | |
| 14-15 | M22 Technical Discovery | |
| 14-20 | M24 IDMS (en paralelo, 7 semanas) | Spec 9.13 |
| 16-17 | M21 Diagnosis | |
| 18-19 | M2 MAGERIT + M4 Gap + M5 Obligations | |
| 20-21 | M12 Magic Link + Evidence Vault (M7) | |
| 22-24 | M8 Pentesting & Red Team | |
| 25-26 | Resto plantillas documentales | |
| 27-28 | M9 Audit Prep + M10 Audit Sim | |
| 28-30 | M25 Lifecycle (en paralelo) | Spec 9.13 |
| 29-30 | M11 Copiloto + Agentes comerciales | |
| 31-32 | M14 avanzado + M15 fiscal completo | |
| 33-34 | M23 Retainer + Multi-cliente | |
| 35-36 | Vigilancia normativa + LUCIA/PILAR/INES | |
| 37-38 | Dogfooding ENS Medio | |
| 39-40 | Pulido + Primer cliente real | |
