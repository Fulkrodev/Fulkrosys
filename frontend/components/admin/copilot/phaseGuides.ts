/**
 * Phase guides catalog · centralized R30 admin tutor content (DRY OPS-026).
 *
 * Sesión 3B-2B.4 Phase 1.3 · CopilotGuidedFlow expansion to core admin pages.
 *
 * Cada entrada wrap-able directly desde page.tsx via:
 *   <CopilotGuidedFlow {...PHASE_GUIDES.dimensiones(projectId)} />
 *
 * Marcos super-vision step-by-step "como si fuera tonto · primer principios"
 * ENS workflow Fase 0→Fase 8.
 */
import type { CopilotGuidedFlowProps } from "./CopilotGuidedFlow";

type GuideBuilder = (projectId: string) => Omit<CopilotGuidedFlowProps, "className">;

export const PHASE_GUIDES = {
  dimensiones: (projectId: string) => ({
    phaseId: "categorizacion-dimensiones",
    title: "Categorización del sistema ENS · 19 dimensiones",
    intro:
      "Captura las 19 dimensiones de adaptación que drive el resto del workflow. Pre-rellenadas desde reunión exploratoria (m13 comercial) y onboarding cliente (m16) · revisas, completas faltantes y firmas E-012 acta de categorización.",
    whyImportant:
      "La categoría (BÁSICA · MEDIA · ALTA) determina qué medidas Anexo II aplican y si el cliente necesita audit ENAC externo. Categorizar mal cuesta tiempo y dinero: BÁSICA insuficiente para AAPP que exige MEDIA bloquea contrato.",
    steps: [
      { label: "Revisa dimensiones pre-rellenadas", detail: "Top-down desde reunión + onboarding · NO partes de cero" },
      { label: "Completa dimensiones faltantes con cliente", detail: "Tooltip ENS explica cada concepto plain Spanish" },
      { label: "Sistema calcula categoría sugerida", detail: "BÁSICA/MEDIA/ALTA · trace dimensions → category visible" },
      { label: "Firma E-012 acta de categorización", detail: "Acta firmada habilita siguiente fase MAGERIT" },
    ],
    commonMistakes: [
      "Aceptar categoría sugerida sin contrastar con pliego AAPP (puede exigir mayor)",
      "Saltarse cumplimentación 19 dims pensando 'arreglo después': el plan de adecuación bloquea sin ellas",
    ],
    estimatedTime: "Sesión cliente 1-2h · firma admin 15 min",
    helpTopics: [
      { label: "RD 311/2022 art. 6 (categorización)", href: "https://www.boe.es/buscar/act.php?id=BOE-A-2022-7191&p=20220504&tn=2#a6", external: true },
      { label: "Preguntar al copiloto", href: "#copilot-dock" },
    ],
    nextAction: {
      label: "Iniciar MAGERIT",
      targetUrl: `/admin/projects/${projectId}/magerit`,
    },
  }),

  magerit: (projectId: string) => ({
    phaseId: "magerit-analysis",
    title: "Análisis de riesgos MAGERIT v3",
    intro:
      "Catálogo amenazas + activos + salvaguardas mapeadas Anexo II ENS. Inventario activos automático desde dimensiones · catálogo amenazas estándar MAGERIT v3 · valoración impacto + probabilidad por dim CIDA.",
    whyImportant:
      "El plan de adecuación trace cada medida Anexo II a un riesgo MAGERIT mitigado. Sin MAGERIT, la DdA queda 'huérfana' y la auditoría ENAC encuentra trazabilidad rota → no-conformidad mayor.",
    steps: [
      { label: "Revisa inventario activos auto-importado", detail: "Desde dimensiones del proyecto · ajusta si falta algo crítico" },
      { label: "Aplica catálogo amenazas MAGERIT v3", detail: "[N]aturales · [I]ndustriales · [E]rrores · [A]taques" },
      { label: "Valora impacto + probabilidad por activo", detail: "Dimensiones CIDA (Confidencialidad · Integridad · Disponibilidad · Autenticidad)" },
      { label: "Salvaguardas mapeadas Anexo II", detail: "Catálogo medidas mp.* op.* org.* · automático desde catálogo CCN" },
    ],
    commonMistakes: [
      "Valorar todo 'crítico' por miedo: hace inviable el plan presupuestario",
      "Saltarse mapping salvaguardas → Anexo II: la DdA queda sin justificación trazable",
    ],
    estimatedTime: "8-16h trabajo distribuido 1-2 semanas",
    helpTopics: [
      { label: "MAGERIT v3 Libro II (catálogos)", href: "https://administracionelectronica.gob.es/pae_Home/pae_Documentacion/pae_Metodolog/pae_Magerit.html", external: true },
      { label: "Preguntar al copiloto", href: "#copilot-dock" },
    ],
    nextAction: {
      label: "Generar DdA",
      targetUrl: `/admin/projects/${projectId}/dda`,
    },
  }),

  dda: (projectId: string) => ({
    phaseId: "dda-applicability",
    title: "Declaración de Aplicabilidad (DdA) · 73 medidas Anexo II",
    intro:
      "Documento firmado por el cliente que justifica cuáles de las 73 medidas Anexo II ENS aplican (y cuáles no). Generación automática desde categoría + MAGERIT · validación cliente + firma Ed25519 EC P-256.",
    whyImportant:
      "Es la pieza central de la auditoría ENAC: el auditor compara DdA vs implantación real + evidencias. Una medida 'aplicable' sin evidencia = no-conformidad. Una medida 'no aplicable' sin justificación trazada = no-conformidad mayor.",
    steps: [
      { label: "Sistema genera DdA borrador", detail: "Filtrado por categoría + Anexo II catálogo CCN · solo medidas que aplican" },
      { label: "Justifica medidas 'no aplicables'", detail: "Cada exclusión requiere razón trazable (Anexo II permite excepciones limitadas)" },
      { label: "Cliente firma Ed25519 magic-link", detail: "Sin cuenta permanente · audit log inmutable" },
      { label: "DdA firmada bloquea cambios", detail: "Modificaciones posteriores generan revisión + re-firma" },
    ],
    commonMistakes: [
      "Excluir medidas 'porque no las entendemos': justifica con criterio técnico o pide al copiloto",
      "Generar DdA antes de MAGERIT: medidas quedan sin riesgo trazado",
    ],
    estimatedTime: "Admin 30 min · cliente revisa+firma 1-2h",
    helpTopics: [
      { label: "Catálogo 73 medidas Anexo II", href: `/admin/projects/${projectId}/dda#catalogo`, external: false },
      { label: "Preguntar al copiloto", href: "#copilot-dock" },
    ],
    nextAction: {
      label: "Ir a Plan de adecuación",
      targetUrl: `/admin/projects/${projectId}/plan`,
    },
  }),

  risks: (projectId: string) => ({
    phaseId: "risks-register",
    title: "Registro de riesgos del proyecto",
    intro:
      "Vista consolidada de riesgos identificados en MAGERIT + riesgos cliente-específicos detectados durante implantación. Cada riesgo trace a salvaguarda Anexo II + estado mitigación.",
    whyImportant:
      "ENAC verifica gestión continua de riesgos (no solo MAGERIT inicial). Riesgos abiertos sin plan de acción = no-conformidad menor · riesgos críticos abiertos pre-cert = bloqueo certificación.",
    steps: [
      { label: "Revisa riesgos heredados MAGERIT", detail: "Auto-importados · valoración impacto + probabilidad" },
      { label: "Añade riesgos detectados post-MAGERIT", detail: "Implantación + auditoría dry-run + retainer pueden generar riesgos nuevos" },
      { label: "Asigna salvaguarda + responsable + fecha", detail: "Cada riesgo abierto necesita plan acción concreto" },
      { label: "Cierre formal con evidencia", detail: "Riesgo cerrado documentado en evidence vault" },
    ],
    commonMistakes: [
      "Dejar riesgos 'abiertos sin propietario': nadie los cierra → bloqueo auditoría",
      "Cerrar riesgos sin evidencia: ENAC pide trazabilidad del cierre",
    ],
    estimatedTime: "Revisión semanal 30 min · acción trimestral 2-4h",
    helpTopics: [
      { label: "MAGERIT del proyecto", href: `/admin/projects/${projectId}/magerit` },
      { label: "Preguntar al copiloto", href: "#copilot-dock" },
    ],
  }),

  plan: (projectId: string) => ({
    phaseId: "plan-adecuacion",
    title: "Plan de adecuación · Gantt + PDA",
    intro:
      "Cronograma de implantación de medidas Anexo II priorizadas. Gantt visual + Plan de Adecuación documental (PDA) generable PDF. Asignación responsables + fecha objetivo + dependencias entre tareas.",
    whyImportant:
      "El plan es el contrato implícito Marcos↔cliente: define qué se hace, cuándo y por quién. Sin plan firmado, la implantación deriva en alcance descontrolado y la auditoría llega sin evidencias preparadas.",
    steps: [
      { label: "Plan auto-generado desde DdA", detail: "Cada medida aplicable → tarea con responsable sugerido" },
      { label: "Ajusta fechas según calendario cliente", detail: "Realista: BÁSICA 4-6 semanas · MEDIA 8-10 · ALTA 12-16" },
      { label: "Genera PDA documental (PDF)", detail: "Documento firmable cliente · base contractual" },
      { label: "Tracking semanal vs plan", detail: "Desviaciones detectadas temprano · ajustes ágiles" },
    ],
    commonMistakes: [
      "Fechas optimistas: cliente AAPP suele tardar 2-3x en validar entregables",
      "Olvidar dependencias técnicas: medida X depende de Y completada · plan paralelo invalido",
    ],
    estimatedTime: "Diseño plan 2-4h · seguimiento semanal 30 min",
    helpTopics: [
      { label: "DdA del proyecto", href: `/admin/projects/${projectId}/dda` },
      { label: "Preguntar al copiloto", href: "#copilot-dock" },
    ],
    nextAction: {
      label: "Recopilar evidencias",
      targetUrl: `/admin/projects/${projectId}/evidence`,
    },
  }),

  evidence: (projectId: string) => ({
    phaseId: "evidence-vault",
    title: "Vault de evidencias · WORM 7 años",
    intro:
      "Repositorio inmutable de evidencias por medida Anexo II implantada. Upload con classifier AI (sugiere medida asociada) · hash SHA-256 + audit log · retención WORM 7 años post-certificación.",
    whyImportant:
      "ENAC pide 'ver y tocar' cada medida implantada. Sin evidencia → la medida no existe · auditor marca no-conformidad. WORM 7 años protege contra alegaciones de manipulación retroactiva.",
    steps: [
      { label: "Upload evidencia (PDF · screenshot · log)", detail: "Drag & drop · multi-archivo · classifier AI sugiere medida" },
      { label: "Confirma medida asociada + categoría", detail: "Marcos valida sugerencia AI antes commit" },
      { label: "Hash + timestamp inmutable", detail: "SHA-256 + audit log · trazabilidad ENAC" },
      { label: "Tagging extra (departamento · responsable)", detail: "Facilita búsqueda durante auditoría" },
    ],
    commonMistakes: [
      "Subir 'todo a la vez sin tagging': irrecuperable durante auditoría · re-trabajo",
      "Pantallazos sin contexto (fecha · sistema · usuario): el auditor pide contexto y no existe",
    ],
    estimatedTime: "Continuous · 5-15 min por evidencia uploaded",
    helpTopics: [
      { label: "Plan del proyecto", href: `/admin/projects/${projectId}/plan` },
      { label: "Preguntar al copiloto", href: "#copilot-dock" },
    ],
    nextAction: {
      label: "Audit dry-run",
      targetUrl: `/admin/projects/${projectId}/audit-dry-run`,
    },
  }),

  conformity: (projectId: string) => ({
    phaseId: "conformity-declaration",
    title: "Declaración de Conformidad ENS · E-041",
    intro:
      "Documento final que declara el sistema ENS conforme (post-implantación + audit). Wizard 5 pasos · valida pre-requisitos · genera declaración + firma Ed25519 cliente · publica registro CCN.",
    whyImportant:
      "Es el output certificable del proyecto. Sin declaración firmada, el sistema NO está en conformidad ENS aunque las medidas estén implantadas. Publicación en registro CCN visible AAPP que licitan.",
    steps: [
      { label: "Wizard valida pre-requisitos", detail: "DdA firmada · plan completado · evidencias indexed · audit dry-run pasado" },
      { label: "Genera declaración borrador", detail: "Template legal RD 311/2022 + datos cliente + scope" },
      { label: "Cliente firma Ed25519 magic-link", detail: "Sin cuenta permanente · firma legalmente vinculante" },
      { label: "Publicación registro CCN", detail: "Visible AAPP que licitan · activa retainer post-cert" },
    ],
    commonMistakes: [
      "Generar declaración antes de audit dry-run pasado: bloquea publicación",
      "Olvidar publicación CCN: cliente no aparece registro y AAPP duda autenticidad",
    ],
    estimatedTime: "Wizard 30 min · firma cliente 1h",
    helpTopics: [
      { label: "Dossier ENAC", href: `/admin/projects/${projectId}/dossier` },
      { label: "Preguntar al copiloto", href: "#copilot-dock" },
    ],
    nextAction: {
      label: "Configurar retainer",
      targetUrl: `/admin/projects/${projectId}/retainer`,
    },
  }),

  verification: (projectId: string) => ({
    phaseId: "verification-pentest",
    title: "Verificación técnica · vuln-scan (MEDIA) / pentest (ALTA)",
    intro:
      "El sistema ejecuta de forma AUTÓNOMA el escaneo de vulnerabilidades (MEDIA) o el pentest + red-team (ALTA) sobre el alcance autorizado, guiado por Opus 4.8 (determinista · anti-inyección · sin bajar severidad). Al cerrar el run genera el informe E-702/703/704 firmado.",
    whyImportant:
      "ENS MEDIA exige análisis de vulnerabilidades (mp.s.2); ALTA exige pentest + red-team (refuerzo R3 · CPSTIC). Sin esta verificación y su informe, el dossier ENAC queda incompleto y el auditor marca no-conformidad.",
    steps: [
      { label: "Autoriza el alcance (ALTA: firma autorización pentest)", detail: "Hosts/web/cloud in-scope · ALTA requiere autorización firmada antes de lanzar (fail-closed)" },
      { label: "Lanza el autopilot", detail: "MEDIA completa sola · ALTA pausa en Gate 2 para atestación del pentester acreditado" },
      { label: "Revisa findings + triage Opus 4.8", detail: "El LLM triagea como ASESOR · nunca baja severidad ni cambia el veredicto determinista" },
      { label: "Informe E-702/703/704 auto-generado", detail: "Firmado Ed25519 · cae solo en el dossier (carpeta 13)" },
    ],
    commonMistakes: [
      "Lanzar ALTA sin autorización firmada: el sistema lo bloquea (fail-closed · zero standing access)",
      "Cerrar el run sin revisar los críticos antes de proponer remediación",
    ],
    estimatedTime: "MEDIA: scan automático + revisión 1-2h · ALTA: + atestación pentester",
    helpTopics: [
      { label: "Herramientas MCP", href: `/admin/projects/${projectId}/mcps` },
      { label: "Preguntar al copiloto", href: "#copilot-dock" },
    ],
    nextAction: {
      label: "Revisar y aplicar remediaciones",
      targetUrl: `/admin/projects/${projectId}/remediation`,
    },
  }),

  mcps: (projectId: string) => ({
    phaseId: "mcps-tools",
    title: "Herramientas de verificación (MCPs)",
    intro:
      "Arsenal de herramientas de seguridad (recon · vuln-scan · web · cloud · SAST) que alimenta la verificación. Normalmente el autopilot las orquesta solo; este panel es para una ejecución puntual o un re-escaneo concreto.",
    whyImportant:
      "Las herramientas producen la evidencia técnica del pentest. El autopilot las usa automáticamente por categoría; aquí solo intervienes para casos puntuales.",
    steps: [
      { label: "Normalmente NO necesitas tocar esto", detail: "La pestaña Verificación (autopilot) ya lanza las herramientas pertinentes por categoría" },
      { label: "Lanza una herramienta puntual si hace falta", detail: "Ej. re-escanear un host concreto tras un cambio" },
      { label: "Resultados → evidencia + findings", detail: "Se adjuntan automáticamente al expediente del proyecto" },
    ],
    commonMistakes: [
      "Lanzar herramientas sin autorización de alcance vigente",
    ],
    estimatedTime: "Puntual · minutos por herramienta",
    helpTopics: [
      { label: "Verificación autónoma", href: `/admin/projects/${projectId}/verification` },
      { label: "Preguntar al copiloto", href: "#copilot-dock" },
    ],
    nextAction: {
      label: "Volver a Verificación",
      targetUrl: `/admin/projects/${projectId}/verification`,
    },
  }),

  remediation: (projectId: string) => ({
    phaseId: "remediation-adr055",
    title: "Remediación · proponer → aprobar (1 clic) → ejecutar",
    intro:
      "El sistema propone remediaciones para los hallazgos cloud (cifrado · acceso público · MFA · HTTPS…) mapeadas a medidas Anexo II. Tú o el cliente las aprobáis con un clic y el sistema las aplica en los sistemas del cliente con ciclo seguro (preflight→snapshot→aplicar→verificar→rollback). Todo queda documentado en el dossier (carpeta 14).",
    whyImportant:
      "Cerrar los hallazgos antes de la auditoría sube el nivel de conformidad y evita no-conformidades. La aprobación con un clic + el snapshot antes/después dan trazabilidad ENAC y seguridad: nada se toca sin autorización del cliente.",
    steps: [
      { label: "Genera propuestas desde los hallazgos", detail: "Botón 'Proponer remediaciones' · mapeo determinista hallazgo→acción del catálogo" },
      { label: "Revisa cada propuesta (qué hace + recurso)", detail: "SAFE_AUTO reversible · GUARDED puede afectar acceso · BLOCKED nunca automático" },
      { label: "El cliente concede permisos de escritura por conector", detail: "Activación + grant-write · sin permiso no se ejecuta nada" },
      { label: "Aprobar y ejecutar (1 clic)", detail: "Ciclo seguro con snapshot + auto-rollback si la verificación falla" },
    ],
    commonMistakes: [
      "Ejecutar sin que el cliente haya concedido permisos al conector: el job queda como plan",
      "Aprobar una GUARDED sin avisar al cliente del posible impacto en accesos",
    ],
    estimatedTime: "Revisión 15-30 min · ejecución automática por acción",
    helpTopics: [
      { label: "Verificación (origen de hallazgos)", href: `/admin/projects/${projectId}/verification` },
      { label: "Preguntar al copiloto", href: "#copilot-dock" },
    ],
    nextAction: {
      label: "Ir al Dossier ENAC",
      targetUrl: `/admin/projects/${projectId}/dossier`,
    },
  }),

  dossier: (projectId: string) => ({
    phaseId: "dossier-enac",
    title: "Dossier ENAC · entrega audit externo",
    intro:
      "Paquete documental completo para handoff auditor ENAC externo (MEDIA/ALTA). 10 documentos canonical · DdA firmada · MAGERIT · plan · evidencias por medida · políticas · registros · pentest report · etc.",
    whyImportant:
      "El auditor ENAC inicia revisión solo si el dossier está completo y trazable. Dossier incompleto = audit retrasado o suspendido · cliente paga horas auditor sin avance. Marcos prepara el dossier impecable antes del handoff.",
    steps: [
      { label: "Verifica 10 documentos completos", detail: "DeliverableAuditor automático · marca rojo lo que falta" },
      { label: "Revisa trazabilidad cruzada", detail: "Cada evidencia trace a medida · cada medida trace a riesgo MAGERIT" },
      { label: "Genera ZIP firmado", detail: "SHA-256 manifest + Ed25519 signature · auditor verifica integridad" },
      { label: "Handoff auditor ENAC", detail: "Magic-link descarga · audit log inmutable" },
    ],
    commonMistakes: [
      "Entregar dossier antes de declaración cliente: auditor rechaza handoff",
      "Olvidar evidencias políticas (RRHH · ciclo vida datos): suele faltar y bloquea revisión",
    ],
    estimatedTime: "Preparación 2-4h · validación cruzada 1-2h",
    helpTopics: [
      { label: "Declaración Conformidad", href: `/admin/projects/${projectId}/conformity` },
      { label: "Preguntar al copiloto", href: "#copilot-dock" },
    ],
  }),
} satisfies Record<string, GuideBuilder>;

export type PhaseGuideSlug = keyof typeof PHASE_GUIDES;
