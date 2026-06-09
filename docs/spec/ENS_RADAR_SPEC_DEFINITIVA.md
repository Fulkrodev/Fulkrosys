# ENS Radar — Especificación Definitiva v1.0

**Documento de referencia técnica y estratégica**
Autor: Marcos Mata (Fulkro) · Asistencia: Claude
Fecha: 25 de mayo de 2026
Marco normativo: RD 311/2022 + jurisprudencia consolidada 2025

---

## Cómo leer este documento

Este no es un plan de sprint. Es la **especificación del norte** del sistema: cómo debería ser el ENS Radar al 100% si tuvieras tiempo y dinero infinitos. Cada versión que construyas debe poder justificarse como progreso hacia esta especificación. La priorización temporal está al final, en el apartado de Roadmap.

---

## Tabla de contenidos

1. [Visión rectora](#1-visión-rectora)
2. [Marco jurisprudencial 2025–2026](#2-marco-jurisprudencial-2025-2026)
3. [Arquitectura en 7 capas](#3-arquitectura-en-7-capas)
4. [Modelo de datos](#4-modelo-de-datos)
5. [SLAs operacionales](#5-slas-operacionales)
6. [Observabilidad](#6-observabilidad)
7. [Anti-features](#7-anti-features)
8. [Roadmap por versiones](#8-roadmap-por-versiones)
9. [Anexo A — Fuentes con URLs verificadas](#anexo-a--fuentes-con-urls-verificadas)
10. [Anexo B — Referencias jurídicas con links oficiales](#anexo-b--referencias-jurídicas-con-links-oficiales)
11. [Anexo C — Stack tecnológico recomendado](#anexo-c--stack-tecnológico-recomendado)

---

## 1. Visión rectora

**ENS Radar = motor de inteligencia comercial en tiempo real sobre el ecosistema de contratación pública española, que produce leads cualificados con justificación jurídica accionable.**

### Tres principios no negociables

1. **Multi-fuente nativo.** El sector público español es fragmentario por diseño: 8 plataformas independientes coexisten con PLACSP. Cubrir solo PLACSP es ceguera estructural sobre Cataluña, Euskadi, Galicia, Navarra y partes de Madrid.
2. **Habilitación previa como concepto rector.** Todo el scoring se calibra contra el régimen jurisprudencial consolidado en 2025 (Informe 25/2025 Andalucía + Resolución TARCJA 451/2025 + Resolución TACPC Canarias 131/2025), no contra la narrativa pre-2024 de "plazo de adecuación post-adjudicación".
3. **Verdad jurídica citable.** Cada lead lleva la cita normativa exacta que justifica su urgencia. Nada de "el ENS es importante", todo "art. 2.3 RD 311/2022 + tu CIF no aparece en el registro CCN + Informe 25/2025 establece exclusión previa a la solvencia".

### Métrica de éxito

El Radar es valioso por número de **leads cualificados convertibles**, no por número de leads totales. Producir 20 leads donde 5 cierran es mejor que producir 500 leads donde 5 cierran y los otros 495 generan ruido operacional.

---

## 2. Marco jurisprudencial 2025–2026

Cuatro piezas que el Radar tiene que conocer y citar:

### 2.1 RD 311/2022, de 3 de mayo

Norma rectora del ENS. Tres artículos relevantes para el Radar:

- **Art. 2.3** — Obliga a las entidades del sector privado que prestan servicios al sector público a cumplir ENS. Los pliegos **deben** contemplar los requisitos para asegurar la conformidad, incluida la cadena de suministro.
- **Art. 40** — Categorización de sistemas en BÁSICA, MEDIA, ALTA.
- **Art. 41** — Publicidad de declaraciones y certificaciones de conformidad.

**Disposición transitoria única:** desde el 5 de mayo de 2024, toda entidad privada que preste servicios al sector público debe tener sus sistemas de información conformes al ENS, independientemente de cuándo se implementaran. **El periodo transitorio acabó.**

### 2.2 Resolución TARCJA 451/2025, de 25 de julio

Tribunal Administrativo de Recursos Contractuales de la Junta de Andalucía. Sentó el criterio sustantivo: la conformidad ENS **no es solvencia**, es **habilitación empresarial o profesional** ex art. 65.2 LCSP. Implicaciones operativas:

- Se verifica **antes** de la solvencia técnica
- Su ausencia en fecha final de presentación de ofertas → **exclusión del procedimiento**
- No es prohibición de contratar (no inhabilita de por vida); simplemente impide licitar hasta certificar

### 2.3 Informe 25/2025 Comisión Consultiva de Contratación Pública de Andalucía, de 3 de noviembre

Consolidó la doctrina jurisprudencial. Confirma TARCJA 451/2025 + añade que la obligación se extiende a la cadena de suministro del adjudicatario, según resultados del análisis de riesgos. Este informe **es la cita comercial más potente** para el outbound: refleja consenso institucional, no opinión.

### 2.4 Resolución TACPC Canarias 131/2025, de 19 de agosto

Tribunal Administrativo de Contratos Públicos de la Comunidad Autónoma de Canarias. Estableció que **los pliegos sin categorización ENS son anulables**. El órgano de contratación debe especificar la categoría exigida (BÁSICA/MEDIA/ALTA). Abre dos mercados adyacentes: asesoría a órganos de contratación para corregir pliegos defectuosos, y asesoría a competidores para impugnación.

### 2.5 Síntesis para el scoring

Una empresa adjudicataria sin ENS en mayo de 2026 está necesariamente en una de tres situaciones:

| Situación | Tipo de lead | Acción Radar |
|---|---|---|
| El pliego no exigía ENS porque el objeto no requiere sistemas de información | Lead frío | Descartar |
| El órgano de contratación incumplió el art. 2.3 y la empresa lo aprovechó | Lead ardiendo + impugnable | Tier 1 |
| La empresa tiene declaración BÁSICA pero le piden MEDIA/ALTA | Lead caliente | Tier 3 |

---

## 3. Arquitectura en 7 capas

```
┌─────────────────────────────────────────────────────────────────┐
│  Capa G:  Outbound asistido + Feedback loop                     │
├─────────────────────────────────────────────────────────────────┤
│  Capa F:  Detección de oportunidades adyacentes                 │
├─────────────────────────────────────────────────────────────────┤
│  Capa E:  Scoring 5 criterios + Tiering 7 niveles               │
├─────────────────────────────────────────────────────────────────┤
│  Capa D:  Cruce / Enriquecimiento (CCN, eInforma, BORME, TARC)  │
├─────────────────────────────────────────────────────────────────┤
│  Capa C:  Detección ENS (regex + LLM inferencia art. 2.3)       │
├─────────────────────────────────────────────────────────────────┤
│  Capa B:  Normalización + Resolución de identidad CIF↔nombre    │
├─────────────────────────────────────────────────────────────────┤
│  Capa A:  Ingesta multifuente (PLACSP + 7 plataformas + BOE)    │
└─────────────────────────────────────────────────────────────────┘
```

### Capa A — Ingesta multifuente

La capa que más te falta hoy y la más crítica para escalar fuera de una única plataforma. Detalle por fuente en [Anexo A](#anexo-a--fuentes-con-urls-verificadas).

**Resumen de cobertura:**

| Fuente | Cobertura geográfica | Fuera de PLACSP |
|---|---|---|
| PLACSP | AGE + mayoría EELL + CCAA delegantes | — (es PLACSP) |
| TED | Contratos UE >143k servicios / >221k otros / >5.5M obras | Complementario |
| Cataluña (PSCP) | Generalitat + entes locales catalanes + universidades | **Sí** |
| Euskadi (KPE/KontratazioA) | Gobierno Vasco + diputaciones forales + entes locales | **Sí** |
| Galicia (Contratos Públicos de Galicia) | Xunta + sector público autonómico + EELL adheridas | **Sí** |
| Madrid (Portal Comunidad de Madrid) | Comunidad + Ayuntamiento de Madrid + organismos | **Parcial** |
| Navarra (Portal de Contratación) | Comunidad Foral + entes locales navarros | **Sí** |
| La Rioja | Publica en PLACSP, portal de consulta propio | No (delega) |
| BOE + BORME | Cambios societarios, anulaciones | Complementario |

**Detalles críticos que se suelen olvidar:**

- **Un anuncio TED = N adjudicaciones PLACSP (lotes).** Hay que expandir lotes en ingesta o tendrás cobertura falsa: un contrato dividido en 5 lotes aparece como 1 anuncio en TED y 5 en PLACSP.
- **Cataluña / Euskadi / Galicia publican bidireccionalmente con PLACSP** según el art. 347.3 LCSP, pero con desfase de 24-72 h. Para `vence_pronto_oferta` no puedes esperar el desfase; tienes que ir directamente a la fuente autonómica.
- **Boletines oficiales autonómicos** (DOG Galicia, DOGC Cataluña, BOPV Euskadi, BOCM Madrid, BON Navarra) publican anuncios cuando la plataforma falla o como fallback legal. Ingesta secundaria de respaldo.
- **Diputaciones forales vascas** (Álava, Bizkaia, Gipuzkoa) tienen perfiles de contratante propios además del KPE. Tres fuentes adicionales en Euskadi.

### Capa B — Normalización + resolución de identidad

Schema unificado de tender (campos clave en [§4 Modelo de datos](#4-modelo-de-datos)).

**Resolución CIF ↔ razón social — la cascada correcta** (esto resuelve el problema actual de `SIN_CIF_*`):

1. **AEAT** — Consulta CIF/NIF a la Sede Electrónica. Gratuita, oficial, pero rate-limited.
2. **Registro Mercantil Central / BORME** — Gratuito, batch processing posible vía descarga BOE.
3. **Informa D&B / eInforma** — Pago, completísimo, incluye CNAE, plantilla, facturación, decisores.
4. **Si fallan los 3 → drop el lead, NO inventar `SIN_CIF_*`.**

Detrás de cada drop debería quedar una entrada en `DiscardedCompany` con motivo claro, para auditoría y futura recuperación cuando mejore enrichment.

### Capa C — Detección ENS en el pliego

La pieza más infravalorada. Tu sistema actual solo detecta cuando aparece **explícito** en pliego. El RD 311/2022 art. 2.3 obliga aunque el pliego no lo mencione. Doble detector en paralelo:

**Detector 1 — Regex / keyword search.** Términos a buscar en pliegos (PCAP + PPT):

- "ENS", "E.N.S."
- "Esquema Nacional de Seguridad"
- "RD 311/2022", "Real Decreto 311/2022", "311/2022"
- "conformidad ENS", "declaración de conformidad", "certificación ENS"
- "categoría básica", "categoría media", "categoría alta" (con "seguridad sistemas información" cerca)
- "anexo II RD 311/2022"
- "CCN-STIC"
- "habilitación seguridad información"
- "art. 65.2 LCSP" (cuando el pliego invoca habilitación profesional)

**Detector 2 — LLM inference layer.** Para cada tender sin match regex, prompt al LLM:

> Lee el objeto de este contrato: [texto del objeto + PPT extractado].
> CPV principal: [código + descripción].
> Comprador: [organismo + naturaleza].
> Pregunta: ¿el adjudicatario necesita usar sistemas de información para tratar datos del comprador o prestar servicios al comprador en virtud del Art. 2.3 RD 311/2022?
> Responde JSON: {exige_ens: SI|NO, categoria_estimada: BÁSICA|MEDIA|ALTA|null, razon: string}

**Whitelist CPV que casi siempre dispara ENS:**

| Familia CPV | Descripción | ENS típico |
|---|---|---|
| 48xxxxxx | Paquetes software, sistemas información | Obligación clara |
| 72xxxxxx | Servicios IT, consultoría, desarrollo | Obligación clara |
| 79xxxxxx (parcial) | Servicios para empresas (RRHH digital, formación digital, gestión documental) | Frecuente |
| 80xxxxxx | Educación con plataforma digital | Frecuente |
| 85xxxxxx | Sanidad y servicios sociales (datos sensibles) | MEDIA o ALTA |
| 92xxxxxx (parcial) | Cultura con archivo digital | Frecuente |

El detector LLM aumenta el corpus ENS detectado entre un 30% y un 50% respecto a solo-explícito.

### Capa D — Cruce / enriquecimiento

**CCN sync (diario, crítico).**

- Lista de **empresas certificadas en ENS** → flag `company.is_ens_certified` + nivel + fecha caducidad
- Lista de **entidades del sector público certificadas** → flag `organismo.ens_certified` (señal de que el comprador exige ENS por coherencia normativa)

URL: https://ens.ccn.cni.es/es/certificacion (ver Anexo A para listados específicos).

**eInforma sync (semanal).**

- Provincia, CCAA, CNAE principal y secundarios
- Plantilla (filtro PYME real: 10-250 empleados)
- Facturación (PYME real: 2-50M €)
- Capital social
- Decisores: CEO, CFO, CIO, CISO
- Permite tier de outbound según decisor disponible

**BORME alerts (diario).**

- Constituciones, disoluciones, fusiones, ampliaciones de capital, cambios de control
- Una empresa vendida a multinacional pierde "fit PYME"
- Una matriz que se desdobla en filial → la filial puede ser nuevo lead independiente

**TARC scraping (semanal).**

Tribunales Administrativos de Recursos Contractuales (TACRC estatal + 17 autonómicos). Filtrar resoluciones por "ENS" como motivo de recurso o exclusión. Cuando aparece "Empresa X excluida por no acreditar ENS":

- Empresa X es lead urgentísimo (sabes que necesita certificación AHORA)
- Otros licitadores en el mismo pliego pueden estar en la misma situación
- Es señal de mercado: ese sector / órgano de contratación está aplicando el shift

**CCN guías STIC monitoring (semanal).**

El CCN publica actualizaciones de guías STIC que cambian requisitos técnicos. Monitorizar `ens.ccn.cni.es` y `ccn-cert.cni.es` te da:

- Alertas a clientes certificados existentes ("hay nueva guía, necesitáis ajustar")
- Justificación adicional para outbound ("el panorama normativo se mueve")

### Capa E — Scoring 5 criterios + Tiering 7 niveles

**Criterios (intersección AND, no suma ponderada):**

- **C1** — Empresa con actividad en pliegos ENS (abiertos O adjudicados últimos 12 meses)
- **C2** — Pliego exige ENS (explícito O inferido por LLM)
- **C3** — Empresa NO en registro CCN, o con certificado caducado
- **C4** — Pattern: ≥2 adjudicaciones en 12 meses O ≥1 licitación abierta en plazo
- **C5** — Importe en sweet spot 60.000–500.000 € (PYME-fit comercial)

> **Nota sobre C4:** la formulación estricta original "reincidente rechazada por no tener ENS" es **incapturable** desde PLACSP, porque `participations.rol` en datos CODICE solo contiene "adjudicatario" (los licitadores perdedores no se publican). El proxy "≥2 adjudicaciones en sweet spot" es jurídicamente distinto pero **comercialmente más interesante**: capta empresas que repetidamente GANAN contratos ENS sin estar certificadas (acumulan exposición a impugnación, no rechazo histórico).

**Tiering (orden de prioridad operativa):**

| Tier | Criterio | Mensaje outbound | Acción |
|---|---|---|---|
| `vence_pronto_oferta` | C1 ∧ C2 ∧ C3 + licitación abierta con cierre <30 días en sweet spot | "Tenéis X días para certificado o exclusión automática (Informe 25/2025)" | Push alert + llamada misma semana |
| `ardiendo_sostenido` | ≥2 adjudicaciones ENS sweet spot últimos 12m + C3 | "Pattern recurrente sin cert. Post-shift 2025, cada nueva licitación es riesgo de exclusión" | Outbound prioritario |
| `ardiendo` | 1 adjudicación ENS reciente en sweet spot + C3 | "Habéis ganado [X]. RD 311/2022 obliga desde 05/05/2024" | Outbound normal |
| `caliente` | Adjudicación en CPV ENS-relevante pero fuera sweet spot O pliego sin ENS explícito | Prospección suave, contenido educativo | Newsletter / drip |
| `renovacion_proxima` | Empresa CON cert CCN vigente, caducidad <6 meses | "Vuestro cert caduca en X meses, renovación 2-3 semanas" | Outbound dedicado |
| `tibio` | Solo licitando, sin adjudicar | Pipeline largo plazo | Drip campaign |
| `ya_certificada` | Empresa con cert CCN vigente | NO contactar como prospecto | Excluir o usar como referral source |

### Capa F — Detección de oportunidades adyacentes

Cuatro mercados que el Radar puede capturar y que están fuera del modelo actual:

**1. Cascada de subcontratación.**
El Informe 25/2025 lo establece literalmente: la obligación se extiende a la cadena de suministro según resultados del análisis de riesgos. Si una empresa grande (Indra, GMV, Atos, Telefónica Tech) es adjudicataria en pliego ENS y subcontrata a una PYME, esa PYME también necesita ENS. Detectar la red:

- Adjudicatario grande en pliego ENS → cruzar con sus subcontratistas habituales (BORME, Informa, LinkedIn)
- Cada subcontratista PYME sin ENS = lead derivado de calidad alta (ya tienen contrato activo)

**2. Renovaciones próximas.**
Los certificados ENS valen 2 años. Los ~1.000 certs CCN emitidos 2023-2024 están renovando 2025-2026. Mercado masivo. Sync diario CCN con `fecha_caducidad` → tier dedicado `renovacion_proxima`.

**3. Pliegos defectuosos impugnables.**
Tras Resolución TACPC Canarias 131/2025, los pliegos ENS sin categorización son anulables. Si el Radar detecta pliegos ENS sin categoría especificada, dos jugadas:

- Acercarte al órgano de contratación ofreciendo asesoría para corregir el pliego (mercado nuevo: AAPP como cliente)
- Acercarte a competidores del adjudicatario ofreciendo asesoría para impugnación

**4. Multinacionales europeas entrando al mercado español.**
Empresas con ISO 27001 / NIS2 pero sin ENS específico. Pueden convertir su 27001 a ENS con menos trabajo que una primera certificación desde cero. Mercado adyacente, ticket más alto.

### Capa G — Outbound asistido + Feedback loop

**Email generator (asistido, NO automático):**

- Plantilla mental con bloques personalizables (no plantilla rígida copia-pega)
- Datos inyectados automáticamente: razón social, nombre decisor, expediente concreto, organismo, importe adjudicado, fecha del pliego, cita jurisprudencial correspondiente al tier
- Marcos revisa, edita y firma cada email antes del envío. El sistema **asiste**, no automatiza.

**Estado del lead (máquina de estados):**

```
nuevo
  → contactado
    → respondido
      → discovery_scheduled
        → discovery_realizada
          → propuesta_enviada
            → en_negociacion
              → cerrado_ganado
              → cerrado_perdido
  → descartado (con motivo)
```

**Feedback humano que reaprende el modelo:**

- Marcos marca un lead como "no era cualificado" (ya tenía cert no detectado / ya no es PYME / sector inadecuado) → penaliza patrón
- Marcos marca como "ganado" → premia patrón
- Tras 50-100 marks, recalibrar thresholds automáticamente o flagear necesidad de revisión humana

---

## 4. Modelo de datos

### Tender (licitación / adjudicación)

```
Tender {
  uuid                       UUID
  source_platform            enum (PLACSP|TED|CAT|EUS|GAL|MAD|NAV|RIO|...)
  source_id                  string (id original en la fuente)
  source_url                 string

  organismo {
    nombre                   string
    nif                      string
    tipo                     enum (estatal|autonomico|local|instrumental|universitario)
    ccaa                     enum (ES17 CCAA + Ceuta + Melilla)
    provincia                string
    is_ens_certificado_ccn   bool
  }

  objeto                     text
  cpv_principal              string (codigo CPV 8 digitos)
  cpv_secundarios            string[]
  importe_estimado           decimal (€)
  importe_adjudicado         decimal (€, nullable)
  tipo_procedimiento         enum (abierto|restringido|negociado|SARA|menor|simplificado)

  fechas {
    publicacion
    fin_presentacion
    apertura
    adjudicacion
    formalizacion
  }

  estado                     enum (abierto|adjudicado|formalizado|desierto|anulado|impugnado)

  ens_requirement {
    explicit_in_pliego       bool
    inferred_by_llm          bool
    categoria_requerida      enum (BÁSICA|MEDIA|ALTA|null)
    pliego_excerpt           text (cita literal si explicit)
    inference_reasoning      text (si inferred_by_llm)
    detection_confidence     float (0-1)
  }

  participations[] {
    company_uuid             UUID
    rol                      enum (licitador|adjudicatario)
    importe_oferta           decimal (nullable)
    fecha                    date
  }

  is_ute                     bool
  ute_members                UUID[] (si is_ute)
  is_lote                    bool
  parent_tender_uuid         UUID (si lote)
  lots                       UUID[] (si tiene lotes)
}
```

### Company (empresa)

```
Company {
  uuid                       UUID
  cif                        string (verificado, NO placeholder)
  razon_social               string (verificada, NO igual al CIF)

  cnae_principal             string
  cnae_secundarios           string[]

  ubicacion {
    ccaa
    provincia
    municipio
    codigo_postal
  }

  size {
    plantilla                int (de eInforma)
    facturacion              decimal (€, de eInforma)
    capital_social           decimal (€, de BORME)
    is_pyme                  bool (derivado)
    is_micro                 bool (derivado)
  }

  estructura {
    is_ute                   bool
    ute_components           UUID[] (si es UTE)
    parent_company_uuid      UUID (si filial)
    subsidiaries             UUID[] (si matriz)
    grupo_empresarial        string (nombre del grupo, si aplica)
  }

  ens_status {
    en_registro_ccn          bool
    nivel_certificado        enum (BÁSICA|MEDIA|ALTA|null)
    fecha_certificacion      date
    fecha_caducidad          date
    auditor                  string (entidad certificadora)
    sistemas_alcance         text
    tiene_declaracion_basica bool (autoevaluación)
  }

  decision_makers[] {
    nombre
    cargo
    email                    string (de eInforma o LinkedIn)
    linkedin_url
    rol_decisional           enum (decisor|influencer|usuario)
  }

  contactability {
    email_general
    telefono
    web
    direccion_fiscal
  }
}
```

### Lead (oportunidad comercial)

```
Lead {
  uuid                       UUID
  company_uuid               UUID
  temperatura                enum (vence_pronto_oferta|ardiendo_sostenido|ardiendo|caliente|renovacion_proxima|tibio|ya_certificada)
  score                      float (0-100)

  criterios {
    c1_concursando           bool
    c2_pliego_exige_ens      bool
    c2_source                enum (explicit|inferred)
    c3_no_certificada_ccn    bool
    c4_pattern_count         int
    c4_pattern_type          enum (multi_adj|licitacion_abierta)
    c5_sweet_spot            bool
  }

  dolor_summary              text (LLM-generated, citado con expediente concreto)
  best_pliego_uuid           UUID (el que más urge para outreach)
  dias_hasta_vencimiento     int (si vence_pronto)

  jurisprudencia_citable {
    informe_25_2025          bool (siempre true en mayo 2026)
    tarcja_451_2025          bool
    canarias_131_2025        bool (si pliego defectuoso detectado)
  }

  estado_contacto            enum (state machine §3.G)
  notas_marcos               text (manual)
  feedback_score             enum (cualificado|no_cualificado|null)

  timeline[] {
    timestamp
    evento                   enum (creado|contactado|respondido|...)
    metadata
  }
}
```

---

## 5. SLAs operacionales

| Componente | Frecuencia ingesta | SLA freshness | Acción si falla |
|---|---|---|---|
| Ingesta PLACSP | 4 h | <8 h | Alert al admin |
| Ingesta TED | 6 h | <12 h | Alert |
| Ingestas autonómicas Cat/Eus/Gal | 24 h | <48 h | Email diario status |
| Ingestas autonómicas Mad/Nav | 24 h | <48 h | Email diario status |
| BORME daily sync | 24 h | <48 h | Tolerable |
| TARC scraping | Semanal | <14 días | Tolerable |
| CCN registry sync | 24 h | <48 h | Alert si >72 h |
| CCN guías STIC monitoring | Semanal | <14 días | Tolerable |
| eInforma sync | Semanal | <14 días | Tolerable (es costoso, no urgir) |
| Scoring batch | Tras cada ingesta | <1 h post-ingesta | N/A |
| Push alert Tier 1 (vence_pronto) | Tiempo real | <30 min tras detección | Critical |
| Lista lunes a Marcos | Lunes 9:00 | Fija | Critical |

---

## 6. Observabilidad

Tres familias de métricas que el dashboard debe exponer:

### 6.1 Salud del pipeline

- **Cobertura por fuente** — % de tenders ENS-relevantes capturados vs publicados (estimado por muestreo)
- **Freshness por fuente** — Lag medio entre publicación origen y aparición en sistema
- **Tasa CIF resoluble** — % leads con razón social real (no placeholder)
- **Tasa CCN cross-check exitoso** — % empresas cruzadas vs no encontradas

### 6.2 Calidad de leads

- **Distribución por tier** — debería ser pirámide invertida (mucho tibio, poco vence_pronto)
- **Precision por tier** — % leads tier X marcados como cualificados por Marcos tras revisión
- **Tiempo medio nuevo → contactado** — cuánto tarda Marcos en procesar
- **Conversion rate por tier** — % que avanzan en la máquina de estados

### 6.3 Negocio

- **Funnel completo** — leads → contactados → discovery → propuesta → cerrado
- **Revenue por tier** — qué tier convierte mejor en €
- **ROI del Radar** — € cerrado / coste operacional Radar (incluye eInforma, infra, mantenimiento)
- **Tiempo medio lead → firma** — por tier

---

## 7. Anti-features (lo que NO debe estar)

Para evitar bloat y dispersión:

- **Email automation full.** Cada email se revisa y edita a mano. La personalización es lo que cierra. El sistema asiste, no envía.
- **Multi-tenancy del Radar.** El Radar es interno tuyo. Si Fulkro pasa a SaaS, el Radar sigue siendo motor propietario, no se vende como producto.
- **Web pública del Radar / SEO funnel self-serve.** Prematuro a tu escala actual; entrega ventaja competitiva gratis; expone Fulkro de forma que viola "shown, never sold".
- **CRM completo.** No construyas un Pipedrive. El Radar termina cuando el lead pasa a discovery; lo que viene después es CRM externo (HubSpot free, Notion, o lo que sea).
- **Procurement intelligence general.** No compitas con Gobierto Contratación, Tendios, Licitaciones.es, BuscaLicitaciones. Tu nicho es ENS-PYME-consultoría. Cuanto más nicho, mejor margen.
- **Análisis sectorial macro.** Si en algún momento aparecen "tendencias del sector salud" o "evolución del mercado IT público", eso es para informes de inversor, no para el Radar operativo.

---

## 8. Roadmap por versiones

> **Principio:** cada versión debe estar justificada por convertibilidad probada en la anterior. No construir adelantado.

### V5 (actual, mayo 2026)
- Ingesta PLACSP (XML CODICE)
- Detección ENS explícita
- Scoring 4-criteria intersection (Path A cerrado 2026-05-25)
- 435 leads en corpus, distribución 314/22/99 (ardiendo/sostenido/caliente)
- 50% CIF sin resolver (`SIN_CIF_*` + razón=CIF)
- eInforma OFF

### V6 — Próximos 3 meses (Q2-Q3 2026, ~25-40 h)
**Objetivo:** convertibilidad real del corpus existente.

- [ ] Activar eInforma → desbloquea ~215 leads contactables
- [ ] Resolución AEAT/BORME → reduce SIN_CIF_*
- [ ] Detección ENS via LLM (Capa C detector 2) → +30-50% corpus
- [ ] Tier `vence_pronto_oferta` (scrapear pliegos abiertos, no solo adjudicaciones)
- [ ] Cita jurisprudencial en outbound template (Informe 25/2025 + TARCJA 451/2025)

### V7 — Q3-Q4 2026 (~30-50 h)
**Objetivo:** cobertura geográfica clave + mercados adyacentes obvios.

- [ ] Ingesta Comunidad de Madrid (sede de Marcos)
- [ ] Ingesta Galicia (Contratos Públicos de Galicia)
- [ ] Tier `renovacion_proxima` (sync CCN con fecha_caducidad)
- [ ] Detección pliegos defectuosos impugnables (Resolución Canarias 131/2025)
- [ ] BORME daily sync básico

### V8 — Q4 2026 / Q1 2027 (~50-80 h)
**Objetivo:** cobertura nacional completa + escalabilidad.

- [ ] Ingesta Cataluña (PSCP)
- [ ] Ingesta Euskadi (KPE / KontratazioA)
- [ ] Ingesta Navarra + La Rioja
- [ ] TED API integration (UE umbrales)
- [ ] Cascada subcontratación (red de subcontratistas vía BORME)
- [ ] Feedback loop reaprendizaje (penaliza/premia patrones)
- [ ] Observabilidad dashboard completo (3 familias de métricas)

### V9 — 2027+ (~40-60 h)
**Objetivo:** optimización fina + adyacentes avanzados.

- [ ] BORME alerts de cambios societarios (fusiones, ventas)
- [ ] TARC scraping resoluciones (TACRC + 17 autonómicos)
- [ ] Multinacionales europeas vía sync ISO 27001
- [ ] CCN guías STIC monitoring + alertas a certificados existentes
- [ ] Diputaciones forales vascas (Álava, Bizkaia, Gipuzkoa)
- [ ] Boletines oficiales autonómicos como ingesta secundaria

**Total Radar definitivo:** ~145-230 h de trabajo distribuido en 9-18 meses. La trampa es querer construirlo todo ya.

---

## Anexo A — Fuentes con URLs verificadas

### A.1 Plataforma de Contratación del Sector Público (PLACSP, estatal)

- **Portal principal:** https://contrataciondelestado.es/
- **Portal datos abiertos:** https://contrataciondelsectorpublico.gob.es/datosabiertos/
- **Ministerio Hacienda — datos abiertos:** https://www.hacienda.gob.es/es-ES/GobiernoAbierto/Datos%20Abiertos/Paginas/licitaciones_plataforma_contratacion.aspx
- **Especificación formato sindicación (CODICE 2.07):** https://contrataciondelsectorpublico.gob.es/datosabiertos/especificacion-sindicacion.pdf
- **Sistema de agregación de licitaciones:** https://contrataciondelestado.es/wps/portal/agregacion
- **Dataset datos.gob.es:** https://datos.gob.es/en/catalogo/e05188501-licitaciones-publicadas-en-la-plataforma-mediante-mecanismos-de-agregacion-excluyendo-los-contratos-menores
- **Sindicación principal:** Atom feed sindicación 643 = licitaciones en perfiles del contratante PLACSP (excluye contratos menores)
- **Formato:** Atom XML con CODICE 2.07
- **Granularidad:** ZIPs mensuales + feed actualizado en tiempo cuasi-real

### A.2 TED (Tenders Electronic Daily, UE)

- **Portal público:** https://ted.europa.eu/
- **API v3 root:** https://api.ted.europa.eu/
- **Swagger UI:** https://api.ted.europa.eu/swagger
- **Documentación oficial:** https://docs.ted.europa.eu/
- **eForms SDK GitHub:** https://github.com/OP-TED/eForms-SDK/
- **Bulk downloads FTP:** ftp://ted.europa.eu/ (credenciales `guest/guest`)
- **Filtros relevantes:** `country=ESP` + CPV codes para España
- **Umbrales 2026 (para servicios AGE):** 143.000 €; otros: 221.000 €; obras: 5.538.000 €

### A.3 Plataforma de Serveis de Contractació Pública de Catalunya (PSCP)

- **Portal público:** https://contractaciopublica.cat/
- **Mirror oficial:** https://contractaciopublica.gencat.cat/
- **Información institucional:** https://contractacio.gencat.cat/ca/contractar-administracio/contractacio-electronica-empreses/pscp/
- **Sobre el sistema corporativo:** https://web.gencat.cat/es/generalitat/accio-govern/contractacio-publica/recursos-empreses/sistema-corporatiu-contractacio-publica-electronica
- **Suporte AOC:** https://suport-pscp.aoc.cat/
- **Cobertura:** Generalitat de Catalunya + sector público autonómico + entes locales catalanes + universidades públicas catalanas
- **Interoperabilidad:** publica bidireccionalmente con PLACSP (art. 347.3 LCSP) con desfase 24-72 h

### A.4 Contratación Pública en Euskadi (KPE / KontratazioA)

- **Portal principal:** https://www.contratacion.euskadi.eus/
- **Portal Gobierno Vasco contratación:** https://www.euskadi.eus/gobierno-vasco/contratacion-publica-euskadi/inicio/
- **Perfil de contratante (búsqueda):** https://www.contratacion.euskadi.eus/webkpe00-kpeperfi/es/ac70cPublicidadWar/busquedaAnuncios?locale=es
- **Registro REVASCON:** https://www.contratacion.euskadi.eus/webkpe00-kpereva/es/y46aRevasconWar/consultaContratosC/filtro?locale=es
- **Junta Asesora Contratación Pública:** https://www.contratacion.euskadi.eus/informacion-general-junta-asesora/webkpe00-kpejunta/es/
- **Open Data Euskadi (general):** https://opendata.euskadi.eus/
- **Cobertura:** Gobierno Vasco + diputaciones forales + entes locales vascos + sector público institucional
- **Nota:** la nueva plataforma "KontratazioA" sustituyó a la versión anterior en marzo 2026
- **Diputaciones forales:** Álava, Bizkaia, Gipuzkoa tienen perfiles propios además del KPE

### A.5 Contratos Públicos de Galicia

- **Portal principal:** https://www.contratosdegalicia.gal/
- **Información Xunta:** https://transparencia.xunta.gal/es/tema/informacion-economica-orzamentaria-e-estatistica/contratacion-publica/plataforma
- **EidoLocal (entidades locales):** https://www.eidolocal.gal/es/nodo-integral-cpeg
- **Cobertura:** Xunta + sector público autonómico (uso obligatorio) + entidades locales adheridas (Galicia FEDER 2021-2027)
- **Operador técnico:** AMTEGA (Agencia para la Modernización Tecnológica de Galicia)

### A.6 Comunidad de Madrid

- **Portal Comunidad de Madrid:** https://contratos-publicos.comunidad.madrid/
- **Portal Ayuntamiento de Madrid:** https://contratacion.madrid.es/
- **Coordinación:** Dirección General de Patrimonio y Contratación (Subdirección General de Coordinación de la Contratación Pública)
- **Contacto institucional:** contratospublicos@madrid.org
- **Cobertura Comunidad:** Comunidad de Madrid + organismos autónomos + empresas públicas autonómicas
- **Cobertura Ayuntamiento:** Ayuntamiento de Madrid + 21 distritos + organismos autónomos municipales + empresas municipales (Plan de Contratación 2026: 1.733 contratos previstos, ~5.000 M €)
- **Nota:** parcialmente integrado en PLACSP (Ayuntamiento usa PLACSP como fuente)

### A.7 Portal de Contratación de Navarra

- **Portal principal:** https://portalcontratacion.navarra.es/es/
- **Cobertura:** Comunidad Foral de Navarra + entes locales navarros
- **Régimen:** Ley Foral 2/2018 de Contratos Públicos de Navarra (régimen propio, no se rige por LCSP estatal en todo)
- **Nota:** Navarra **NO publica en PLACSP**. Es fuente obligatoria para cobertura completa.

### A.8 La Rioja

- **Portal Gobierno La Rioja:** https://www.larioja.org/contratacion-publica/es
- **Consulta licitaciones:** https://www.larioja.org/contratacion-publica/es/licitaciones
- **Nota crítica:** **La Rioja publica sus contratos en PLACSP**. El portal propio es de consulta y trámite, pero los datos están en PLACSP. Cobertura efectiva vía PLACSP.

### A.9 CCN — Centro Criptológico Nacional (registro de certificados ENS)

- **Portal ENS:** https://ens.ccn.cni.es/
- **Página de certificación:** https://ens.ccn.cni.es/es/certificacion
- **Listado empresas certificadas (privadas):** https://ens.ccn.cni.es/es/certificacion/empresas-certificadas
- **Listado entidades sector público certificadas:** https://ens.ccn.cni.es/es/certificacion (mismo portal)
- **Entidades de certificación acreditadas (ENAC + CCN):** https://ens.ccn.cni.es/es/certificacion/entidades-de-certificacion
- **CCN-CERT (alertas, guías STIC):** https://www.ccn-cert.cni.es/
- **FAQ ENS:** https://ens.ccn.cni.es/es/que-es-el-ens/faq
- **Volumen aproximado (2026):** ~1.000+ certificados emitidos (279 sector público + 721 empresas privadas, datos públicos CCN 2023, han crecido)

### A.10 Boletines y registros oficiales

- **BOE (Boletín Oficial del Estado):** https://www.boe.es/
- **BORME (Boletín Oficial del Registro Mercantil, vía BOE):** https://www.boe.es/diario_borme/
- **AEAT (consulta CIF/NIF):** https://www.agenciatributaria.gob.es/
- **Registro Mercantil Central:** https://www.rmc.es/
- **datos.gob.es (catálogo nacional):** https://datos.gob.es/

### A.11 Juntas Consultivas de Contratación (jurisprudencia administrativa)

- **JCCP del Estado (Ministerio Hacienda):** https://www.hacienda.gob.es/es-ES/Areas%20Tematicas/Contratacion/Junta%20Consultiva%20de%20Contratacion%20Administrativa/Paginas/default.aspx
- **Comisión Consultiva Andalucía:** https://www.juntadeandalucia.es/organismos/economiahaciendayfondoseuropeos/servicios/informes-comision-consultiva.html
- **Junta Consultiva Canarias:** https://www.gobiernodecanarias.org/hacienda/contratacion/Junta_Consultiva/informes_junta_consultiva/index.html
- **Repositorio comparativo:** https://contratodeobras.com/informes-juntas-consultivas-de-contratacion-administrativa/
- **Blog seguimiento JCCPs:** https://www.crisisycontratacionpublica.org/

### A.12 Tribunales Administrativos de Recursos Contractuales (TARC)

- **TACRC (estatal):** https://www.hacienda.gob.es/es-ES/Tribunal%20Administrativo%20Central%20de%20Recursos%20Contractuales/Paginas/default.aspx
- **TARCJA (Andalucía):** integrado en portal Junta de Andalucía
- **TACPC Canarias:** integrado en portal Gobierno de Canarias
- Resto de TARC autonómicos: 17 organismos, integrados en sus respectivos portales de hacienda autonómicos

---

## Anexo B — Referencias jurídicas con links oficiales

### B.1 RD 311/2022, de 3 de mayo

- **Texto oficial BOE:** https://www.boe.es/buscar/act.php?id=BOE-A-2022-7191
- **Entrada en vigor:** 5 de mayo de 2022
- **Fin del periodo transitorio:** 5 de mayo de 2024

### B.2 Ley 9/2017, de Contratos del Sector Público (LCSP)

- **Texto oficial BOE:** https://www.boe.es/buscar/act.php?id=BOE-A-2017-12902
- **Art. 65.2** — Habilitación empresarial o profesional
- **Art. 71 ss.** — Prohibiciones de contratar (numerus clausus)
- **Art. 140.4** — Exclusión por falta de habilitación
- **Art. 347** — Plataformas de contratación

### B.3 Informe 25/2025 Comisión Consultiva de Contratación Pública de Andalucía

- **PDF oficial:** https://www.juntadeandalucia.es/sites/default/files/2025-11/Informe-25-2025.pdf
- **Fecha:** 3 de noviembre de 2025
- **Tema:** Cumplimiento de los requisitos para asegurar la conformidad de los sistemas de información con el ENS en las licitaciones públicas
- **Conclusión clave:** la conformidad ENS es **requisito de habilitación empresarial o profesional**, no de solvencia

### B.4 Resolución TARCJA 451/2025

- **Tribunal:** Tribunal Administrativo de Recursos Contractuales de la Junta de Andalucía
- **Fecha:** 25 de julio de 2025
- **Tema:** Configuración del ENS como habilitación empresarial; necesidad de verificación previa a la solvencia
- **Acceso:** disponible vía portal Junta de Andalucía (buscar en TARCJA)

### B.5 Resolución TACPC Canarias 131/2025

- **Tribunal:** Tribunal Administrativo de Contratos Públicos de la Comunidad Autónoma de Canarias
- **Fecha:** 19 de agosto de 2025
- **Tema:** Anulación de cláusula de pliego que exige ENS sin categorización
- **Acceso:** disponible vía portal Gobierno de Canarias (buscar en TACPC)

### B.6 Ley 40/2015, de Régimen Jurídico del Sector Público

- **Texto oficial BOE:** https://www.boe.es/buscar/act.php?id=BOE-A-2015-10566
- **Art. 156** — Esquema Nacional de Seguridad (definición legal)

### B.7 Guías CCN-STIC relevantes

- **CCN-STIC 809** — Declaración y Certificación de Conformidad con el ENS
- **CCN-STIC 101** — Certificación de cumplimiento STIC sistemas clasificados
- **Acceso a guías:** https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad.html

---

## Anexo C — Stack tecnológico recomendado

Coherente con tu stack actual de Fulkro (Python/FastAPI/PostgreSQL):

### C.1 Ingesta

- **Lenguaje:** Python 3.12+
- **HTTP / scraping:** `httpx` (async) + `parsel` (CSS/XPath) + `playwright` (JS-heavy)
- **XML CODICE:** `lxml` para parsing PLACSP
- **TED eForms:** SDK oficial Python (https://github.com/OP-TED/eForms-SDK)
- **Scheduling:** `APScheduler` o Celery beat (depende de si necesitas distribuir)
- **Resilience:** `tenacity` para retries + circuit breakers per fuente

### C.2 Almacenamiento

- **PostgreSQL 16** con extensiones:
  - `pgvector` para embeddings semánticos del objeto de contrato
  - `pg_trgm` para fuzzy match razón social
  - `pgaudit` para auditoría (ya lo tienes)
  - **Apache AGE** para grafo de relaciones empresariales (matriz/filial, UTE, subcontratación) — ya lo tienes
- **Object storage:** S3-compatible para PDFs de pliegos (MinIO local, o B2/R2 en producción)

### C.3 Procesamiento ENS

- **LLM detection (Capa C):** Claude API (modelo Sonnet 4 o 4.6 según necesidad de razonamiento)
- **Embeddings:** OpenAI `text-embedding-3-small` o equivalente local con `sentence-transformers`
- **Regex/keywords:** stdlib Python `re` + diccionario de términos versionado

### C.4 Cruce / enrichment

- **eInforma:** REST API oficial (de pago, contratar plan adecuado)
- **AEAT:** scraping respetuoso (rate limit propio, no SLA público)
- **CCN scraping:** httpx + parsel, diario
- **BORME:** descargas diarias del PDF + parsing (BquantFinance/licitaciones-espana puede servir de referencia open source)

### C.5 Observabilidad

- **Logs estructurados:** `structlog` (ya lo tienes en Fulkro)
- **Métricas:** Prometheus + Grafana, o alternativa simple basada en PostgreSQL si quieres minimizar dependencias
- **Alertas:** webhook → email/Telegram

### C.6 Hosting

- **Hetzner AX52 dedicado** (ya planeado) — sobrado para el Radar
- **LUKS encryption** (pendiente decisión, contexto Fulkro)
- **Proton Mail Business** para correo institucional (ya planeado)
- **Cloudflare** delante (ya planeado)

---

## Consejo final que conviene grabar a fuego

El mejor ENS Radar no es el técnicamente más completo. Es el que produce **menos leads pero más cualificados**.

Si Tier 1 te genera 5 leads/semana y conviertes 1, eso es mejor que 100 leads/semana con conversión 0,5. La presión psicológica de "tengo 200 leads que procesar" mata más deals que la falta de leads.

**Calidad > Volumen.** Toda esta especificación está al servicio de eso, no al servicio de tener un Radar impresionante de cara a inversores futuros (que llegará su momento).

---

*Documento generado el 25 de mayo de 2026. URLs verificadas en esa fecha. Marco jurisprudencial vigente: Informe 25/2025 + TARCJA 451/2025 + TACPC Canarias 131/2025. Próxima revisión sugerida: cuando aparezca nueva jurisprudencia ENS (esperable Q3-Q4 2026 según cadencia actual de las Comisiones Consultivas).*
