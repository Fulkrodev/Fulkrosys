# DOCUMENTO E-209 — PROCEDIMIENTO DE PRUEBAS DE CONTINUIDAD

**Operativo de la Política de Continuidad (E-109). Complementa E-207 (Backup) y E-208 (Restauración) con pruebas completas del PCS.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-209"
titulo: "Procedimiento de Pruebas de Continuidad"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-109"
---

# PROCEDIMIENTO DE PRUEBAS DE CONTINUIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-209 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer la planificación, ejecución y documentación de las pruebas periódicas del Plan de Continuidad del Servicio (PCS) y del Plan de Recuperación ante Desastres (DRP), conforme a la medida **op.cont.3 (Pruebas periódicas)** del Anexo II del Real Decreto 311/2022.

## 2. TIPOS DE PRUEBA

| Tipo | Descripción | Impacto en producción |
|---|---|---|
| **Revisión documental** | Revisión de los planes PCS/DRP para verificar vigencia y coherencia | Ninguno |
| **Walkthrough (ejercicio de mesa)** | Recorrido paso a paso con el Equipo de Continuidad sobre un escenario simulado | Ninguno |
| **Prueba parcial técnica** | Restauración de un componente o servicio concreto en entorno aislado | Ninguno |
| **Prueba completa (failover)** | Activación de los medios alternativos y restauración íntegra del servicio | Controlado, puede haber ventana de indisponibilidad |

## 3. PERIODICIDAD MÍNIMA

| Tipo de prueba | BÁSICA | MEDIA | ALTA |
|---|---|---|---|
| Revisión documental | Anual | Semestral | Semestral |
| Walkthrough | Anual | Anual | Semestral |
| Prueba parcial técnica | Bienal | Anual | Semestral |
| Prueba completa | Bienal | Bienal | Anual |

## 4. FLUJO OPERATIVO

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Elaborar el **Plan Anual de Pruebas de Continuidad** con escenarios, calendario, participantes y criterios de éxito | Resp. Seguridad |
| 2 | Aprobar el Plan por el Comité de Seguridad | Comité |
| 3 | Comunicar a los participantes con antelación suficiente (≥ 15 días para walkthroughs, ≥ 30 días para pruebas completas) | Resp. Seguridad |
| 4 | **Definir el escenario**: tipo de disrupción simulada, servicios afectados, RTO/RPO objetivo, criterios de éxito/fracaso | Resp. Seguridad |
| 5 | **Ejecutar la prueba** conforme al escenario, cronometrando los tiempos reales de cada fase | Equipo Continuidad |
| 6 | **Medir resultados**: tiempo real de recuperación (RTR) vs RTO objetivo, punto real de recuperación vs RPO, servicios restaurados vs previstos | Resp. Seguridad |
| 7 | Elaborar **Informe de Prueba de Continuidad** con: escenario, participantes, cronología, tiempos medidos, incidencias, desviaciones, lecciones aprendidas, acciones correctivas | Resp. Seguridad |
| 8 | Presentar el informe al Comité de Seguridad | Resp. Seguridad |
| 9 | Si la prueba falla o el RTR > RTO: abrir **acción correctiva** con análisis de causa raíz y plan de mejora | Resp. Seguridad |

## 5. INDICADORES

| Indicador | Objetivo |
|---|---|
| Pruebas ejecutadas conforme al plan anual | 100% |
| RTR ≤ RTO en pruebas completas | 100% |
| Acciones correctivas cerradas en plazo | ≥ 90% |

---

**Documento {{ proyecto.codigo_documento_base }}-209 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
