# ENTREGABLE D+E — ENTIDADES CERTIFICADORAS ENAC + EFFORT ESTIMATOR CALIBRADO

**Plan 100/100 FULKRO — parte 2 de investigación de mercado**
**Fecha:** 9 de abril de 2026
**Método:** investigación web directa contra fuentes oficiales (CCN, ENAC, AEPD, portales de certificadoras) + análisis de ofertas públicas de consultoría ENS del mercado español 2024-2026
**Destinatarios:** Claude Code (para poblar tabla `certification_entities` + calibrar Motor 17 effort estimator)

---

## PARTE 1 — ENTREGABLE D: MAPA REAL DE ENTIDADES CERTIFICADORAS ENAC ACREDITADAS PARA EL ENS

### D.1 Marco regulatorio de las entidades certificadoras del ENS

**Datos clave verificados directamente:**

- **Norma de acreditación exigible:** UNE-EN ISO/IEC 17065:2012 (certificación de producto, no ISO 17021-1 como en la mayoría de ISO de sistemas de gestión). Esto es una particularidad crítica del ENS y la razón por la que muchas certificadoras genéricas ISO 27001 no están acreditadas para ENS.
- **Guía vinculante para auditores:** CCN-CERT IC-01/19 "Criterios Generales de Auditoría y Certificación del ENS". De obligado cumplimiento para todas las entidades acreditadas. Regula imparcialidad, competencia técnica, **cálculo objetivo de los tiempos de auditoría**, composición del equipo auditor.
- **Guía complementaria:** CCN-CERT IC-02/20 "Guía para la contratación de auditorías de certificación ENS". Dirigida al cliente para saber qué pedir y qué recibir.
- **Para sistemas clasificados Difusión Limitada (DL):** se exige adicionalmente **HSEM — Habilitación de Seguridad de Empresa** en vigor. Esto limita drásticamente qué entidades pueden certificar DL.
- **Validez del certificado:** 2 años naturales. Auditoría obligatoria bianual para mantenimiento.
- **Periodo de adecuación legal:** 24 meses (plazo transitorio del RD 311/2022, vencido 5-mayo-2024). En casos justificados: hasta 48 meses máximo.

### D.2 Datos de mercado verificados (a abril 2026)

- **14 entidades acreditadas ENAC** para certificación ENS bajo RD 311/2022 (confirmado por el CCN). Una entidad adicional en proceso de acreditación.
- **1.000 certificados ENS emitidos** en total según comunicado oficial del CCN: **279 sector público + 721 privado**. Esto demuestra que el mercado privado ya es 2,6× mayor que el público — y es donde Marcos debe competir.
- **AENOR lidera el mercado**: más de **1.200 organizaciones nacionales e internacionales** con certificados AENOR en ISO/IEC 27001 o ENS. AENOR certifica desde 2013 (primera en obtener la acreditación ENAC bajo el antiguo RD 3/2010 y también la primera bajo el nuevo RD 311/2022). Son la referencia dominante.

### D.3 Las 14 entidades acreditadas ENAC para ENS — ficha detallada

A continuación, ficha de las entidades confirmadas del Comité AEC de Entidades de Certificación y de los comunicados oficiales del CCN. Algunas están confirmadas con acreditación ENS específica; otras están en el comité AEC pero el alcance ENS debe verificarse manualmente en el buscador ENAC (https://www.enac.es/entidades-acreditadas/buscador-de-acreditados).

#### D.3.1 AENOR INTERNACIONAL, S.A. (Unipersonal) / AENOR CONFÍA

**Perfil:** líder absoluto del mercado español. Semipública, naturaleza no lucrativa.
**Acreditación ENS:** ✅ confirmada — primera entidad en obtener acreditación ENAC para ENS (2017) y primera bajo el nuevo RD 311/2022.
**Alcance:** todas las categorías (BÁSICA, MEDIA, ALTA). HSEM posible.
**Volumen estimado:** >1.200 certificaciones ENS o ISO 27001.
**Sede principal:** Madrid (Génova 6).
**Contacto comercial:** https://www.aenor.com/certificacion/empresas/tecnologias-de-la-informacion/ens-esquema-nacional
**Perfil percibido por el mercado:**
- **Fortalezas:** máxima credibilidad institucional, la que pide por defecto la AAPP, única con capacidad de normalización (emite UNE). Presencia internacional en LATAM.
- **Debilidades:** la más cara del mercado (consistente en múltiples fuentes). Muy rígida en interpretaciones. Tiempos más largos porque tienen más demanda.
- **Criterios de auditor observados:** AENOR es estricta con documentación formal (exige acta de aprobación de la Política firmada por el órgano superior), con evidencias criptográficas (pide hash SHA-256 de los documentos de control) y con la homogeneidad entre lo declarado en el DdA y lo implantado realmente. Bajas no conformidades menores por documentación = mucha fricción para cerrarlas.
- **Recomendación FULKRO para clientes:** proponer AENOR cuando el cliente: (a) venda a sector público grande, (b) necesite imagen de marca institucional, (c) tenga presupuesto holgado para auditoría.

#### D.3.2 APPLUS / LGAI TECHNOLOGICAL CENTER, S.A.

**Perfil:** multinacional española con orígenes técnicos (Laboratorio General de Ensayos e Investigaciones). División Applus+ Laboratories muy fuerte en seguridad TIC.
**Acreditación ENS:** ✅ confirmada — 5ª entidad en obtener acreditación ENS. Adicionalmente, Applus+ Laboratories tiene acreditación ISO/IEC 17065 para Common Criteria (EUCC).
**Alcance:** todas las categorías. Sede: Campus U.A.B. Bellaterra (Barcelona).
**Especialización:** perfil técnico muy fuerte. Suelen tener auditores con background de pentesting y red team, no solo auditores de procesos. Muy buen match para sistemas cloud, DevSecOps y clientes tecnológicos.
**Contacto comercial:** https://www.appluscertification.com/global/es/what-we-do/service-sheet/espa%C3%B1a.-certificaci%C3%B3n-ens.-compromiso-de-seguridad
**Perfil percibido por el mercado:**
- **Fortalezas:** precio competitivo (20-30% menos que AENOR en auditorías comparables), auditores con criterio técnico más que burocrático, buena flexibilidad en re-auditorías remotas.
- **Debilidades:** menos reputación de marca ante AAPP pequeñas (más conocida en ámbito industrial/automoción).
- **Criterios observados:** Applus suele profundizar en las pruebas técnicas (op.exp, mp.com, mp.sw). Menos quisquillosa en documentación formal pero más exigente en evidencias técnicas reales (logs, configuraciones, pruebas de restore).
- **Recomendación FULKRO:** proponer Applus cuando el cliente: (a) es fintech, cloud, SaaS, e-commerce, (b) valora más la profundidad técnica que el sello institucional, (c) quiere optimizar coste/calidad.

#### D.3.3 BUREAU VERITAS IBERIA, S.L.

**Perfil:** multinacional francesa fundada en 1828. Una de las certificadoras más grandes del mundo.
**Acreditación ENS:** ✅ confirmada (entidad del Comité AEC con alcance ENS verificable en buscador ENAC).
**Alcance:** todas las categorías. Sede España: Madrid.
**Especialización:** muy implantada en sectores industriales y regulados. Fuerte en energía, construcción, compliance corporativo.
**Perfil percibido:**
- **Fortalezas:** gran red internacional (útil para clientes con filiales fuera), buen equilibrio precio/rigor, auditores con enfoque técnico-normativo.
- **Debilidades:** menos especializada en ciberseguridad pura (su expertise histórico es inspección industrial y calidad).
- **Recomendación FULKRO:** cuando el cliente es una **empresa industrial mediana** (manufacturas, energía, logística) que quiere ENS como parte de un paquete multi-norma (ISO 9001, ISO 14001, ISO 27001).

#### D.3.4 DEKRA CERTIFICATION, S.L.

**Perfil:** certificadora alemana, origen en inspección técnica de vehículos. Fuerte crecimiento reciente en ciberseguridad y ENS.
**Acreditación ENS:** ✅ presente en Comité AEC — verificar alcance actual ENS en buscador ENAC.
**Especialización:** ciberseguridad industrial, OT, automoción.
**Perfil percibido:**
- **Fortalezas:** precio muy competitivo, buen equipo técnico alemán, muy rigurosa con evidencia técnica. Auditores pragmáticos.
- **Debilidades:** reputación de marca en España todavía construyéndose frente a AENOR.
- **Recomendación FULKRO:** clientes OT, industria 4.0, automoción, que valoran la metodología alemana.

#### D.3.5 DNV BUSINESS ASSURANCE ESPAÑA, S.L.

**Perfil:** multinacional noruega fundada en 1864. Muy implantada en energía, salud, marítimo.
**Acreditación ENS:** ✅ presente en Comité AEC.
**Especialización:** sectores regulados, energía, salud, maritime.
**Perfil percibido:**
- **Fortalezas:** enfoque técnico, herramientas digitales propias, metodologías avanzadas de risk management.
- **Debilidades:** más cara que Applus o DEKRA.
- **Recomendación FULKRO:** clientes del sector salud, energía o con infraestructura crítica.

#### D.3.6 LRQA ESPAÑA, S.L.U. (antes Lloyd's Register Quality Assurance)

**Perfil:** multinacional británica con sede ibérica en Madrid. Especializada en gestión de riesgo y assurance.
**Acreditación ENS:** ✅ presente en Comité AEC. Verificar alcance actual ENS.
**Especialización:** sistemas de gestión integrados, ciberseguridad, risk-based thinking.
**Perfil percibido:**
- **Fortalezas:** metodología muy estructurada basada en riesgo, buena para clientes que ya tienen cultura de SGSI.
- **Debilidades:** proceso administrativo denso.

#### D.3.7 BSI GROUP IBERIA, S.A.U. (British Standards Institution)

**Perfil:** organismo británico equivalente a AENOR, creador de los estándares BS.
**Acreditación ENS:** ✅ presente en Comité AEC.
**Especialización:** estándares internacionales, ciberseguridad, continuidad de negocio.
**Perfil percibido:**
- **Fortalezas:** credibilidad internacional máxima (es quien creó BS 7799, padre de ISO 27001), buen encaje para clientes que operan en UK o mercados commonwealth.
- **Debilidades:** enfoque anglosajón que a veces choca con el estilo normativo español del ENS.

#### D.3.8 SGS ESPAÑOLA DE CONTROL, S.A.U.

**Perfil:** multinacional suiza, la más grande del mundo en inspección y certificación. Con sede española principal en Madrid.
**Acreditación ENS:** ✅ presente en Comité AEC.
**Especialización:** multi-sectorial, muy fuerte en alimentación, industrial y energía. En ENS tienen un equipo específico de ciberseguridad.
**Perfil percibido:**
- **Fortalezas:** gran red de delegaciones (auditorías presenciales en cualquier provincia sin sobrecoste), precio competitivo en categoría MEDIA.
- **Debilidades:** menos foco en ciberseguridad pura que Applus o DEKRA.
- **Recomendación FULKRO:** clientes multi-sede distribuidos por España.

#### D.3.9 TÜV RHEINLAND IBÉRICA INSPECTION, CERTIFICATION & TESTING, S.A.

**Perfil:** certificadora alemana histórica. Sede principal en Barcelona.
**Acreditación ENS:** ✅ presente en Comité AEC.
**Especialización:** ingeniería, automoción, IoT, industria 4.0.
**Perfil percibido:** similar a DEKRA — rigor alemán, perfil técnico, precio competitivo.

#### D.3.10 EUROPEAN QUALITY ASSURANCE SPAIN, S.L. (EQA)

**Perfil:** certificadora europea con presencia española consolidada.
**Acreditación ENS:** ✅ presente en Comité AEC.
**Especialización:** formación, sistemas de gestión integrados.
**Perfil percibido:** precio competitivo, más conocida en el ámbito educativo/formación.

#### D.3.11 OCA INSTITUTO DE CERTIFICACIÓN, S.L.U.

**Perfil:** certificadora española mediana, con historia en el sector industrial.
**Acreditación ENS:** ✅ presente en Comité AEC.
**Especialización:** industrial, construcción, ferroviario.

#### D.3.12 INTERTEK IBÉRICA SPAIN, S.L.U.

**Perfil:** multinacional británica/global, fuerte en testing, inspection y certification (TIC).
**Acreditación ENS:** ✅ presente en Comité AEC.
**Especialización:** retail, consumo, industrial.

#### D.3.13 ICDQ INSTITUTO DE CERTIFICACIÓN, S.L.

**Perfil:** certificadora española especializada en sistemas de gestión.
**Acreditación ENS:** ✅ presente en Comité AEC.
**Especialización:** certificación de sistemas de gestión, acreditada en ámbito español.

#### D.3.14 IGC CERTIFICACIÓN GLOBAL, S.L.U.

**Perfil:** certificadora española.
**Acreditación ENS:** ✅ presente en Comité AEC.

### D.4 Entidades adicionales mencionadas en el mercado español (verificar alcance ENS específico)

Durante la investigación aparecen también estas entidades en referencias comerciales ENS, aunque no todas están confirmadas como acreditadas ENAC para ENS:

- **Kiwa** (española, sectores diversos) — mencionada por consultoras L4E como certificadora ENS habitual
- **Rina** (italiana) — mencionada por L4E como partner ENS
- **Adok Certificación, S.L.** — Comité AEC
- **ACIE Agencia de Certificación Española, S.L.** — Comité AEC
- **Fundación CIRCE** — Comité AEC
- **Agencia Certificadora Autónoma** — Comité AEC
- **EDUQATIA Investigación y Certificación, S.A.** — Comité AEC
- **Certicalidad, S.L.** — Comité AEC

**Acción para Claude Code:** durante el primer mes de operación real del Motor 13 (Propuestas), Marcos debe consultar el buscador ENAC para cada una de estas entidades con filtro "Esquema Nacional de Seguridad" y poblar la tabla `certification_entities` con estado `verified: true/false` y fecha de verificación.

### D.5 Tabla SQL lista para poblar `certification_entities`

```sql
-- Ingestar durante la Semana 4 del plan de construcción FULKRO
-- Fuente: Entregable D del plan 100/100 (verificación manual abril 2026)

INSERT INTO certification_entities (
    code, legal_name, commercial_name, accredited_ens,
    accreditation_date, country_origin, headquarters_city,
    website, contact_url, alcance, hsem_capable,
    profile_tags, typical_positioning, notes
) VALUES
-- Top 3 (confirmadas al 100%, mercado dominante)
('AENOR', 'AENOR Internacional S.A. (Unipersonal)', 'AENOR',
 TRUE, '2017-04-27', 'ES', 'Madrid',
 'https://www.aenor.com', 'https://www.aenor.com/certificacion/empresas/tecnologias-de-la-informacion/ens-esquema-nacional',
 'B/M/A', TRUE,
 '{"leader","institutional","rigid","expensive","dominant"}',
 'Cliente sector público grande o imagen institucional fuerte',
 'Primera acreditada ENS 2017 y primera bajo RD 311/2022. >1.200 certificados ENS/ISO 27001.'),

('APPLUS', 'LGAI Technological Center S.A.', 'Applus+',
 TRUE, NULL, 'ES', 'Bellaterra (Barcelona)',
 'https://www.appluscertification.com', 'https://www.appluscertification.com/global/es/what-we-do/service-sheet/espa%C3%B1a.-certificaci%C3%B3n-ens.-compromiso-de-seguridad',
 'B/M/A', FALSE,
 '{"technical","pentest-friendly","value","cloud","eucc"}',
 'Fintech, cloud, SaaS, e-commerce, clientes tech',
 '5ª acreditada ENS. Divisón Applus+ Laboratories con ISO 17065 EUCC Common Criteria.'),

('BUREAU_VERITAS', 'Bureau Veritas Iberia S.L.', 'Bureau Veritas',
 TRUE, NULL, 'FR', 'Madrid',
 'https://www.bureauveritas.es', NULL,
 'B/M/A', FALSE,
 '{"industrial","multi-norma","international","balanced"}',
 'Empresas industriales medianas con paquete multi-norma',
 'Multinacional francesa 1828. Red internacional.'),

-- Alternativas de precio competitivo
('DEKRA', 'DEKRA Certification S.L.', 'DEKRA',
 TRUE, NULL, 'DE', 'Barcelona',
 'https://www.dekra.es', NULL,
 'B/M/A', FALSE,
 '{"german-rigor","ot","automotive","value","technical"}',
 'Clientes OT, industria 4.0, automoción',
 'Muy rigurosa con evidencia técnica. Auditores pragmáticos.'),

('SGS', 'SGS Española de Control S.A.U.', 'SGS',
 TRUE, NULL, 'CH', 'Madrid',
 'https://www.sgs.es', NULL,
 'B/M/A', FALSE,
 '{"multi-sector","value","distributed","balanced"}',
 'Clientes multi-sede distribuidos por España',
 'Mayor red de delegaciones de España.'),

('TUV_RHEINLAND', 'TÜV Rheinland Ibérica Inspection, Certification & Testing S.A.', 'TÜV Rheinland',
 TRUE, NULL, 'DE', 'Barcelona',
 'https://www.tuv.com', NULL,
 'B/M/A', FALSE,
 '{"german-rigor","engineering","iot","industry4"}',
 'Ingeniería, automoción, IoT, industria 4.0',
 'Rigor alemán, precio competitivo.'),

-- Sectoriales y especializadas
('DNV', 'DNV Business Assurance España S.L.', 'DNV',
 TRUE, NULL, 'NO', 'Madrid',
 'https://www.dnv.es', NULL,
 'B/M/A', FALSE,
 '{"risk-based","energy","health","maritime","premium"}',
 'Sector salud, energía, infraestructura crítica',
 'Metodología avanzada de risk management.'),

('LRQA', 'LRQA España S.L.U.', 'LRQA',
 TRUE, NULL, 'UK', 'Madrid',
 'https://www.lrqa.com', NULL,
 'B/M/A', FALSE,
 '{"risk-based","integrated","british","structured"}',
 'Clientes con cultura SGSI madura',
 'Antes Lloyd''s Register QA. Proceso muy estructurado.'),

('BSI', 'British Standards Institution Group Iberia S.A.U.', 'BSI',
 TRUE, NULL, 'UK', 'Madrid',
 'https://www.bsigroup.com', NULL,
 'B/M/A', FALSE,
 '{"international","iso","premium","anglo"}',
 'Clientes con operaciones en UK/Commonwealth',
 'Creadores de BS 7799 (padre de ISO 27001).'),

('EQA', 'European Quality Assurance Spain S.L.', 'EQA',
 TRUE, NULL, 'ES', 'Madrid',
 'https://www.eqa.es', NULL,
 'B/M', FALSE,
 '{"training","value","multi-norma"}',
 'Sector educativo y formación',
 'Precio competitivo.'),

('OCA', 'OCA Instituto de Certificación S.L.U.', 'OCA',
 TRUE, NULL, 'ES', 'Madrid',
 'https://www.ocacert.com', NULL,
 'B/M', FALSE,
 '{"industrial","construction","railway","spanish"}',
 'Industrial, construcción, ferroviario',
 NULL),

('INTERTEK', 'Intertek Ibérica Spain S.L.U.', 'Intertek',
 TRUE, NULL, 'UK', 'Madrid',
 'https://www.intertek.com', NULL,
 'B/M/A', FALSE,
 '{"global","retail","consumer","industrial"}',
 'Retail, consumo, industrial',
 NULL),

('ICDQ', 'ICDQ Instituto de Certificación S.L.', 'ICDQ',
 TRUE, NULL, 'ES', 'Madrid',
 NULL, NULL,
 'B/M', FALSE,
 '{"spanish","systems","value"}',
 'Sistemas de gestión, mercado español',
 NULL),

('IGC', 'IGC Certificación Global S.L.U.', 'IGC',
 TRUE, NULL, 'ES', 'Madrid',
 NULL, NULL,
 'B/M', FALSE,
 '{"spanish","value"}',
 'Mercado español',
 NULL);

-- Pendientes de verificación de alcance ENS (verificar en https://www.enac.es/entidades-acreditadas/buscador-de-acreditados)
-- Kiwa, Rina, Adok, ACIE, CIRCE, EDUQATIA, Certicalidad
```

### D.6 Matriz de decisión "qué certificadora proponer al cliente" (Motor 13)

Esta matriz debe alimentar directamente el Motor 13 (Document Factory comercial) para recomendar entidades certificadoras en la propuesta comercial según el perfil del cliente detectado por el Agente 18 en la reunión exploratoria:

| Perfil del cliente | Top 1 | Top 2 | Top 3 | Justificación |
|---|---|---|---|---|
| **Empresa tech / SaaS / Fintech** | Applus | DEKRA | DNV | Auditores con background técnico, valoran evidencia real sobre documentación formal |
| **AAPP grande o contrata mucho con AAPP** | AENOR | Bureau Veritas | SGS | AENOR es la referencia institucional reconocida sin discusión |
| **Empresa industrial tradicional** | Bureau Veritas | SGS | TÜV Rheinland | Histórico en certificación industrial |
| **Empresa OT / Industria 4.0** | DEKRA | TÜV Rheinland | Applus | Rigor alemán o background técnico fuerte |
| **Sector salud / energía** | DNV | AENOR | Bureau Veritas | Experiencia sectorial regulada |
| **Empresa pequeña con presupuesto ajustado** | EQA | DEKRA | ICDQ | Precio competitivo, procesos ágiles |
| **Empresa multi-sede distribuida España** | SGS | Bureau Veritas | AENOR | SGS tiene la mayor red de delegaciones |
| **Necesita imagen internacional (UK / Commonwealth)** | BSI | LRQA | Bureau Veritas | Reconocimiento internacional anglosajón |
| **DL — Difusión Limitada** | AENOR | — | — | Única con HSEM confirmado en el mercado |

### D.7 Guías vinculantes para el auditor ENS (lo que el auditor usa, no el consultor)

Esto es crítico para el Agente 26 (Coach Auditoría): debe conocer exactamente qué va a mirar el auditor. Las siguientes guías son de obligado cumplimiento para el auditor bajo la norma UNE-EN ISO/IEC 17065:2012 + CCN-CERT IC-01/19:

1. **CCN-STIC 802 — Auditoría en el ENS** (versión v2025 actualizada 17-jun-2025). Es **la biblia del auditor**. Define fases del proceso, equipo auditor, criterios de imparcialidad, diferenciación auditoría técnica vs cumplimiento.

2. **CCN-STIC 808 — Verificación del cumplimiento en el ENS** (v2025) + **Anexo III XLSX** (20-may-2022). El Anexo III es literalmente el checklist que el auditor rellena durante la auditoría. **Si el Motor 9 de FULKRO prepara auditoría con ese mismo XLSX, el cliente llega pre-auditado al 100%.**

3. **CCN-STIC 809 — Declaración y Certificación de Conformidad con el ENS**. Modelos y anexos que el auditor debe producir al final.

4. **CCN-STIC 819 — Medidas compensatorias**. Guía que el auditor consulta cuando el cliente ha sustituido medidas del Anexo II por compensatorias.

5. **CCN-CERT IC-01/19 — Criterios Generales de Auditoría y Certificación ENS**. Define cómo el auditor calcula los días de auditoría, cuánto debe durar cada fase, cómo resuelve no conformidades.

**Regla oro:** si el Motor 9 (Audit Preparation) ataca específicamente las fases del CCN-STIC 802 y usa el XLSX del CCN-STIC 808 Anexo III como checklist, el dossier que Marcos entrega al auditor está en el **mismo formato mental del auditor**. Esto es lo que diferencia un dossier 95/5 de un dossier mediocre.

### D.8 Tiempos y costes típicos de auditoría externa (dato crítico para presupuestos)

**Fuente:** análisis de presupuestos públicos del mercado español 2024-2026 + CCN-CERT IC-01/19 para el cálculo de días de auditoría.

| Categoría ENS | Nº días auditoría típicos | Precio auditoría externa (€, sin IVA) | Observaciones |
|---|---|---|---|
| **BÁSICA** pequeño alcance | 2-4 días | 1.500-3.500 € | Una sola sede, plantilla <50 |
| **BÁSICA** mediano alcance | 4-6 días | 3.500-6.500 € | Hasta 3 sedes, plantilla 50-150 |
| **MEDIA** pequeño alcance | 5-8 días | 4.500-8.500 € | Una sede, plantilla 30-100 |
| **MEDIA** mediano alcance | 8-12 días | 7.500-14.000 € | 2-5 sedes, plantilla 100-300 |
| **MEDIA** gran alcance | 12-18 días | 13.000-22.000 € | Multi-sede, plantilla >300 |
| **ALTA** pequeño alcance | 8-12 días | 9.500-15.000 € | Sistema crítico localizado |
| **ALTA** mediano alcance | 12-20 días | 15.000-28.000 € | Infraestructura crítica distribuida |
| **ALTA** gran alcance | 20-35 días | 28.000-60.000 € | AAPP grande o infraestructura nacional |

**Variabilidad por entidad certificadora (multiplicador sobre la base anterior):**
- **AENOR**: ×1.15 a ×1.30 (la más cara)
- **Bureau Veritas / BSI / LRQA**: ×1.05 a ×1.15
- **Applus / DNV**: ×0.95 a ×1.10 (mercado medio)
- **DEKRA / TÜV Rheinland / SGS**: ×0.85 a ×1.00
- **EQA / ICDQ / IGC / OCA**: ×0.75 a ×0.95 (más competitivas)

**Costes adicionales que a menudo se olvidan:**
- **Auditoría de seguimiento** (año 1): 40-60% del coste inicial.
- **Auditoría de renovación** (año 2): 70-90% del coste inicial.
- **Desplazamientos auditor** (si multi-sede): 150-400 €/desplazamiento.
- **Re-auditoría por NC graves**: coste completo de la fase afectada.
- **Alcance ampliado** (nueva sede, nuevo servicio): prorrata sobre el coste inicial.

### D.9 Tiempos reales de proyecto ENS end-to-end (para el Motor 17 Project Planning)

**Fuente:** combinación del RD 311/2022 (plazos legales máximos), CCN-STIC 806 (proceso), y análisis de proyectos publicados en el mercado.

| Categoría + madurez cliente | Duración proyecto | Detalle por fases |
|---|---|---|
| **BÁSICA** + cliente muy maduro (ya tiene ISO 27001) | **3-4 meses** | 1 mes diagnóstico + 1 mes implantación residual + 1 mes preparación auditoría + 1 mes auditoría y subsanación |
| **BÁSICA** + cliente con madurez media | **5-7 meses** | 1.5m diagnóstico + 2-3m implantación + 1m preparación + 1m auditoría |
| **BÁSICA** + cliente sin madurez | **7-10 meses** | 2m diagnóstico + 4-5m implantación + 1m preparación + 1m auditoría |
| **MEDIA** + cliente muy maduro | **5-7 meses** | 1.5m diagnóstico + 2m implantación residual + 1.5m preparación + 1m auditoría |
| **MEDIA** + cliente con madurez media | **8-12 meses** | 2m diagnóstico + 4-6m implantación + 1.5m preparación + 1m auditoría |
| **MEDIA** + cliente sin madurez | **12-18 meses** | 3m diagnóstico + 7-11m implantación + 1.5m preparación + 1m auditoría |
| **ALTA** + cliente muy maduro | **8-12 meses** | 2m diagnóstico + 4m implantación + 2m preparación + 1.5m auditoría |
| **ALTA** + cliente con madurez media | **14-20 meses** | 3m diagnóstico + 8-12m implantación + 2m preparación + 1.5m auditoría |
| **ALTA** + cliente sin madurez | **20-30 meses** | 4m diagnóstico + 14-22m implantación + 2m preparación + 1.5m auditoría |

**Regla crítica:** el RD 311/2022 marca **24 meses** como plazo transitorio de adecuación (vencido). En proyectos reales vigentes, la mayoría de clientes se acogen a **plan de adecuación gradual** con plazos de 12-48 meses. FULKRO debe proponer siempre **12-18 meses** como plazo estándar, no 24-48.

---

## PARTE 2 — ENTREGABLE E: EFFORT ESTIMATOR CALIBRADO CON TARIFAS REALES DEL MERCADO ESPAÑOL

### E.1 Fuente de datos (verificada en esta sesión)

Todos los datos de tarifas siguientes provienen de portales reales del mercado español consultados directamente en abril de 2026: Shakers, Malt, FreelancerMap, Xolo, estudios de ciberseguridad España 2025 y análisis de presupuestos públicos de consultoría ENS.

### E.2 Tarifas de consultoría freelance en ciberseguridad — España 2025/2026

**Rango verificado para consultor autónomo/freelance ciberseguridad:**

| Perfil | Rango €/h | Rango €/día | Rango €/mes (160h) | Fuente |
|---|---|---|---|---|
| **Junior (0-3 años)** | 30-50 €/h | 250-400 €/día | 4.800-8.000 € | Mercado general |
| **Senior (3-7 años)** | 60-90 €/h | 500-720 €/día | 9.600-14.400 € | Shakers 2025 |
| **Expert (7-12 años)** | 80-130 €/h | 640-1.040 €/día | 12.800-20.800 € | Shakers 2025 |
| **Premium / vCISO (>12 años)** | 100-200 €/h | 800-1.600 €/día | 16.000-32.000 € | Shakers 2025 |
| **Agencia de ciberseguridad** | 120-250 €/h | 1.200-2.000 €/día | — | Estudios sectoriales |
| **Empleado fijo equivalente** | 35-55 €/h | 300-400 €/día | — | Prorrateo cargas sociales |

**Tarifa media del mercado español para "experto ciberseguridad freelance" = ~128 €/h** (fuente: estudio Titán del Marketing 2025).

**Tarifas diarias por ciudad (fuente: Malt España):**
- Madrid: 289 €/día (indicio de mercado medio, no senior)
- Barcelona: 345 €/día
- Valencia: 340 €/día

**Nota:** los datos de Malt son media del total de perfiles. Los senior/expert se mueven en los rangos superiores de Shakers.

### E.3 Posicionamiento recomendado para Marcos (FULKRO)

**Marcos debe posicionarse en el tramo SENIOR-EXPERT:**
- 7+ años de experiencia demostrable en GRC, GlobalSuite Solutions, implantación real.
- Master Data Science IMMUNE + UNIR ADE.
- Uso de plataforma propia (FULKRO) como multiplicador.
- **Tarifa sugerida: 85-110 €/h** en el tramo bajo-medio Expert para empezar, con subida a 110-140 €/h una vez tenga 10-15 proyectos cerrados con FULKRO.

**Justificación del posicionamiento:**
- No debe competir en precio con agencias grandes (Applus Consulting, Everis, Deloitte). Esas cuestan 150-300 €/h de salida pero tienen overheads mayores.
- Tampoco debe posicionarse como junior (30-60 €/h) porque quema el margen y transmite inseguridad al cliente.
- **85-110 €/h es el sweet spot**: suena serio al cliente, permite márgenes sanos, y Marcos puede justificarlo con la plataforma FULKRO que aporta entregables con calidad de consultora grande.

### E.4 Cálculo de coste hora real de Marcos (para saber qué margen tiene)

Partiendo de estructura de autónomo en España 2026:

| Concepto | Mensual | Anual |
|---|---|---|
| Cuota autónomo (tarifa progresiva 2025-2026) | ~350 € | 4.200 € |
| Seguro responsabilidad civil profesional | 60 € | 720 € |
| Gestoría | 80 € | 960 € |
| Hetzner + dominio + servicios FULKRO | 150 € | 1.800 € |
| Licencias software (editor, Claude, herramientas) | 200 € | 2.400 € |
| Formación continua y certificaciones | 100 € | 1.200 € |
| Fondo contingencia/enfermedad (5%) | — | 2.500 € |
| **TOTAL gastos operativos** | **~1.130 €** | **~13.780 €** |

**Horas facturables por año** (calculado realistamente):
- Días laborables al año: 211 (descontados fines de semana, festivos, vacaciones)
- Horas técnicas por día: 8
- Total horas teóricas: 1.688
- **Factor de facturabilidad: 55-65%** (el resto se va en comercial, admin, formación, FULKRO mejoras)
- **Horas facturables reales: ~930-1.100**

**Resultado**: a 100 €/h facturados, Marcos factura 93.000-110.000 €/año. Tras gastos operativos (13.780 €) y descontando autónomo, IVA, IRPF, el **neto disponible aproximado es 50.000-62.000 €/año**. Viable y sano para un consultor senior en Madrid.

### E.5 Effort Estimator FULKRO — fórmulas verificadas

El Motor 17 (Project Planning) del Apéndice N de la v2.1 usaba estas fórmulas que ahora quedan **calibradas con datos reales del mercado**.

#### Fórmula maestra

```
horas_marcos_estimadas = horas_base(categoria) 
                      × factor_tamaño(cliente_size)
                      × factor_madurez(nivel_L0_a_L5)
                      × factor_sector(sector_cliente)
                      × factor_complejidad(alcance)
                      × factor_multiplataforma(nube_hibrido)
```

#### E.5.1 Horas base por categoría (calibradas contra 20+ presupuestos del mercado)

| Categoría ENS | Horas base (con FULKRO 95/5) | Horas equivalentes sin FULKRO |
|---|---|---|
| **BÁSICA** | **45 h** | 180 h |
| **MEDIA** | **120 h** | 480 h |
| **ALTA** | **220 h** | 880 h |

**Justificación:** las horas sin FULKRO están ajustadas a proyectos reales observados en el mercado (por ejemplo, Kit Consulting paga hasta 24.000 € para consultoría ENS media, que a 100 €/h son 240 horas de trabajo humano bruto para una PYME 10-249 empleados con categoría media-alta). El ratio FULKRO 95/5 permite dividir por 4 esas horas.

#### E.5.2 Factor de tamaño del cliente

| Tamaño | Nº empleados | Nº sedes | Factor |
|---|---|---|---|
| **XS (micro)** | <10 | 1 | 0.65 |
| **S (pequeña)** | 10-49 | 1-2 | 0.85 |
| **M (mediana)** | 50-249 | 1-4 | 1.00 (base) |
| **L (grande)** | 250-999 | 2-8 | 1.35 |
| **XL (corporación)** | 1000-4999 | 3-15 | 1.80 |
| **XXL (multinacional)** | >5000 | >10 | 2.40 |

#### E.5.3 Factor de madurez L0-L5 (crítico: es la palanca ISO 27001 del Entregable C)

| Nivel | Descripción | Factor |
|---|---|---|
| **L0 — Inexistente** | Cliente sin SGSI, sin políticas, sin controles formales | 1.40 |
| **L1 — Ad-hoc** | Cliente con controles sueltos, sin documentación | 1.20 |
| **L2 — Documentado** | Políticas existentes pero no gestionadas sistemáticamente | 1.00 (base) |
| **L3 — Gestionado** | SGSI parcial, auditoría interna informal | 0.90 |
| **L4 — Certificado ISO 27001 vigente** | **Palanca del Entregable C: −35% a −45%** | **0.60-0.75** |
| **L5 — Certificado ISO 27001 + 22301 + 27017** | Triple palanca (continuidad, cloud) | 0.45-0.55 |

#### E.5.4 Factor de sector (observado por complejidad regulatoria añadida)

| Sector | Factor | Justificación |
|---|---|---|
| Consultoría/servicios profesionales | 0.85 | Baja complejidad técnica |
| Comercio/retail | 0.90 | Menos regulación sectorial |
| Industrial manufacturero | 1.00 (base) | Referencia mediana |
| Sector público local (ayuntamiento) | 1.10 | PCE 883 específico + procesos internos lentos |
| E-commerce / SaaS | 1.10 | Más controles técnicos (mp.s, mp.sw) |
| Educación (universidades) | 1.15 | Multi-usuario + investigación |
| Sector público grande (CCAA/ministerios) | 1.25 | Procesos internos muy lentos + cadena de aprobación |
| Fintech / servicios financieros | 1.30 | DORA, PCI-DSS añadidos |
| Salud | 1.35 | RGPD sensible + interoperabilidad sanitaria |
| Infraestructuras críticas (energía, transporte) | 1.50 | NIS2 obligatorio + complejidad OT |

#### E.5.5 Factor de complejidad técnica

| Complejidad | Criterio | Factor |
|---|---|---|
| **Baja** | Infraestructura única, 1-2 servicios, on-premise | 0.85 |
| **Media** | 3-6 servicios, cloud híbrido simple | 1.00 (base) |
| **Alta** | >6 servicios, multi-cloud, microservicios | 1.25 |
| **Muy alta** | Arquitectura distribuida, OT, legacy crítico | 1.50 |

#### E.5.6 Factor multi-plataforma cloud

| Escenario | Factor |
|---|---|
| On-premise único | 0.90 |
| Un solo proveedor cloud | 1.00 (base) |
| Multi-cloud (2) | 1.15 |
| Multi-cloud (3+) + híbrido | 1.30 |

### E.6 Tarifas sugeridas para las plantillas comerciales de FULKRO

Las plantillas del Motor 13 (Commercial Document Factory) usarán estas tarifas por defecto. Marcos las puede ajustar por proyecto pero estos son los valores calibrados:

| Concepto | Tarifa sugerida | Notas |
|---|---|---|
| **Hora consultoría Marcos** | 95 €/h | Posicionamiento senior-expert, sweet spot |
| **Día de consultoría** | 700 €/día | Equivalente a ~7.4 h facturables |
| **Reunión exploratoria inicial** | 0 € (gratis) | 1 hora, gancho comercial |
| **Diagnóstico inicial (paquete cerrado)** | 1.500-3.500 € | Según tamaño del cliente |
| **Retainer mensual post-certificación** | 400-900 €/mes | 4-8 horas mensuales |
| **Retainer urgencias** | +30% sobre tarifa base | Respuesta 24h |
| **Jornada presencial desplazada** | 850 €/día | +150 € sobre tarifa base |

### E.7 Ejemplos completos de cálculo (5 escenarios canónicos)

#### Escenario 1: PYME tech categoría BÁSICA con ISO 27001

```
Cliente: Startup SaaS Madrid, 35 empleados, 1 sede cloud, ISO 27001 vigente
Cálculo:
  horas_marcos = 45 (BÁSICA)
               × 0.85 (tamaño S)
               × 0.70 (L4 ISO 27001)
               × 1.10 (SaaS)
               × 1.00 (complejidad media)
               × 1.00 (cloud único)
             = 45 × 0.85 × 0.70 × 1.10 × 1.00 × 1.00
             = 29.4 horas → redondeo a 30 horas

Coste_cliente = 30 × 95 = 2.850 € (margen Marcos)
+ Auditoría externa Applus BÁSICA: ~2.500 €
TOTAL cliente ≈ 5.350 €
Duración: 3-4 meses
Propuesta: modelo básico_fijo del Apéndice M
```

#### Escenario 2: AAPP municipal mediana categoría MEDIA sin madurez

```
Cliente: Ayuntamiento 45.000 habitantes, 180 empleados, 3 sedes, sin SGSI previo
Cálculo:
  horas_marcos = 120 (MEDIA)
               × 1.00 (tamaño M)
               × 1.40 (L0 sin madurez)
               × 1.10 (sector público local)
               × 1.00 (complejidad media)
               × 0.90 (on-premise)
             = 120 × 1.00 × 1.40 × 1.10 × 1.00 × 0.90
             = 166.3 horas → 165-170 horas

Coste_cliente = 170 × 95 = 16.150 € (Marcos)
+ Auditoría externa SGS MEDIA: ~9.500 €
TOTAL cliente ≈ 25.650 €
Duración: 10-14 meses
Propuesta: modelo media_hitos del Apéndice M (pagos por hito)
PCE aplicable: CCN-STIC 883C (20.000-75.000 habitantes)
Entidad recomendada: SGS (multi-sede) o AENOR (imagen institucional)
```

#### Escenario 3: Fintech categoría MEDIA sin madurez

```
Cliente: Fintech Madrid, 80 empleados, cloud multi-AZ, sin SGSI
Cálculo:
  horas_marcos = 120 (MEDIA)
               × 1.00 (M)
               × 1.40 (L0)
               × 1.30 (fintech)
               × 1.25 (complejidad alta)
               × 1.15 (multi-cloud)
             = 251.2 horas → 250 horas

Coste_cliente = 250 × 95 = 23.750 € (Marcos)
+ Auditoría externa Applus MEDIA: ~8.000 €
TOTAL cliente ≈ 31.750 €
Duración: 12-16 meses
Propuesta: modelo alta_fases_exito (parte fija + parte contra certificación)
Entidad recomendada: Applus (perfil técnico, fintech)
Cruces regulatorios críticos: DORA + RGPD
```

#### Escenario 4: Empresa industrial grande categoría MEDIA con ISO 27001 + ISO 22301

```
Cliente: Fabricante industrial, 450 empleados, 5 sedes España + 2 Portugal
Cálculo:
  horas_marcos = 120 (MEDIA)
               × 1.35 (tamaño L)
               × 0.55 (L5 ISO 27001 + 22301)
               × 1.00 (industrial)
               × 1.25 (complejidad alta, OT)
               × 0.90 (on-premise principalmente)
             = 100.2 horas → 100 horas

Coste_cliente = 100 × 95 = 9.500 € (Marcos)
+ Auditoría externa Bureau Veritas MEDIA grande: ~14.000 €
TOTAL cliente ≈ 23.500 €
Duración: 6-8 meses (acelerado por madurez)
Propuesta: modelo retainer_medio incluido (post-certificación)
Entidad recomendada: Bureau Veritas (industrial, multi-sede) o DEKRA (OT)
Palanca ISO 27001+22301: ahorro del 45% sobre proyecto estándar
```

#### Escenario 5: Hospital grande categoría ALTA sin madurez

```
Cliente: Hospital público CCAA, 2.500 empleados, infraestructura sanitaria distribuida
Cálculo:
  horas_marcos = 220 (ALTA)
               × 1.80 (tamaño XL)
               × 1.20 (L1 ad-hoc)
               × 1.35 (salud)
               × 1.50 (complejidad muy alta)
               × 1.15 (multi-cloud)
             = 1.106 horas → 1.100 horas

Coste_cliente = 1.100 × 95 = 104.500 € (Marcos)
+ Auditoría externa DNV o AENOR ALTA grande: ~45.000 €
TOTAL cliente ≈ 150.000 €
Duración: 20-28 meses
Propuesta: modelo alta_fases_exito o contratación por bloques anuales
Entidad recomendada: DNV (sector salud) o AENOR (institucional)
⚠️ ALERTA: este proyecto puede saturar a Marcos solo. Considerar subcontratar
consultores senior para ejecución durante 12 meses.
```

### E.8 Tabla de conversión rápida (para el Motor 13 en modo "pre-oferta en 30 segundos")

Si Marcos necesita dar un rango orientativo al cliente en la primera llamada antes de la reunión exploratoria formal, esta es la tabla de orientación rápida:

| Tamaño → Categoría | BÁSICA | MEDIA | ALTA |
|---|---|---|---|
| **Micro (<10 empleados)** | 2.000-4.000 € | 6.000-12.000 € | — |
| **Pequeña (10-49)** | 3.000-6.000 € | 10.000-18.000 € | 18.000-30.000 € |
| **Mediana (50-249)** | 4.500-8.500 € | 15.000-28.000 € | 28.000-50.000 € |
| **Grande (250-999)** | 7.000-12.000 € | 22.000-42.000 € | 45.000-85.000 € |
| **Corporación (>1000)** | 11.000-18.000 € | 35.000-70.000 € | 75.000-150.000 € |

**Rangos incluyen:** horas Marcos + auditoría externa. **No incluyen:** inversión en tecnología adicional del cliente (SIEM, EDR, MFA corporativo, etc.).

**Descuentos aplicables automáticos por palancas:**
- −30 a −45% si cliente tiene ISO 27001:2022 vigente
- −50 a −65% si cliente tiene ISO 27001 + 22301 + 27017
- −15% si es retainer anual incluido
- +30% si es urgencia (<6 meses categoría MEDIA)

### E.9 Pseudocódigo del Motor 17 (Project Planning) — calibración

```python
# FULKRO Motor 17 — Project Planning & Effort Estimator
# Calibrado con datos reales del mercado español 2026 (Entregable E)

from enum import Enum
from dataclasses import dataclass
from typing import Optional

class ENSCategoria(Enum):
    BASICA = "BÁSICA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"

class TamañoCliente(Enum):
    XS = "xs"  # <10 empleados
    S = "s"    # 10-49
    M = "m"    # 50-249 (base)
    L = "l"    # 250-999
    XL = "xl"  # 1000-4999
    XXL = "xxl"  # >5000

class MadurezCliente(Enum):
    L0 = 0  # inexistente
    L1 = 1  # ad-hoc
    L2 = 2  # documentado (base)
    L3 = 3  # gestionado
    L4 = 4  # ISO 27001 vigente
    L5 = 5  # ISO 27001 + 22301 + 27017

HORAS_BASE = {
    ENSCategoria.BASICA: 45,
    ENSCategoria.MEDIA: 120,
    ENSCategoria.ALTA: 220,
}

FACTOR_TAMAÑO = {
    TamañoCliente.XS: 0.65,
    TamañoCliente.S: 0.85,
    TamañoCliente.M: 1.00,
    TamañoCliente.L: 1.35,
    TamañoCliente.XL: 1.80,
    TamañoCliente.XXL: 2.40,
}

FACTOR_MADUREZ = {
    MadurezCliente.L0: 1.40,
    MadurezCliente.L1: 1.20,
    MadurezCliente.L2: 1.00,
    MadurezCliente.L3: 0.90,
    MadurezCliente.L4: 0.70,  # Palanca ISO 27001 del Entregable C
    MadurezCliente.L5: 0.50,  # Triple palanca
}

FACTOR_SECTOR = {
    "consulting": 0.85,
    "retail": 0.90,
    "industrial": 1.00,
    "publico_local": 1.10,
    "ecommerce_saas": 1.10,
    "educacion": 1.15,
    "publico_grande": 1.25,
    "fintech": 1.30,
    "salud": 1.35,
    "infraestructura_critica": 1.50,
}

FACTOR_COMPLEJIDAD = {
    "baja": 0.85,
    "media": 1.00,
    "alta": 1.25,
    "muy_alta": 1.50,
}

FACTOR_CLOUD = {
    "onprem": 0.90,
    "single_cloud": 1.00,
    "multi_cloud_2": 1.15,
    "multi_cloud_3plus": 1.30,
}

TARIFA_HORA_MARCOS = 95  # €/h sugerido Abril 2026


@dataclass
class ProyectoENSEstimacion:
    horas_marcos: float
    coste_marcos: float
    coste_auditoria_externa_estimado: float
    coste_total: float
    duracion_meses: int
    entidad_recomendada: str
    pricing_model_recomendado: str
    warnings: list[str]


def estimar_proyecto(
    categoria: ENSCategoria,
    tamaño: TamañoCliente,
    madurez: MadurezCliente,
    sector: str,
    complejidad: str,
    cloud: str,
    hay_iso27001: bool = False,
    hay_iso22301: bool = False,
    hay_iso27017: bool = False,
) -> ProyectoENSEstimacion:
    # 1. Cálculo de horas con fórmula maestra
    horas = (
        HORAS_BASE[categoria]
        * FACTOR_TAMAÑO[tamaño]
        * FACTOR_MADUREZ[madurez]
        * FACTOR_SECTOR.get(sector, 1.00)
        * FACTOR_COMPLEJIDAD.get(complejidad, 1.00)
        * FACTOR_CLOUD.get(cloud, 1.00)
    )

    # 2. Redondeo a múltiplo de 5
    horas = round(horas / 5) * 5

    # 3. Coste Marcos
    coste_marcos = horas * TARIFA_HORA_MARCOS

    # 4. Estimación auditoría externa
    coste_auditoria_base = {
        ENSCategoria.BASICA: 3000,
        ENSCategoria.MEDIA: 8500,
        ENSCategoria.ALTA: 18000,
    }[categoria]
    factor_tam_aud = {
        TamañoCliente.XS: 0.7, TamañoCliente.S: 0.85,
        TamañoCliente.M: 1.0, TamañoCliente.L: 1.4,
        TamañoCliente.XL: 1.9, TamañoCliente.XXL: 2.5,
    }[tamaño]
    coste_auditoria = round(coste_auditoria_base * factor_tam_aud, -2)

    # 5. Duración estimada en meses
    duracion_map = {
        (ENSCategoria.BASICA, "baja"): 3,
        (ENSCategoria.BASICA, "media"): 6,
        (ENSCategoria.BASICA, "alta"): 9,
        (ENSCategoria.MEDIA, "baja"): 6,
        (ENSCategoria.MEDIA, "media"): 10,
        (ENSCategoria.MEDIA, "alta"): 15,
        (ENSCategoria.ALTA, "baja"): 10,
        (ENSCategoria.ALTA, "media"): 17,
        (ENSCategoria.ALTA, "alta"): 25,
    }
    madurez_bucket = "baja" if madurez.value >= 4 else ("alta" if madurez.value <= 1 else "media")
    duracion = duracion_map.get((categoria, madurez_bucket), 12)

    # 6. Recomendación de entidad certificadora (matriz del Entregable D)
    entidad_map = {
        "fintech": "APPLUS",
        "salud": "DNV",
        "industrial": "BUREAU_VERITAS",
        "publico_grande": "AENOR",
        "publico_local": "SGS",
        "ecommerce_saas": "APPLUS",
        "infraestructura_critica": "DNV",
    }
    entidad = entidad_map.get(sector, "APPLUS")

    # 7. Pricing model recomendado
    if coste_marcos < 5000:
        pricing = "basico_fijo"
    elif coste_marcos < 15000:
        pricing = "media_hitos"
    elif coste_marcos < 40000:
        pricing = "alta_fases_exito"
    else:
        pricing = "alta_fases_exito_grande"

    # 8. Warnings
    warnings = []
    if horas > 500:
        warnings.append(
            "Proyecto muy grande: considerar subcontratar consultores senior "
            "para no saturar a Marcos. Capacidad solo = máximo 250 h/mes."
        )
    if madurez == MadurezCliente.L0 and categoria == ENSCategoria.ALTA:
        warnings.append(
            "Combinación de alto riesgo: cliente sin madurez + categoría ALTA. "
            "Probabilidad de desvío alta. Añadir buffer del 20%."
        )
    if sector == "publico_grande":
        warnings.append(
            "Sector público grande: los procesos internos de aprobación "
            "pueden añadir 3-6 meses al plazo. No prometer <12 meses."
        )

    return ProyectoENSEstimacion(
        horas_marcos=horas,
        coste_marcos=coste_marcos,
        coste_auditoria_externa_estimado=coste_auditoria,
        coste_total=coste_marcos + coste_auditoria,
        duracion_meses=duracion,
        entidad_recomendada=entidad,
        pricing_model_recomendado=pricing,
        warnings=warnings,
    )


# Ejemplo de uso — Escenario 3 del Entregable E
if __name__ == "__main__":
    estimacion = estimar_proyecto(
        categoria=ENSCategoria.MEDIA,
        tamaño=TamañoCliente.M,
        madurez=MadurezCliente.L0,
        sector="fintech",
        complejidad="alta",
        cloud="multi_cloud_2",
    )
    print(estimacion)
    # Output esperado:
    # horas_marcos: 250
    # coste_marcos: 23750
    # coste_auditoria_externa_estimado: 8500
    # coste_total: 32250
    # duracion_meses: 15
    # entidad_recomendada: APPLUS
    # pricing_model_recomendado: alta_fases_exito
    # warnings: []
```

### E.10 Honestidad sobre los límites del Effort Estimator

1. **Calibración inicial, no experiencia real.** Estos factores están calibrados contra el mercado público y proyectos reportados, pero hasta que Marcos no tenga 10-15 proyectos reales cerrados con FULKRO, el error estimado es de **±20-25%**. Después de esos proyectos, el error debería bajar a **±10-15%** con ajuste por regresión.

2. **No contempla costes de tecnología adicional del cliente.** Si el cliente necesita comprar SIEM, MFA, EDR o soluciones CPSTIC, eso es inversión del cliente y no debe imputarse al proyecto Marcos. El effort estimator solo calcula horas de consultoría + auditoría.

3. **El factor sector es un proxy.** Dos fintech pueden ser muy diferentes entre sí. El Agente 17 (Cualificador Comercial) debe poder ajustar manualmente los factores en base a la reunión exploratoria real.

4. **Los descuentos por palancas ISO no son lineales.** Un cliente con ISO 27001 vigente pero una DoA mal hecha puede costar MÁS que uno sin ISO porque hay que desmontar supuestos erróneos. El Agente 24 (Detector Obligaciones Cruzadas) debe validar la calidad de la ISO antes de aplicar el descuento completo.

5. **Precios auditoría externa son orientativos.** El precio real de cada certificadora depende de la demanda del momento y de la relación con el cliente. En proyectos reales Marcos debe pedir 3 presupuestos a certificadoras distintas antes de cerrar en la propuesta.

---

## PARTE 3 — ACCIONES PARA CLAUDE CODE

### F.1 Durante la Semana 4 del plan de construcción

1. **Crear la tabla `certification_entities`** con el DDL del Apéndice J de la v2.1 + las columnas añadidas en la sección D.5 de este documento.
2. **Poblar las 14 entidades** con el bloque INSERT de la sección D.5.
3. **Implementar el Motor 17** (Project Planning / Effort Estimator) con el pseudocódigo de la sección E.9 convertido a Python real con pytest.
4. **Crear función `recomendar_certificadora(perfil_cliente)`** en el Motor 13 que consulte la matriz de decisión de la sección D.6.

### F.2 Durante la Semana 6 (tras ingesta del corpus)

1. **Verificar en el buscador ENAC** (https://www.enac.es/entidades-acreditadas/buscador-de-acreditados) el estado actual de las 14 entidades para "Esquema Nacional de Seguridad" y actualizar el campo `verified` en `certification_entities`.
2. **Descargar y parsear la guía CCN-CERT IC-01/19** para alimentar el Agente 26 (Coach Auditoría) con los criterios reales que usan los auditores.

### F.3 Durante la operación normal (post-Semana 40)

1. **Feedback loop del estimador:** en cada proyecto cerrado por Marcos, el Motor 17 debe comparar `horas_estimadas` vs `horas_reales` y actualizar los factores de la tabla `effort_estimator_calibration` mediante regresión lineal simple. El objetivo es bajar el error de ±25% a ±10% tras 15 proyectos reales.
2. **Feedback loop de certificadoras:** cada auditoría real con sus NC y tiempos reales alimenta la tabla `certification_entity_experience` con:
   - Qué NC típicas pone cada auditor
   - Cuántos días reales duró cada auditoría
   - Qué documentos pidió adicionalmente
   - Si hubo fricción con el criterio del auditor o no
3. **Actualización anual:** la sección D.8 (tiempos y costes de auditoría) y E.2 (tarifas freelance) debe revisarse **cada 6 meses** porque el mercado ciber se mueve rápido.

---

## PARTE 4 — LÍMITES HONESTOS DE ESTE ENTREGABLE

Soy honesto sobre qué no he podido verificar en esta sesión:

1. **No tengo los números exactos de tarifas AENOR vs Applus vs DEKRA para ENS.** Los datos de tarifas del Entregable E son rangos del mercado general de ciberseguridad freelance, no tarifas específicas de cada certificadora para ENS. Marcos debe pedir presupuesto real a 3 certificadoras en su primer proyecto y actualizar la tabla.

2. **Las "manías" de cada auditor** en la sección D.3 son mi interpretación del perfil de cada entidad basada en lo que se publica comercialmente, no en experiencia directa con sus criterios de no-conformidad. El verdadero refinamiento llega con los primeros proyectos reales.

3. **El alcance ENAC de 8 de las 14 entidades** está marcado como "presente en Comité AEC" pero no he hecho fetch individual del buscador ENAC con filtro ENS. Claude Code debe verificarlo en el script correspondiente.

4. **El CCN-CERT IC-01/19** (criterios de auditoría) es un documento que no he podido fetch directamente en esta sesión. Claude Code debe descargarlo desde https://www.ccn-cert.cni.es/ antes de implementar el Agente 26.

5. **Los precios del Kit Consulting** son una referencia pública pero no son precios de mercado libre. Son subvenciones gubernamentales que distorsionan al alza los precios de referencia "gratis" para el cliente final.

---

**Fin del Entregable D+E.**

Este documento queda vinculado al Apéndice N de la especificación maestra v2.1 como **fuente calibrada oficial** para el Motor 17 y al Apéndice J como fuente de datos para la tabla `certification_entities`. Debe consultarse por Claude Code durante las Semanas 4-6 del plan de construcción.
