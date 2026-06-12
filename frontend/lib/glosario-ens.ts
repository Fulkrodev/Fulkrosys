/**
 * GLOSARIO_ENS · diccionario term → definición/label/link.
 *
 * SAN-E v3.MB-2.2 + 2.2.bis · 134 entradas · cobertura ENS · MAGERIT · DNS ·
 * eIDAS · auth · workflow · arquetipos · sectores · roles ·
 * frameworks · documentos · pentesting · retainer · evidencias ·
 * v3 (in-portal signing · WhatsApp · capabilities).
 *
 * Tono cliente-friendly intuitivo (cleanup 2.2.bis):
 * - Sin jerga sin traducir · acrónimo + explicación misma frase
 * - Analogías concretas (candado verde · huella digital · cadena)
 * - Ejemplos cuando aporten claridad
 * - Conversacional · tuteo 2ª persona
 * - 2-3 frases máximo · mobile-friendly tooltip 360px
 * - Mismo glosario sirve cliente y admin (ambos no-expertos en áreas concretas)
 */

export type GlossaryEntry = {
  label: string;
  definition: string;
  docLink?: string;
};

export const GLOSARIO_ENS = {
  // === A.1 · DNS / Email infra (10) ===
  DNS: { label: "DNS", definition: "Sistema que convierte 'fulkro.es' en una dirección IP que el ordenador entiende. Como una agenda telefónica de internet · cuando escribes una web · DNS busca a qué servidor llamar." },
  postmark: { label: "Postmark", definition: "Servicio que envía los emails de FULKRO al cliente (notificaciones · facturas · reuniones). Más fiable que Gmail en envíos masivos · raramente cae en spam.", docLink: "https://postmarkapp.com/support/article/1054-add-a-domain" },
  DKIM: { label: "DKIM", definition: "Firma matemática automática en tus emails. Cuando llegan a Gmail/Outlook · ellos la verifican · si coincide saben que es tuyo · si no · va a spam." },
  SPF: { label: "SPF", definition: "Lista pública de qué servidores tienen permiso para enviar email desde tu dominio. Sin SPF · cualquiera puede falsificar tu email y los buzones modernos lo bloquean." },
  DMARC: { label: "DMARC", definition: "Política que combina SPF y DKIM. Le dice a Gmail/Outlook qué hacer si un email parece falsificado: spam · rechazo · o pasar (no recomendado)." },
  MX_record: { label: "Registro MX", definition: "Apunta a qué servidor recibe los emails de tu dominio. Solo lo necesitas si recibes correos en @tudominio.es. Si solo envías · no hace falta." },
  A_record: { label: "Registro A", definition: "Apunta tu dominio (ej: app.fulkro.es) a una IP concreta del servidor. Es el primer registro DNS que configuras al lanzar una web." },
  CNAME_record: { label: "Registro CNAME", definition: "Apunta un dominio a OTRO dominio (alias). Útil para 'www' que apunte a la raíz · o para subdominios que cambian de IP." },
  TLS: { label: "TLS / HTTPS", definition: "El candado verde arriba del navegador. Significa que la comunicación está cifrada · si alguien intercepta · solo ve basura. Imprescindible en producción." },
  IP_address: { label: "Dirección IP", definition: "Identificador numérico único del servidor en internet (ej: 91.107.x.x). Las IPs son lo que apuntas en el DNS para que tu dominio funcione." },

  // === A.2 · ENS normativo (15) ===
  ENS: { label: "ENS", definition: "Esquema Nacional de Seguridad · las reglas obligatorias de ciberseguridad para cualquier empresa que trabaje con la Administración Pública española. Sin certificado ENS · no puedes presentarte a contratos públicos.", docLink: "https://www.boe.es/buscar/act.php?id=BOE-A-2022-7191" },
  RD_311_2022: { label: "RD 311/2022", definition: "El Real Decreto que regula el ENS desde 2022 · sustituye al RD 3/2010. Define las 73 medidas de seguridad obligatorias.", docLink: "https://www.boe.es/buscar/act.php?id=BOE-A-2022-7191" },
  Anexo_I: { label: "Anexo I", definition: "Sección del ENS que clasifica tu sistema en BÁSICA · MEDIA o ALTA según 5 dimensiones (las DICAT). Más alto = más medidas obligatorias = más coste." },
  Anexo_II: { label: "Anexo II", definition: "Las 73 medidas concretas de seguridad del ENS. Se dividen en organizacionales (4) · operacionales (33) · y técnicas (36). Cuáles te aplican depende de tu categoría." },
  Anexo_III: { label: "Anexo III", definition: "Cómo se audita el ENS. En MEDIA/ALTA hace falta un auditor ENAC externo cada 2 años · en BÁSICA puedes autoevaluarte siguiendo CCN-STIC 809." },
  categoria_basica: { label: "Categoría BÁSICA", definition: "Sistemas con bajo impacto si fallan (ej: web informativa). ~33 días de adecuación · 6500-14000€ aprox · te autoevalúas sin auditor externo." },
  categoria_media: { label: "Categoría MEDIA", definition: "Sistemas con impacto significativo (ej: portal con datos personales). ~60 días · 22000-55000€ · auditor ENAC externo cada 2 años." },
  categoria_alta: { label: "Categoría ALTA", definition: "Sistemas críticos para España (sanidad · energía · defensa · grandes AAPP). ~99 días · 48000-140000€ · auditor ENAC obligatorio + medidas reforzadas." },
  DICAT: { label: "DICAT", definition: "Las 5 cosas que el ENS mide en tu sistema: D=funciona cuando lo necesitas · I=los datos no cambian sin permiso · C=solo lo ven quien debe · A=sabes quién hizo qué · T=queda registro de todo." },
  ENAC: { label: "ENAC", definition: "El 'examinador oficial' de España (Entidad Nacional de Acreditación). Solo los auditores certificados por ENAC pueden firmar tu conformidad ENS · si firma uno no-ENAC · no vale.", docLink: "https://www.enac.es/" },
  CCN_CERT: { label: "CCN-CERT", definition: "Centro Criptológico Nacional · el organismo público que publica las guías técnicas (CCN-STIC) que orientan cómo cumplir el ENS en la práctica.", docLink: "https://www.ccn-cert.cni.es/" },
  CCN_STIC_809: { label: "CCN-STIC 809", definition: "Guía oficial para autoevaluar tu ENS BÁSICA · sin auditor externo. Tu RSEG firma · es legal en BÁSICA · NO vale en MEDIA/ALTA." },
  CCN_STIC_804: { label: "CCN-STIC 804", definition: "Guía oficial que detalla CADA una de las 73 medidas ENS · cómo implementarla y qué evidencia aportar. Tu manual de referencia técnica." },
  CCN_STIC_808: { label: "CCN-STIC 808", definition: "Guía oficial que define exactamente qué evalúa el auditor ENAC en tu auditoría. Si pasas estos checks · pasas la auditoría." },
  CCN_STIC_805: { label: "CCN-STIC 805", definition: "Guía oficial sobre cómo gestionar logs y trazabilidad para cumplir ENS. Sin logs correctos · suspendes auditoría." },

  // === A.3 · MAGERIT (8) ===
  MAGERIT: { label: "MAGERIT v3", definition: "La forma oficial española de identificar qué puede salir mal en tu sistema (ej: que pierdas datos · entren atacantes · se caiga el servidor) y cuánto problema te causaría. Obligatorio si tu proyecto es nivel MEDIA o ALTA.", docLink: "https://administracionelectronica.gob.es/pae_Home/pae_Documentacion/pae_Metodolog/pae_Magerit.html" },
  activo: { label: "Activo", definition: "Cualquier elemento valioso de tu sistema: datos · servicios · software · servidores · personas. Cada activo tiene un valor en MAGERIT y los proteges según su importancia." },
  amenaza: { label: "Amenaza", definition: "Algo malo que puede pasarle a un activo (ej: incendio · ataque ransomware · empleado descontento · fallo eléctrico). MAGERIT trae un catálogo con 57 amenazas estándar para no olvidarte ninguna." },
  salvaguarda: { label: "Salvaguarda", definition: "Medida que reduce que una amenaza ocurra · o que reduce el daño si ocurre (ej: backups · cifrado · formación · alarmas). MAGERIT trae un catálogo de 98." },
  riesgo_intrinseco: { label: "Riesgo intrínseco", definition: "Lo peor que podría pasar SIN ninguna protección. El punto de partida · sin salvaguardas. Sirve para ver cuánto bajas el riesgo cuando aplicas medidas." },
  riesgo_efectivo: { label: "Riesgo efectivo", definition: "Lo que realmente está expuesto HOY · con las salvaguardas que ya tienes. El riesgo actual · el que el auditor quiere ver bajo control." },
  riesgo_residual: { label: "Riesgo residual", definition: "Lo que queda después de aplicar TODO lo planificado. Si es aceptable · firmas y cierras. Si no · hay que añadir más medidas." },
  PILAR: { label: "PILAR", definition: "Herramienta oficial CCN-CERT para hacer análisis MAGERIT. FULKRO importa/exporta XML PILAR para que puedas trabajar en cualquiera de los dos.", docLink: "https://www.ccn-cert.cni.es/herramientas-de-ciberseguridad/pilar.html" },

  // === A.4 · eIDAS / Firma técnica (10) ===
  eIDAS: { label: "eIDAS", definition: "Reglamento europeo de firma electrónica. FULKRO usa firma simple (Art. 25.1) que vale para 99% de documentos · NO firma cualificada (caro · prestador acreditado)." },
  firma_simple: { label: "Firma simple", definition: "Firma electrónica básica · suficiente para 99% de documentos ENS · NO necesitas certificado oficial caro. FULKRO la asegura con criptografía moderna (Ed25519) + código OTP en acciones críticas." },
  firma_cualificada: { label: "Firma cualificada", definition: "Firma electrónica máxima con certificado de prestador acreditado (ej: FNMT). Más cara y compleja · FULKRO NO la implementa · no hace falta para ENS." },
  Ed25519: { label: "Ed25519", definition: "Algoritmo de firma criptográfica moderno · más rápido y seguro que el clásico RSA. FULKRO lo usa para sellar tus firmas digitalmente · indetectable falsificarlo." },
  hash_chain: { label: "Cadena hash", definition: "Cada acción queda firmada matemáticamente y enlazada con la anterior · como una cadena. Si alguien intenta modificar un registro pasado · la cadena se rompe y se nota al instante." },
  SHA256: { label: "SHA-256", definition: "Es la huella digital matemática de un documento. Si cambias una sola coma · la huella es completamente distinta · por eso detecta cualquier manipulación." },
  OTP: { label: "OTP", definition: "One-Time Password · código de 6 dígitos que vale 1 vez. FULKRO te lo pide en acciones críticas (firmar conformidad · autorizar pentest) como confirmación extra." },
  XAdES: { label: "XAdES", definition: "Firma electrónica avanzada sobre XML. Se usa en Facturae para que las facturas a AAPP no se puedan modificar · ellos las verifican automáticamente." },

  // === A.5 · Auth (6) ===
  TOTP: { label: "TOTP", definition: "Time-Based One-Time Password · el código de 6 dígitos que cambia cada 30 segundos en Google Authenticator/Authy. Solo Marcos lo usa · tu portal cliente NO." },
  WebAuthn: { label: "WebAuthn", definition: "Estándar mundial para iniciar sesión con biometría (huella · cara) o llave física FIDO2. Reemplaza la contraseña tradicional · más seguro." },
  JWT: { label: "JWT", definition: "JSON Web Token · una cadena firmada criptográficamente que prueba quién eres en cada petición. FULKRO la guarda en una cookie segura que JavaScript no puede leer (mitiga ataques)." },
  RLS: { label: "RLS", definition: "Row-Level Security · característica de PostgreSQL. Cada cliente solo ve SUS datos automáticamente · imposible filtrar mal por error en el código · la base de datos lo garantiza." },
  scope: { label: "Scope", definition: "Permiso granular asignado a un rol (ej: 'puede firmar documentos' · 'puede ver facturas'). Cada rol tiene su lista · así controlas quién hace qué." },
  CSRF: { label: "CSRF", definition: "Cross-Site Request Forgery · ataque donde una web maliciosa hace acciones en tu nombre. FULKRO protege con un token único en cookie + cabecera · si no coinciden · bloquea la petición." },

  // === A.6 · Workflow 10 fases (10) ===
  workflow_pre_venta: { label: "Fase Pre-venta", definition: "Lead identificado · estás en reunión exploratoria o esperando propuesta firmada. Sin contrato aún · solo conversaciones." },
  workflow_onboarding: { label: "Fase Onboarding", definition: "Acabas de firmar. Recopilamos lo básico: quién es quién en tu organización · qué infraestructura tienes · qué sistemas son críticos." },
  workflow_diagnostico: { label: "Fase Diagnóstico", definition: "Análisis organizacional inicial. Medimos tu madurez ENS (L0-L5) y revisamos qué normativas extra te aplican (RGPD · NIS2 · DORA · sector...)." },
  workflow_analisis_riesgos: { label: "Fase Análisis Riesgos", definition: "MAGERIT en marcha · listamos tus activos · qué amenazas les pueden pasar · qué salvaguardas tienes y cuáles necesitas." },
  workflow_adecuacion: { label: "Fase Adecuación", definition: "MAGERIT aprobado y categoría oficial confirmada. Plan de Adecuación firmado · ya sabes exactamente qué hacer y en qué orden." },
  workflow_implantacion: { label: "Fase Implantación", definition: "Estás aplicando los cambios: políticas · procedimientos · controles técnicos. Vamos recolectando evidencias para el auditor." },
  workflow_dda_final: { label: "Fase DdA Final", definition: "Declaración de Aplicabilidad completa · las 73 medidas implementadas o justificadas como no aplicables. Listo para verificación final." },
  workflow_verificacion: { label: "Fase Verificación", definition: "Pentesting + escaneo de vulnerabilidades con el sistema FULKRO de 5 filtros (Zero False Positive). Cazamos lo real · ignoramos el ruido." },
  workflow_conformidad: { label: "Fase Conformidad", definition: "Dossier ENAC preparado. En MEDIA/ALTA viene el auditor externo · en BÁSICA tú firmas autoevaluación con CCN-STIC 809." },
  workflow_retainer_cierre: { label: "Fase Retainer / Cierre", definition: "Certificación obtenida. Decides: entras en retainer post-cert (mantenemos el ENS vivo) o cerramos proyecto." },

  // === A.7 · Arquetipos PYME (7) ===
  archetype_saas_only: { label: "SaaS Only", definition: "Tu PYME está 100% en cloud · sin servidores propios. ENS focus: contratos con proveedores cloud · backup · acceso · cifrado en SaaS." },
  archetype_teletrabajo: { label: "Teletrabajo Total", definition: "Tus empleados trabajan 100% remotos. ENS focus: securizar el portátil de cada uno · VPN · gestión de identidad · MFA en todo." },
  archetype_sector_salud: { label: "Sector Salud", definition: "Manejas datos de salud (RGPD Art. 9 · datos sensibles). Cifrado obligatorio · roles muy granulares · auditoría reforzada · trazabilidad total." },
  archetype_sector_educacion: { label: "Sector Educación", definition: "Manejas datos de menores. RGPD reforzado + LOPDGDD añade reglas específicas (consentimiento parental · finalidad estricta)." },
  archetype_proveedor_financiero: { label: "Proveedor Financiero", definition: "Sector financiero regulado. ENS + RGPD obligatorios + PSD2 (pagos) + DORA (resiliencia) + a veces PCI-DSS (tarjetas)." },
  archetype_desarrollador_aapp: { label: "Desarrollador AAPP", definition: "Desarrollas software para AAPP. El ENS aplica al sistema que construyes · no solo al tuyo · obliga a cumplir desde diseño." },
  archetype_generico: { label: "Genérico", definition: "PYME estándar sin características sectoriales especiales. ENS sin extras · 73 medidas según tu categoría." },

  // === A.8 · Sectores cross-compliance (6) ===
  sector_fintech: { label: "Fintech", definition: "ENS + RGPD + PSD2 + DORA obligatorios. Si manejas tarjetas · también PCI-DSS. Si servicio esencial UE · NIS2 encima." },
  sector_sanidad: { label: "Sanidad", definition: "ENS + RGPD + RGPD-Salud Art. 9 (datos sensibles · cifrado obligatorio). Auditoría reforzada · controles más estrictos." },
  sector_saas_tech: { label: "SaaS Tech", definition: "ENS + RGPD + ISO 27001 (recomendada · da credibilidad comercial). Si trabajas con AAPP también ENS aplica al servicio que vendes." },
  sector_industria: { label: "Industria", definition: "ENS + RGPD básicos. Si eres sector esencial UE · NIS2 obligatoria. Si tienes OT/ICS (sistemas industriales) · IEC 62443 también." },
  sector_servicios_profesionales: { label: "Servicios Profesionales", definition: "ENS + RGPD básicos. Abogados/auditores tienen además PBC (Prevención Blanqueo Capitales) · ITP (deber secreto)." },
  sector_energia: { label: "Energía", definition: "ENS + RGPD + NIS2 OBLIGATORIA (sector esencial UE). Auditorías reforzadas · incidentes con reporte obligatorio." },

  // === A.9 · Roles ENS (8) ===
  rol_sponsor: { label: "Sponsor", definition: "Patrocinador del proyecto · suele ser CEO. Aprueba presupuestos · es la voz final en decisiones de coste/scope." },
  rol_RI: { label: "RI · Responsable Información", definition: "Responsable de la Información · decide qué datos trata el sistema y cómo de sensibles son. Rol obligatorio en ENS." },
  rol_RS: { label: "RS · Responsable Servicio", definition: "Responsable del Servicio · decide qué presta el sistema y qué disponibilidad necesita. Rol obligatorio en ENS." },
  rol_RSEG: { label: "RSEG · Responsable Seguridad", definition: "Responsable de Seguridad · diseña y supervisa todas las medidas. Firma documentos clave (DdA · políticas). Rol obligatorio en ENS." },
  rol_RSIS: { label: "RSIS · Responsable Sistema", definition: "Responsable del Sistema · implementa técnicamente las medidas. Suele ser tu Director TI. Rol obligatorio en ENS." },
  rol_director_ti: { label: "Director TI", definition: "Cliente lateral · accede a evidencias técnicas y firma documentos técnicos. No es rol ENS oficial pero es operativo en tu portal." },
  rol_gerente: { label: "Gerente", definition: "Cliente · ve resúmenes ejecutivos · firma documentos de gestión · revisa facturas. Acceso intermedio · sin detalles técnicos." },
  rol_lectura_solo: { label: "Solo Lectura", definition: "Cliente · solo ve el resumen del proyecto y descarga documentos públicos. Acceso mínimo para stakeholders externos o consulta." },

  // === A.10 · Magic links (8 · concepto general + 7 specific 3rd parties/post-cierre v3) ===
  magic_link: { label: "Magic link · enlace de un solo uso", definition: "Enlace temporal que se manda por email para hacer una sola acción (firmar · descargar · responder encuesta). Caduca en horas · solo funciona una vez · más seguro que pedir contraseña a alguien externo." },
  ml_AUDITOR_ENAC_REVIEW: { label: "Magic link · Auditor ENAC", definition: "Enlace que recibe el auditor ENAC para revisar tu dossier. Acceso temporal sin necesidad de cuenta · caduca cuando deja de hacer falta." },
  ml_AUDITOR_ENAC_DOSSIER_DOWNLOAD: { label: "Magic link · Descarga dossier auditor", definition: "Enlace al auditor ENAC para descargar el dossier 1 vez. Caduca tras 24h · si lo necesita otra vez · le mandas otro." },
  ml_ABOGADO_NDA_REVIEW: { label: "Magic link · Abogado NDA", definition: "Enlace al abogado externo para firmar el NDA 1 vez sin necesidad de crearle cuenta. Caduca tras firma." },
  ml_PERITO_INFORME: { label: "Magic link · Perito informe", definition: "Enlace al perito externo para acceder a documentos del proyecto y emitir su informe pericial. Acceso limitado a lo necesario." },
  ml_DESCARGA_BACKUP_ARCHIVO: { label: "Magic link · Descarga backup", definition: "Enlace al cliente post-cierre para descargar el ZIP firmado de backup completo del proyecto. Te lo damos cuando cerramos." },
  ml_NPS_POST_CIERRE: { label: "Magic link · NPS post-cierre", definition: "Enlace para encuesta NPS al cliente · una vez el proyecto está cerrado. Nos sirve para mejorar." },
  ml_INCIDENT_REPORT_PUBLIC: { label: "Magic link · Reporte incidente público", definition: "Enlace público para que cualquier persona reporte un incidente de seguridad sin necesidad de login · útil si descubren algo en producción." },

  // === A.11 · Frameworks externos (6) ===
  RGPD: { label: "RGPD", definition: "Reglamento General de Protección de Datos UE. Obligatorio para cualquiera que trate datos personales · multas hasta 20M€ o 4% facturación." },
  NIS2: { label: "NIS2", definition: "Directiva UE de ciberseguridad para sectores esenciales (energía · transporte · banca · sanidad · agua · digitales). Obligatoria desde 2024." },
  DORA: { label: "DORA", definition: "Digital Operational Resilience Act · obligatorio para finanzas UE desde enero 2025. Resiliencia operacional · reportar incidentes · gestión de proveedores TIC." },
  PSD2: { label: "PSD2", definition: "Payment Services Directive 2 · regula servicios de pago en UE. Obliga a autenticación reforzada (SCA) y abre APIs bancarias." },
  ISO_27001: { label: "ISO 27001", definition: "Estándar internacional de gestión de seguridad. Voluntaria · pero da credibilidad comercial · 39 medidas mapeables a ENS." },
  ENI: { label: "ENI", definition: "Esquema Nacional de Interoperabilidad · el hermano del ENS para que las AAPP puedan intercambiar datos entre sí. Si trabajas con AAPP · te aplica." },

  // === A.12 · Adaptadores externos (5) ===
  CLARA: { label: "CLARA", definition: "Plataforma CCN-CERT para gestionar tus certificados ENS · su renovación · y el reporte de cumplimiento al CCN." },
  LUCIA: { label: "LUCIA", definition: "Federación CCN-CERT para reportar tu conformidad ENS al estado. Una vez certificado · mandas reporte aquí." },
  INES: { label: "INES", definition: "Informe Nacional del Estado de la Seguridad · reporte anual del estado de seguridad. Para proveedores PRIVADOS es voluntario (lo vinculante es la certificación ENS); FULKRO puede generarlo si tu organismo cliente lo solicita." },
  FACE: { label: "FACE", definition: "Punto General de Entrada de Facturas Electrónicas a AAPP. Si facturas a una administración pública · va por aquí en formato Facturae." },
  Facturae: { label: "Facturae", definition: "Formato XML español obligatorio para facturar a AAPP. Versión 3.2.x · firmado XAdES · FULKRO lo genera y firma automáticamente." },
  Verifactu: { label: "Verifactu", definition: "Sistema de la Agencia Tributaria que controla las facturas en tiempo real (obligatorio desde 2025). FULKRO genera tus facturas firmadas y las envía automáticamente · sin que tengas que hacer nada.", docLink: "https://sede.agenciatributaria.gob.es/verifactu" },

  // === A.13 · Scoring ENS (6) ===
  maturity_L0: { label: "Madurez L0", definition: "Inexistente · la medida no está implementada ni planificada. Punto de partida para muchas medidas en el primer diagnóstico." },
  maturity_L1: { label: "Madurez L1", definition: "Inicial · existe conciencia y se hace algo · pero ad-hoc · sin proceso definido. Suficiente para algunas medidas BÁSICAS · insuficiente en MEDIA/ALTA." },
  maturity_L2: { label: "Madurez L2", definition: "Repetible · proceso documentado · pero no aplicado igual en todas las áreas. Hay inconsistencia entre departamentos." },
  maturity_L3: { label: "Madurez L3", definition: "Nivel intermedio de madurez ENS · la medida funciona en producción y se documenta · pero no se mide ni mejora aún. Es donde la mayoría de PYMEs aterriza tras adecuación." },
  maturity_L4: { label: "Madurez L4", definition: "Gestionado · el proceso se mide · monitoriza · y mejora con datos. Buen nivel · objetivo a largo plazo." },
  maturity_L5: { label: "Madurez L5", definition: "Optimizado · proceso optimizado continuamente con automatización. El máximo · raro alcanzar todas las medidas a este nivel." },

  // === A.14 · Documentos clave (10) ===
  P001_propuesta: { label: "P-001 Propuesta", definition: "Documento maestro comercial · detalla qué haremos · pricing · hitos · plazos. Generado automático por A19 (Opus 4.7) según tu caso." },
  C001_contrato: { label: "C-001 Contrato", definition: "Contrato principal de consultoría ENS. Cláusulas dinámicas según tu categoría (BÁSICA/MEDIA/ALTA) y si eres AAPP o no." },
  C002_adenda: { label: "C-002 Adenda Proveedor", definition: "Adenda al contrato de cada proveedor crítico. Detecta gaps de seguridad según ENS Art. 18 + RGPD Art. 28 (encargado de tratamiento)." },
  C003_retainer: { label: "C-003 Retainer", definition: "Contrato post-certificación ENS · 4 perfiles disponibles (LITE · STD · PLUS · CRITICAL) según tamaño y criticidad." },
  C004_NDA: { label: "C-004 NDA", definition: "Acuerdo de confidencialidad mutuo. Necesario antes de compartir información sensible con proveedores · auditores · peritos." },
  C005_SLA: { label: "C-005 SLA", definition: "Acuerdo de Nivel de Servicio · qué garantizo y qué pasa si no se cumple. Aplicable en retainer post-cert." },
  E040_acta: { label: "E-040 Acta", definition: "Acta de comité de seguridad. DOCX firmado con hash + Ed25519 + firma in-portal del cliente. Evidencia clave para auditor ENAC." },
  E090: { label: "E-090", definition: "Análisis de Riesgos · documento E-090. Secciones de narrativa generadas con IA (A4) · cálculos deterministas en M21+M22. Reproducible." },
  PDA: { label: "PDA · Plan de Adecuación", definition: "Plan de Adecuación · detalla cómo vas a implementar las 73 medidas ENS · en qué orden · con qué presupuesto · firmado por tu RSEG." },
  DdA: { label: "DdA · Declaración Aplicabilidad", definition: "Declaración de Aplicabilidad · documento que dice qué medidas ENS aplican y cuáles no (con justificación). 73 entries obligatorias · es el doc estrella." },

  // === A.15 · Pentesting (8) ===
  zero_false_positive: { label: "Zero False Positive", definition: "Sistema FULKRO de 5 filtros que revisa cada vulnerabilidad encontrada. Sin filtros: 80% de alertas son ruido falso. Con filtros: solo te avisa del 5% que es real." },
  MITRE_ATT_CK: { label: "MITRE ATT&CK", definition: "Catálogo mundial de todas las formas conocidas de atacar sistemas · usado por defensores. FULKRO etiqueta cada vulnerabilidad con su técnica MITRE para que sepas qué tipo de ataque es." },
  purple_team: { label: "Purple Team", definition: "Combinación de red team (ataca) + blue team (defiende) trabajando juntos. FULKRO automatiza ambos para que veas cómo te defenderías ante un ataque real." },
  CVE: { label: "CVE · Common Vulnerabilities and Exposures", definition: "Identificador único de cada vulnerabilidad pública conocida (ej: CVE-2024-1234). Como matrícula que sigue una vulnerabilidad por todo el mundo · todos los antivirus y escáneres usan los mismos códigos.", docLink: "https://cve.mitre.org/" },
  CVSS: { label: "CVSS · Common Vulnerability Scoring System", definition: "Puntuación de gravedad de una vulnerabilidad (0-10). 0-3.9 baja · 4-6.9 media · 7-8.9 alta · 9-10 crítica. FULKRO prioriza por CVSS para que arregles primero las críticas.", docLink: "https://www.first.org/cvss/" },
  OWASP_top_10: { label: "OWASP Top 10", definition: "Las 10 vulnerabilidades web más comunes mundialmente · actualizado cada pocos años. Si tu app web no falla en ninguna del Top 10 · tienes un nivel de seguridad respetable.", docLink: "https://owasp.org/Top10/" },
  SAST: { label: "SAST · Static Application Security Testing", definition: "Análisis del código fuente buscando bugs sin ejecutar la app · como un revisor que lee tu programa antes de que se publique. Detecta SQL injection · contraseñas hardcoded · etc." },
  DAST: { label: "DAST · Dynamic Application Security Testing", definition: "Análisis con la app corriendo · le envía ataques reales como si fuera un hacker y mira qué responde. Complementa al SAST: SAST mira código · DAST mira comportamiento real." },

  // === A.16 · Retainer (5) ===
  retainer_R_LITE: { label: "R LITE", definition: "Retainer para microempresa o PYME pequeña ≤25 usuarios. 300-700€/mes · vigilancia normativa + monitoring básico · ideal post-cert simple." },
  retainer_R_STD: { label: "R STD", definition: "Retainer estándar para PYME 26-150 usuarios. 700-1200€/mes · CISO virtual a tiempo parcial + comité trimestral + soporte continuo." },
  retainer_R_PLUS: { label: "R PLUS", definition: "Retainer para empresas medianas 150-500 usuarios · multi-sede o cloud complejo. 1200€+/mes · CISO + auditoría anual + simulacro DR." },
  retainer_R_CRITICAL: { label: "R CRITICAL", definition: "Retainer máximo para sistemas categoría ALTA o tras un cambio material grande. CISO + 24/7 IR + pentest recurrente · pricing personalizado." },
  retainer_drift: { label: "Drift", definition: "Cuando una medida que estaba bien implantada empieza a degradarse (no se actualiza · no se revisa). FULKRO detecta drift automático · te avisa antes de que sea problema en auditoría." },

  // === A.17 · Evidencias (5) ===
  evidencia: { label: "Evidencia", definition: "Cualquier prueba (PDF · captura · log · certificado) de que una medida ENS funciona realmente. Sin evidencia · una medida es solo papel · no la puedes defender ante auditor." },
  freshness: { label: "Frescura", definition: "Estado de actualización de una evidencia: vigente / próxima a caducar / caducada. Las evidencias caducadas NO valen · te aviso para que renueves antes." },
  renewal: { label: "Renovación", definition: "Solicitud automática de renovar una evidencia que está cerca de caducar. Notificamos al responsable · le decimos qué hace falta y para cuándo." },
  cadena_custodia: { label: "Cadena de custodia", definition: "Registro inmutable de quién accedió a una evidencia · cuándo · y qué hizo. Crítico para que el auditor ENAC confíe en lo que ve." },
  evidencia_firmada: { label: "Evidencia firmada", definition: "Evidencia con firma Ed25519 que garantiza no ha sido modificada desde su ingestión. El auditor verifica la firma y sabe que es la original." },

  // === A.18 · NEW v3 · in-portal + WhatsApp + capabilities (7) ===
  whatsapp_thread: { label: "WhatsApp · canal directo", definition: "Comunicación 1:1 con Marcos vía WhatsApp Business · sincronizada con tu portal. Lo que hablas en WhatsApp queda registrado y trazable también." },
  in_portal_signing: { label: "Firma in-portal", definition: "Firmas documentos directamente en el portal · sin descargar PDF · sin abrir email · sin app externa. Click en 'Firmar' · introduces código OTP · firmado." },
  signing_intent: { label: "Intent de firma", definition: "Cuando haces click 'Firmar' · se genera un intent que expira en 15 minutos. Te asegura que la firma es deliberada · no un click accidental que se procesó después." },
  step_up_otp: { label: "OTP refuerzo", definition: "Para acciones críticas (autorizar pentest · firmar conformidad) · te pedimos un OTP de 6 dígitos como confirmación adicional. Doble check antes de algo importante." },
  capability_active: { label: "Capability activa", definition: "Funcionalidad opcional ya activada para tu proyecto · suele ser feature avanzada o recomendada según tu perfil sectorial/regulatorio." },
  capability_recommended: { label: "Capability recomendada", definition: "Funcionalidad sugerida basada en tu proyecto · puedes activarla cuando quieras o ignorarla. Solo recomendaciones · no obligación." },
  multihop_propagation: { label: "Propagación multi-hop", definition: "Cálculo avanzado MAGERIT que propaga riesgos entre activos en topologías complejas (>200 activos típicamente). Sin esto · te perderías cadenas de impacto en sistemas grandes." },

  // === A.19 · Pricing & Continuidad (8) ===
  tier_basica: { label: "Pack BÁSICA · 3.900€", definition: "Adecuación ENS BÁSICA para sistemas no-críticos (ej: web informativa · CRM interno). 30-40h trabajo · sin auditor externo · ideal primer ENS PYME." },
  tier_media: { label: "Pack MEDIA · desde 9.500€", definition: "Adecuación ENS MEDIA para sistemas que tratan datos sensibles. 80-110h trabajo · base 9.500€ · con extras según complejidad (sector regulado · multi-ubicación · varios sistemas) llega a 16.000€." },
  tier_alta: { label: "Pack ALTA · 25.000€+", definition: "Adecuación ENS ALTA para sistemas críticos (sanidad · energía · defensa · grandes AAPP). Desde 25.000€ · siempre en co-consultoría con partner senior por la complejidad. Incluye auditor ENAC obligatorio." },
  BIA: { label: "BIA · Business Impact Analysis", definition: "Análisis que mide cuánto te dolería que cada parte de tu sistema fallara (en dinero · reputación · clientes). Obligatorio en ENS MEDIA/ALTA · base para decidir qué proteges con más prioridad." },
  RTO: { label: "RTO · Recovery Time Objective", definition: "Cuántas horas máximo puede estar caído tu sistema sin que sea catástrofe. Si tu RTO es 4h · debes tener todo listo para recuperarte en menos de 4h tras un fallo." },
  RPO: { label: "RPO · Recovery Point Objective", definition: "Cuántos datos puedes permitirte perder. Si tu RPO es 1h · necesitas un backup cada hora máximo · si pierdes el último · solo pierdes 1h de trabajo." },
  backup_policy: { label: "Política de copias de seguridad", definition: "Documento que define cuándo se hacen backups · dónde se guardan · cuánto tiempo se conservan · y cuándo se prueban (¡un backup que nunca se ha probado puede no funcionar!). Obligatorio ENS." },
  incidente_seguridad: { label: "Incidente de seguridad", definition: "Cualquier evento que pone en riesgo tus datos (hackeo · robo de portátil · email phishing exitoso · empleado malicioso). Si afecta a datos personales · debes notificarlo a la AEPD en menos de 72h.", docLink: "https://www.aepd.es/derechos-y-deberes/cumple-tus-deberes/medidas-de-cumplimiento/notificacion-de-quiebras-seguridad" },

  // === A.20 · Discovery técnico M22 (6 keys NEW v3.MB-4.1) ===
  pentest: { label: "Pentest · prueba de penetración", definition: "Auditor simula ser hacker e intenta romper tu sistema (con tu permiso · sin daño real). Encuentra fallos antes de que los encuentre alguien malo. Más profundo que un escaneo automático." },
  cis_benchmark: { label: "CIS benchmark", definition: "Lista de configuraciones recomendadas para servidores · cloud · BBDD (publicadas por Center for Internet Security). Pasa el check si tus configuraciones cumplen el estándar; falla si están sueltas · descuidadas.", docLink: "https://www.cisecurity.org/cis-benchmarks" },
  dataflow: { label: "Diagrama de flujos de datos", definition: "Mapa visual de cómo viajan tus datos (origen → procesado → destino · qué cifrado lleva · si cruzan fronteras). Obligatorio RGPD · indispensable detectar transferencias internacionales que requieren cláusulas tipo." },
  siem: { label: "SIEM · gestor centralizado de logs", definition: "Sistema que recoge logs de todos tus servidores · firewalls · apps · y los analiza en tiempo real buscando patrones de ataque. Ejemplos: Splunk · Sentinel · Wazuh. Obligatorio ENS MEDIA/ALTA." },
  log_management: { label: "Gestión de logs", definition: "Dónde se guardan los registros · cuánto tiempo · quién puede borrarlos. ENS pide retención mínima (típicamente 1-2 años) y que sean inmutables (nadie puede modificar el pasado).", docLink: "https://www.boe.es/buscar/act.php?id=BOE-A-2022-7191" },
  RGPD_Art_49: { label: "RGPD Art. 49 · transferencias internacionales", definition: "Si mandas datos personales fuera del EEE (ej: backup en US · servicio cloud en Singapur) · necesitas garantías formales (cláusulas tipo · BCR · adequacy decision). Sin esto · transferencia ilegal." },

  // === A.21 · Workspace M20 (2 keys NEW v3.MB-4.2) ===
  workspace_proyecto: { label: "Workspace del proyecto", definition: "Espacio compartido entre Marcos y tu equipo durante el proyecto · contiene archivos en staging · chat bilateral · y un timeline de actividad. Marcos lo gestiona desde el panel admin · tu lado lo ves en el portal." },
  audit_log: { label: "Audit log · timeline trazable", definition: "Registro inmutable de eventos del proyecto (qué pasó · quién · cuándo). Incluye creación/edición de documentos · firmas · evidencias aportadas · etc. Crítico para auditoría ENS y RGPD: cualquier acción debe poder reconstruirse." },

  // === A.22 · Onboarding M16 (3 keys NEW v3.MB-4.3) ===
  branching_logic: { label: "Branching · ramificación de preguntas", definition: "Las preguntas del wizard se adaptan a tus respuestas previas: si dices que no usas cloud · saltamos las preguntas de cloud. Te ahorra responder cosas que no aplican a tu organización." },
  oauth_real: { label: "OAuth · conexión segura sin pegar contraseñas", definition: "Conectas tu workspace (GitHub · Microsoft 365 · Azure · Google) sin dar credenciales a FULKRO. Te lleva al login del proveedor · autorizas · y FULKRO recibe un token revocable. Puedes desconectar cuando quieras." },
  lms_assignment: { label: "Asignación de curso (LMS)", definition: "Curso de concienciación obligatorio asignado a tu equipo (cumplimiento ENS · RGPD · ISO 27001). Cuando un empleado lo completa · genera certificado E-502 · evidencia auditable." },

  // === A.23 · Inbox cliente · MB-4.bis3 ADR-020 (1 key NEW) ===
  inbox_cliente: { label: "Bandeja de notificaciones", definition: "Centraliza acciones pendientes (firmas · evidencias · ofertas · etc) en tu portal · sustituye los emails con enlaces de un solo uso. Todo dentro del portal · cliquea para ir a la página de acción · marca como leído o descártalo." },

} as const satisfies Record<string, GlossaryEntry>;

export type GlossaryKey = keyof typeof GLOSARIO_ENS;

export function getGlossaryEntry(key: string): GlossaryEntry | null {
  return (GLOSARIO_ENS as Record<string, GlossaryEntry>)[key] ?? null;
}
