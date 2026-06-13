# Cómo audita un auditor acreditado por ENAC un sistema ENS de categoría MEDIA (RD 311/2022)

**Documento de referencia auditor-grade · Rúbrica de evaluación para una implantación ENS-MEDIA**
*Fuentes primarias: BOE-A-2022-7191 (RD 311/2022, texto consolidado), CCN-STIC-809, CCN-STIC-802, CCN-STIC-808, procedimiento de certificación de Entidad de Certificación acreditada por ENAC (Cámara Certifica PG-CC-ENS-032 Rev.8). Fecha: junio 2026.*

> **Numeración RD 311/2022**: auditoría = **Art. 31** (antes Art. 34 RD 3/2010); conformidad = **Art. 38**. DdA = **Art. 28.2**.

## 1. Modelo de conformidad: Declaración vs Certificación
- **BÁSICA** → Declaración de Conformidad (autoevaluación interna).
- **MEDIA y ALTA** → **Certificación de Conformidad obligatoria** por **Entidad de Certificación acreditada por ENAC** bajo **UNE-EN ISO/IEC 17065:2012** (tercera parte independiente). Art. 38.1 RD 311/2022; CCN-STIC-809 §§20-23.
- Aplica directamente a empresa privada que licita a la AAPP (caso FULKRO).

## 2. Obligación y cadencia (MEDIA)
- Auditoría **obligatoria, ordinaria al menos cada 2 años** (Art. 31.1). Extraordinaria ante cambios sustanciales (resetea el cómputo de 2 años). Prórroga 3 meses por fuerza mayor.
- Auditoría según **categoría** y, en su caso, **perfil de cumplimiento específico** (Art. 31.2) + ITS de Auditoría.
- Art. 31.6 (suspensión de operación por deficiencias graves) aplica a **ALTA**, no a MEDIA.
- **Certificado vigencia 2 años**. Entre certificaciones: auditorías internas ≥50%/año, 100%/bienio (PG-CC-ENS-032 §6.5). Falta de auditoría interna → Observación → NC Mayor si persiste.

## 3. Medidas Anexo II — 73 / 68 / 52 + refuerzos
- **73 medidas-base**: 4 `org.*` + 32 `op.*` + 37 `mp.*` (16 familias).
- Aplicables por categoría: **BÁSICA ≈52, MEDIA ≈68, ALTA 73**. (Derivan de la tabla de aplicabilidad del Anexo II; coinciden con catálogo corregido FULKRO.)
- **Refuerzos R1..R9** (novedad RD 311/2022): requisito base + refuerzos, alineados con nivel de dimensión y categoría; **no siempre acumulativos** (a veces alternativas). MEDIA = base + **R1** típico en medidas críticas; ALTA = base + R2/R3. Base legal Art. 28.1.
- **Perfil de cumplimiento específico (PCE)** Art. 30: subconjunto de medidas validado por CCN; la auditoría se hace contra el perfil.

## 4. Qué comprueba el auditor por medida
- **DdA (Declaración de Aplicabilidad)** = artefacto central. Art. 28.2: "*relación de medidas... formalizada en documento... firmado por el responsable de la seguridad*". Art. 28.3: medidas **compensatorias** justificadas documentalmente con correspondencia explícita. Anexo III §1.1.f: SGSI documentado tomando como base la DdA.
- **Evidencia objetiva por medida** (Anexo III §1.2): (a) documentación de procedimientos, (b) registro de incidentes, (c) examen/entrevista del personal afectado (conocimiento y praxis), (d) productos certificados.
- Constataciones Anexo III §1.1: política define roles/funciones; procedimientos de resolución de conflictos; diferenciación de responsabilidades; **análisis de riesgos con revisión/aprobación anual**; cumplimiento Anexo II; SGSI documentado sobre DdA.
- Cruce por medida: **política → procedimiento → registro/log → configuración real → entrevista** + contratos/SLA (op.ext/op.nub). Informe referencia **versión de DdA y nivel por dimensión por medida**.

### Clasificación de hallazgos (PG-CC-ENS-032 §5)
- **NC MENOR**: incumplimiento parcial de artículo o medida/requisito; satisfecho de forma manifiestamente mejorable; sin afectar capacidad del sistema.
- **NC MAYOR**: incumplimiento total de artículo o de un **conjunto de medidas de un dominio**; incumplimiento legal; afecta significativamente funciones esenciales; duda razonable de control eficaz; número significativo de NC menores del mismo requisito; uso indebido de la marca.
- **Observación / Oportunidad de mejora**: debilidad/vulnerabilidad sin comprometer aún.

## 5. Ciclo de auditoría (CCN-STIC-802)
1. Solicitud y revisión. 2. **Revisión documental previa** (políticas, categorización, AR, **DdA**, plan adecuación, procedimientos, informes previos, INÉS). 3. **In situ** (reunión inicial → desarrollo: registros, pruebas, observación, entrevistas → reunión final con desviaciones). 4. **Muestreo de evidencias** (profundidad hasta evidencia suficiente, Art. 31.3). 5. **Informe** (dictamen grado de cumplimiento + hallazgos conformidad/no conformidad justificados + criterios metodológicos + alcance/objetivo + ref. versión DdA y nivel por dimensión; Art. 31.4, Anexo III §2.2). 6. **PAC**. 7. **Decisión del Comité de Certificación** (separado del equipo auditor, ISO 17065) → Certificado 2 años + distintivo nº ENAC. 8. Seguimiento/renovación.
- **CCN-STIC-844 = manual INÉS** (Art. 32 informe estado seguridad), NO guía de auditoría. Guía auditoría = **CCN-STIC-802**; verificación medidas = **CCN-STIC-808**.

## 6. Documentos clave esperados (→ guía CCN-STIC)
Política de seguridad (org.1 · CCN-STIC-805/801) · Categorización 5 dimensiones D/A/I/C/T (Anexo I, Art. 40 · 803) · **Análisis de riesgos MAGERIT con revisión anual** (op.pl.1 · 804/PILAR) · **DdA firmada/versionada con refuerzos y compensatorias** (Art. 28.2/28.3 · 808) · Plan de adecuación/mejora (806) · Procedimientos operativos (org.3 · 821) · **Registro de actividad/logs + incidentes** (op.exp.8/10, op.mon · 817) · Continuidad BIA+plan+pruebas (op.cont · 810) · Servicios externos/cloud contratos+SLA (op.ext/op.nub · 823/884) · Formación/concienciación (mp.per · 454) · INÉS (Art. 32 · 844) · Conformidad+distintivos (Art. 38 · 809).

## 7. Veredicto APTO / NO APTO + PAC
| Dictamen | Definición | ¿Certifica? |
|---|---|---|
| **FAVORABLE** | Sin NC Mayor ni Menor | Sí, directo |
| **FAVORABLE CON NC** | NC menores y/o mayores | Sí, **condicionado a PAC aceptado** |
| **DESFAVORABLE** | NC Mayores no resolubles vía PAC (requiere auditoría extraordinaria in-situ) | **No** hasta superar extraordinaria |

- **No se certifica sin PAC válido** presentado (≤1 mes) con **causa raíz + acción correctiva + evidencias de cierre** (PG-CC-ENS-032 §6.8/§7).
- Mapeo grading FULKRO: **APTO** = FAVORABLE o FAVORABLE-CON-NC+PAC; **NO APTO** = DESFAVORABLE o FAVORABLE-CON-NC sin PAC. El simulacro `m09`/`m10` debería derivar `NO_APROBAR` con NC Mayor sin PAC.

## CHECKLIST AUDITOR (rúbrica de grading · MEDIA = 68 medidas, refuerzos R1)
**A. Gobierno (Anexo III §1.1):** 1) Categorización 5 dimensiones aprobada · 2) Política de seguridad con roles + resolución de conflictos · 3) Diferenciación de responsabilidades · 4) **AR MAGERIT revisado/aprobado <1 año** · 5) **DdA firmada/versionada, decisión por cada medida (aplica/no + R + nivel dim), compensatorias justificadas** · 6) SGSI documentado + plan de adecuación + mejora continua · 7) Auditorías internas ≥50%/año.
**B. org.* (4):** 8) org.1 política · 9) org.2 normativa · 10) org.3 procedimientos · 11) org.4 autorización.
**C. op.* (32):** 12) op.pl (AR, arquitectura, productos certificados, dimensionamiento) · 13) op.acc (identificación, segregación, 2FA/robustez R1) · 14) op.exp (inventario, config segura, cambios, antimalware, **registro actividad op.exp.8**, claves op.exp.10) · 15) op.ext (contratos/SLA+monitorización) · 16) op.nub (protección cloud) · 17) op.cont (BIA+plan+**pruebas**) · 18) op.mon (detección+métricas+incidentes).
**D. mp.* (37):** 19) mp.if instalaciones · 20) mp.per personal+**formación** · 21) mp.eq equipos · 22) mp.com comunicaciones (cifrado R1) · 23) mp.si soportes (cifrado+borrado) · 24) mp.sw aplicaciones (análisis vulnerabilidades) · 25) mp.info (cifrado, firma, sellos tiempo, **backups probados**, DCP) · 26) mp.s servicios (correo, web, **anti-DoS**).
**E. Veredicto:** 27) cruce evidencia↔DdA↔Anexo II por medida · 28) clasificación NC mayor/menor/observación · 29) informe completo con ref. versión DdA · 30) PAC con causa raíz+evidencias · 31) decisión Comité + Certificado 2 años + nº ENAC.

### Fuentes
- BOE-A-2022-7191 (RD 311/2022): Arts. 28, 30, 31, 38, 40; Anexo II; Anexo III.
- CCN-STIC-809 (Declaración/Certificación de Conformidad + distintivos).
- CCN-STIC-808 (Verificación del cumplimiento de las medidas / formato DdA).
- CCN-STIC-802 (Auditoría del ENS).
- PG-CC-ENS-032 Rev.7/8 (Procedimiento EC acreditada ENAC: clasificación NC, fases, dictamen, PAC, vigencia 2 años, ISO 17065).
- ENS FAQ oficial (ccn.cni.es): EC/OAT, periodicidad bienal, definición DdA.
- CCN-STIC-844 (Manual INÉS — NO es guía de auditoría).
