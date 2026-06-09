# DOCUMENTO E-225 — PROCEDIMIENTO DE PRUEBAS PRE-PRODUCCIÓN

**Es el procedimiento operativo que materializa la medida mp.sw.1 (desarrollo seguro) en su tramo de validación previa al despliegue.** Define qué pruebas son obligatorias en el entorno PRE, con qué datos, durante cuánto tiempo y con qué criterios de aceptación.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-225"
titulo: "Procedimiento de Pruebas Pre-Producción"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_sistema.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-114"
medidas_ens: ["mp.sw.1", "mp.sw.2"]
---

# PROCEDIMIENTO DE PRUEBAS PRE-PRODUCCIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-225 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las pruebas obligatorias que toda nueva versión de software debe superar en el entorno de pre-producción (PRE) antes de ser candidata a despliegue en producción, junto con los criterios de aceptación, los datasets utilizables y los plazos de evaluación.

Este procedimiento desarrolla la medida **mp.sw.1 (desarrollo seguro)** del Anexo II del Real Decreto 311/2022 conforme a la guía CCN-STIC 804.

## 2. ALCANCE

Aplica al entorno PRE de toda aplicación crítica del alcance del SGSI:

- Aplicaciones internas en cualquier release.
- Configuraciones de aplicación con impacto funcional.
- Cambios de infraestructura que requieran validación con tráfico realista.
- Migraciones de datos.
- Integraciones nuevas con sistemas externos.

## 3. PRINCIPIOS

1. **PRE es isofuncional con PROD:** misma topología, mismas versiones de SO/runtime, mismo tipo y dimensionamiento proporcional de servicios.
2. **PRE no contiene datos personales reales sin anonimizar.**
3. **Pasar PRE no garantiza ausencia de defectos:** PRE es la última línea de defensa antes de PROD, no la única.
4. **Las pruebas son automatizadas en la mayor medida posible.** Lo manual se utiliza para validación funcional, exploratoria y de aceptación.

## 4. PREPARACIÓN DEL ENTORNO PRE

### 4.1. Configuración base

| Aspecto | Requisito |
|---|---|
| Plataforma | Misma que PROD (cloud, on-prem o hybrid). |
| Versiones | Mismas versiones major/minor de runtime, librerías y servicios externos. |
| Dimensionamiento | Mínimo del 25 % de la capacidad de PROD. Para pruebas de carga, escalable al 100 %. |
| Red | Segregada de PROD; tráfico sintético o tráfico productivo replicado y enmascarado. |
| Acceso | Restringido al equipo autorizado para QA, desarrollo y operaciones. |
| Datos | Sintéticos o productivos anonimizados conforme apartado 4.2. |

### 4.2. Datos de prueba

- **Generación sintética:** datasets generados con herramientas (Faker, Mimesis) con volúmenes y distribuciones representativas.
- **Anonimización de productivos:** procesos automatizados que aplican enmascaramiento, generalización, supresión y, cuando proceda, perturbación estadística. La validación de la anonimización requiere informe del DPO.
- **Datos sensibles** (categoría especial RGPD, datos financieros): nunca se trasladan a PRE en su forma original; siempre tokenizados o sintéticos.

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** la anonimización de datasets productivos requiere informe específico del DPO con verificación de no reidentificación, archivado por 6 años.
{% endif %}

## 5. CATÁLOGO DE PRUEBAS OBLIGATORIAS

### 5.1. Pruebas funcionales

- Suite de regresión automatizada con cobertura mínima del 70 % de los flujos críticos.
- Pruebas de aceptación de usuario (UAT) para cambios funcionales relevantes.
- Pruebas exploratorias dirigidas por casos de error productivos recientes.

### 5.2. Pruebas de seguridad

- **DAST** (OWASP ZAP, Burp Suite Pro, Nuclei) sobre la superficie expuesta — sin hallazgos CRÍTICOS o ALTOS abiertos.
- **Pruebas de autorización:** validar segregación de roles, IDOR, escalado horizontal y vertical.
- **Pruebas de inyección:** SQLi, XSS, command injection, SSRF, deserialization.
- **Pruebas de criptografía:** TLS configuration (testssl.sh), correcta gestión de cookies de sesión, secure headers.
- **Para releases significativas:** pentest dirigido externo o interno conforme al procedimiento {{ proyecto.codigo_documento_base }}-209.

### 5.3. Pruebas de rendimiento

- Carga base: tráfico equivalente al **percentil 95** de PROD durante 1 hora.
- Carga pico: 2× el percentil 95 durante 15 minutos.
- Estrés: hasta degradación, identificando el punto de saturación.
- Soak test (resistencia): tráfico sostenido durante 4 a 8 horas para detectar fugas de memoria o degradación.

Criterios de aceptación: latencia P95 ≤ línea base + 10 %, error rate ≤ 0,1 %, sin caída de servicios dependientes.

### 5.4. Pruebas de continuidad

- **Failover** controlado del componente afectado por el cambio (BD, balanceador, instancia).
- Verificación del **RTO** y **RPO** documentados en el BIA ({{ proyecto.codigo_documento_base }}-400).
- Para cambios CRÍTICOS, simulación de desastre regional (cloud) o de site (on-prem).

### 5.5. Pruebas de migración (si aplica)

- Migración seca con dataset representativo (mínimo 10 % del volumen productivo).
- Validación de integridad post-migración (checksum por tabla, conteos, muestreo de datos).
- Cronometraje real para confirmar que la ventana de migración prevista es viable.
- Plan de rollback probado.

### 5.6. Pruebas de privacidad

- Verificación de que los **derechos ARCO+** (acceso, rectificación, cancelación, oposición, portabilidad, limitación) funcionan tras el cambio.
- Verificación de que los **plazos de retención** se respetan.
- Validación de que el **consentimiento** se solicita y registra correctamente cuando aplica.

## 6. FLUJO OPERATIVO

### Fase 1 — Despliegue del candidato a PRE

**Responsable:** Equipo de Operaciones.

1. Despliegue automatizado del artefacto firmado conforme a {{ proyecto.codigo_documento_base }}-224.
2. Verificación de smoke tests post-despliegue.
3. Notificación al equipo de QA de inicio del periodo de pruebas.

### Fase 2 — Ejecución de pruebas

**Responsable:** Equipo de QA con apoyo del equipo de Seguridad.

4. Lanzamiento del **paquete de pruebas obligatorias** del apartado 5.
5. Periodo mínimo de pruebas:

| Categoría del cambio | Tiempo mínimo en PRE |
|---|---|
| Estándar bajo impacto | 24 horas |
| Estándar alto impacto | 3 días naturales |
| CRÍTICO | 5 días naturales |
| EMERGENCIA | 4 horas (justificadas, con riesgo asumido) |

6. Documentación continua de hallazgos en el sistema de gestión de defectos.

### Fase 3 — Análisis de resultados

**Responsable:** QA Lead + Responsable de la Seguridad.

7. Clasificación de hallazgos:
   - **Bloqueante:** impide el go-live, exige nueva build.
   - **Mayor:** despliegue solo con plan de mitigación aprobado.
   - **Menor:** se documenta y planifica para release posterior.

8. Revisión cruzada de resultados de seguridad: ningún hallazgo CRÍTICO o ALTO abierto al go-live.

### Fase 4 — Acta de aceptación

**Responsable:** QA Lead, Responsable de la Seguridad y propietario funcional.

9. Cumplimentación del **registro R-225 — Acta de Aceptación PRE** con:
    - Identificador de la versión candidata.
    - Pruebas ejecutadas y resultados.
    - Hallazgos abiertos y plan de tratamiento.
    - Aprobaciones (firmas electrónicas).
    - Recomendación: GO / NO-GO / GO CONDICIONAL.

10. Si recomendación es GO o GO CONDICIONAL, la versión queda candidata a despliegue conforme a {{ proyecto.codigo_documento_base }}-224.

### Fase 5 — Limpieza

11. Tras el go-live, los datos de PRE se rotan o eliminan conforme a la política de retención del entorno (máximo 90 días).
12. Las versiones intermedias se archivan en el repositorio de artefactos durante 12 meses.

## 7. INTEGRACIÓN CON OTROS PROCEDIMIENTOS

| Procedimiento | Relación |
|---|---|
| {{ proyecto.codigo_documento_base }}-224 (Despliegue) | PRE es prerrequisito para PROD. |
| {{ proyecto.codigo_documento_base }}-205 (Vulnerabilidades) | Hallazgos DAST/SAST se canalizan al inventario de vulnerabilidades. |
| {{ proyecto.codigo_documento_base }}-209 (Pruebas de Continuidad) | Las pruebas de failover en PRE alimentan los informes BCP. |
| {{ proyecto.codigo_documento_base }}-203 (Cambios) | El acta R-225 es input al CAB. |

## 8. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| R-225 | Acta de Aceptación PRE | 3 años |
| R-225.A | Resultados de pruebas automatizadas | 12 meses |
| R-225.B | Informe DAST / SAST | 24 meses |
| R-225.C | Informe de rendimiento y carga | 24 meses |

## 9. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| Cobertura de regresión automatizada | flujos críticos cubiertos / total | ≥ 70 % |
| Tasa de defectos detectados en PRE | defectos PRE / (defectos PRE + defectos PROD) | ≥ 80 % |
| Tiempo medio de pruebas (cambios estándar) | media horas | ≤ 48 |
| % releases con DAST clean | releases sin hallazgos crit/high / total | 100 % |
| % cambios con plan de rollback probado | con rollback probado / total CRITICOS | 100 % |

## 10. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Cambien las herramientas de prueba estandarizadas.
- Se incorporen nuevas obligaciones regulatorias (RGPD, NIS2, DORA).
- Se modifique mp.sw.1 en CCN-STIC 804.
- Se detecten patrones de defectos productivos no capturados en PRE.

Responsabilidad: **Responsable del Sistema** + **QA Lead**, con aprobación del **Responsable de la Seguridad**.
