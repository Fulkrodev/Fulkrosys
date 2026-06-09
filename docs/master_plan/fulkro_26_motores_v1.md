# FULKRO — Master Plan de los 26 Motores v1.0

**Fecha**: 2026-04-13
**Version**: 1.0
**Estado**: Aprobado por founder
**Vigencia**: Hasta que la realidad del proyecto obligue a revision

---

## 1. Resumen ejecutivo

Este documento es el plan de ejecucion vinculante para la construccion de
los 26 motores de la plataforma FULKRO, derivado del analisis sistematico
del spec v2.1 (ENS_PLATFORM_MASTER_SPEC) y del estado real del repositorio
verificado en el Bloque 10 de auditoria. Define el orden optimo basado en
dependencias reales, no en la secuencia original del spec.

Estado actual del proyecto: 2 motores cerrados al 100% del scope alcanzable
(Motor 1 Categorization, Motor 2 MAGERIT), 1 motor parcial desactivado
(Motor 26 Backup, 584 lineas sin tests), y 23 motores stub (solo
`__init__.py`). Infraestructura DB con 82 tablas creadas, la mayoria vacias.
46 commits en main, 191/191 tests verdes. Cronograma estimado: 10-16 meses
optimista, 15-20 meses realista.

El plan se organiza en 3 fases secuenciales: Fase 1 completa los motores
foundation que desbloquean el resto (M12, M3, M26, M19). Fase 2 construye
el core ENS operativo desde diagnostico hasta evidencias mas el Copiloto LLM
(M6, M4, M5, M7, M22, M11). Fase 3 completa la plataforma con un checkpoint
de cliente piloto en el mes 8-10 tras tener ciclo completo minimo.

---

## 2. Estado actual (snapshot)

| Motor | Nombre | Estado | Dependencias del spec | Horas est. |
|---|---|---|---|---|
| M1 | Categorization Engine | COMPLETO | ninguna | -- |
| M2 | MAGERIT Risk Engine | COMPLETO | ninguna | -- |
| M3 | DdA Engine | STUB | M1 | 25-40h |
| M4 | Gap Analysis Engine | STUB | M3 | 20-30h |
| M5 | Obligations & Planning | STUB | M4, M6, M12 | 50-70h |
| M6 | Document Factory | STUB | corpus ENS | 80-120h |
| M7 | Evidence Collection | STUB | M5, M6, M12 | 20-30h |
| M8 | Pentesting & Red Team | STUB | M12, M22 | 60-90h |
| M9 | Audit Preparation | STUB | M1, M3, M5, M6, M7, M8 | 20-30h |
| M10 | Audit Simulation | STUB | M3, M7, M9 | 25-35h |
| M11 | Copiloto LLM | STUB | corpus ENS, todos (lee) | 80-120h |
| M12 | Magic Link Engine | STUB | ninguna | 25-35h |
| M13 | Commercial Doc Factory | STUB | M6, M17 | 35-50h |
| M14 | Contracts Engine | STUB | M12, M13, M15 | 25-35h |
| M15 | Billing Engine | STUB | M14 | 20-30h |
| M16 | Adaptive Onboarding | STUB | M12 | 50-70h |
| M17 | Project Planning | STUB | M19 | 25-35h |
| M18 | Communication & Reporting | STUB | M12, M20 | 15-25h |
| M19 | Project Risk Mgmt | STUB | ninguna | 20-30h |
| M20 | Collaborative Workspace | STUB | M12, M14 | 40-60h |
| M21 | Organizational Diagnosis | STUB | M16 | 25-35h |
| M22 | Technical Discovery | STUB | M16 | 35-50h |
| M23 | Retainer Management | STUB | M8, M10, M15 | 15-25h |
| M24 | IDMS Documental | STUB | M6, M7, M11, M20 | 80-120h |
| M25 | Project Lifecycle | STUB | M14, M15, M24, M26 | 15-25h |
| M26 | Backup & DR | PARCIAL-DESACTIVADO | ninguna | 8-12h |

---

## 3. Grafo de dependencias

### 3.1 Motores foundation (sin dependencias hacia atras)

- **M1 Categorization** -- COMPLETO
- **M2 MAGERIT** -- COMPLETO
- **M12 Magic Link** -- STUB, desbloquea 9 motores
- **M19 Risk Mgmt (proyecto)** -- STUB, foundation pequeno
- **M26 Backup** -- PARCIAL, deuda tecnica a cerrar

### 3.2 Cadena principal ENS

```
M1 --> M3 --> M4 --> M5 --> M7 --> M9 --> M10
 ok    DdA    Gap   Oblig  Evid  AuditP AuditS
```

Esta es la cadena critica del producto. Cada motor depende del anterior.
M6 (Document Factory) es transversal y alimenta M5, M7 y M9.

### 3.3 Cadena comercial

```
M19 --> M17 --> M13 --> M14 --> M15 --> M23
RiskP  Plann  ComDoc Contrac Billing Retain
```

Cadena independiente del pipeline ENS. Se construye en Fase 3 excepto
M19 (foundation, Fase 1) y M15 (pre-piloto, Fase 3A).

### 3.4 Cadena diagnostico

```
M16 --> M21  (Onboarding --> Diagnosis organizativo)
M16 --> M22  (Onboarding --> Discovery tecnico)
```

M22 alimenta M1, M2, M4, M5 y M8. Se construye en Fase 2.

### 3.5 Motores transversales

- **M6** Document Factory: hub documental, alimenta M5, M7, M9, M13, M24
- **M11** Copiloto LLM: lee datos de todos los motores, se construye ultimo en Fase 2
- **M18** Communication: reportes automatizados, depende de M12 y M20
- **M20** Collaborative Workspace: infraestructura colaborativa efimera
- **M24** IDMS Documental: gestor inteligente, depende de M6, M7, M11, M20
- **M25** Project Lifecycle: archivado y ciclo de vida, ultimo en construirse

### 3.6 El cuello de botella — Motor 12 Magic Link

9 motores dependen directamente de M12:
M5, M7, M8, M13, M14, M16, M18, M20, M23.

Construirlo primero genera el maximo desbloqueo del grafo de dependencias.
Cada semana de retraso en M12 retrasa 9 cadenas independientes.

---

## 4. Plan de ejecucion en 3 fases

### FASE 1 — Foundation completada (~4-6 semanas, 78-117h)

Objetivo: completar los motores foundation que quedan para desbloquear
el resto del proyecto.

| # | Motor | Nombre | Horas | Justificacion |
|---|---|---|---|---|
| 1 | M12 | Magic Link Engine | 25-35h | Desbloquea 9 motores |
| 2 | M3 | DdA Engine | 25-40h | Core ENS, M1 ya hecho |
| 3 | M26 | Backup (cerrar parcial) | 8-12h | Elimina deuda tecnica |
| 4 | M19 | Risk Mgmt (proyecto) | 20-30h | Foundation pequeno |

**Al final de Fase 1**:
- 6 motores cerrados al 100% (M1, M2, M3, M12, M19, M26)
- Magic link operativo: M1 y M2 se re-integran para cerrar gaps de firma
- Motor 3 = corazon ENS operativo (categorizacion + AR + DdA)

### FASE 2 — Core ENS operativo (~9-13 semanas, 230-335h)

Objetivo: completar el pipeline ENS desde diagnostico tecnico hasta
auditoria + el Copiloto LLM.

| # | Motor | Nombre | Horas | Dependencias cumplidas |
|---|---|---|---|---|
| 5 | M6 | Document Factory | 80-120h | Hub documental, desbloquea mucho |
| 6 | M4 | Gap Analysis | 20-30h | M3 hecho en Fase 1 |
| 7 | M5 | Obligations | 50-70h | M4, M6, M12 cumplidos |
| 8 | M7 | Evidence Vault | 20-30h | M5, M6, M12 cumplidos |
| 9 | M22 | Technical Discovery | 35-50h | Diagnostico automatizado |
| 10 | M11 | Copiloto LLM | 80-120h | Cierra gaps LLM de M1+M2+M3+... |

**Al final de Fase 2**:
- 12 motores cerrados al 100%
- Copiloto LLM operativo: re-integracion automatica de features LLM en
  M1, M2, M3, M4, M5
- Pipeline tecnico ENS completo (discovery -> categorizacion -> AR -> DdA ->
  gaps -> obligaciones -> evidencias)

### FASE 3 — Completado plataforma + Cliente piloto (~20-30 semanas, 505-750h)

Objetivo: construir motores restantes + salir al primer cliente piloto
en el mes 8-10 con ciclo completo operativo.

**Sub-fase 3A (pre-piloto, ~8-10 semanas)**:

| # | Motor | Nombre | Horas | Justificacion |
|---|---|---|---|---|
| 11 | M16 | Adaptive Onboarding | 50-70h | Necesario para cliente piloto |
| 12 | M20 | Workspace | 40-60h | Infraestructura colaborativa piloto |
| 13 | M8 | Pentesting Engine | 60-90h | Diferenciador comercial clave |
| 14 | M9 | Audit Prep Engine | 20-30h | Cierra ciclo ENS |
| 15 | M21 | Organizational Diag. | 25-35h | Completa diagnostico |
| 16 | M15 | Billing (facturacion) | 20-30h | Imprescindible para facturar al piloto |

**-> CHECKPOINT: Cliente piloto en mes 8-10 <-**

Con Fase 1 + 2 + 3A operativo, FULKRO tiene:
- Ciclo completo ENS (discovery -> AR -> DdA -> gaps -> obligaciones ->
  evidencias -> pentest -> audit prep)
- Copiloto LLM operativo
- Onboarding adaptativo
- Facturacion legal operativa
- Firma electronica (magic links)
- Documentacion firmada

**Sub-fase 3B (post-piloto, refinamiento + motores comerciales)**:

| # | Motor | Nombre | Horas |
|---|---|---|---|
| 17 | M17 | Project Planning | 25-35h |
| 18 | M13 | Commercial Doc Factory | 35-50h |
| 19 | M14 | Contracts Engine | 25-35h |
| 20 | M18 | Communication Engine | 15-25h |
| 21 | M10 | Audit Simulation | 25-35h |
| 22 | M24 | IDMS Documental avanzado | 80-120h |
| 23 | M23 | Retainer Mgmt | 15-25h |
| 24 | M25 | Project Lifecycle | 15-25h |

### Re-integracion final (2-3 semanas)

| # | Motor | Accion | Horas |
|---|---|---|---|
| 25 | M1 | Cerrar gaps (magic link + LLM) | 10-15h |
| 26 | M2 | Cerrar gaps (E-028 + LLM importador) | 10-15h |
| 27 | Transversal | Frontend + observabilidad + CI/CD + docs | 200-400h distribuido |

---

## 5. Dependencias criticas resueltas (matriz)

Tabla mostrando que gap actual del Motor 1/2 se resuelve en que fase:

| Gap actual | Motor bloqueante | Fase donde se resuelve |
|---|---|---|
| M1-G1 Asistencia LLM valoraciones | M11 Copiloto | Fase 2 |
| M1-G2 Firma E-012 magic link | M12 Magic Link | Fase 1 |
| M2-G3 LLM+RAG importador | M11 Copiloto | Fase 2 |
| M2-G6 Firma E-028 magic link | M12 Magic Link | Fase 1 |
| M2-G8 Mapping salvaguarda->Anexo II descripcion | M3 DdA con ens_measures poblado | Fase 1 |
| TODO-9 caso PILAR | Externo CCN | Queda pendiente |
| TODO-24 PILAR .mgr | Externo CCN | Queda pendiente |

---

## 6. Cronograma total estimado

| Fase | Horas | Semanas (25h/sem) | Meses |
|---|---|---|---|
| Fase 1 Foundation | 78-117h | 3-5 sem | 0.75-1.25 |
| Fase 2 Core ENS | 230-335h | 9-13 sem | 2.25-3.25 |
| Fase 3A Pre-piloto | ~215-315h | 9-13 sem | 2.25-3.25 |
| **CLIENTE PILOTO** | -- | -- | **Mes ~8-10** |
| Fase 3B Post-piloto | ~290-435h | 12-17 sem | 3.0-4.25 |
| Re-integracion + transversal | ~220-430h | 9-17 sem | 2.25-4.25 |
| **TOTAL** | **~1033-1632h** | **~42-65 sem** | **~10.5-16 meses** |

**Nota honesta**: cronograma anterior (23-26 meses) incluia buffer para
imprevistos, integracion, debugging cruzado, y refinamientos post-piloto.
El Master Plan optimista es 10-16 meses. La realidad entre ambos es
15-20 meses.

---

## 7. Decisiones arquitectonicas pre-tomadas

Decisiones del founder Marcos que aplican a TODOS los motores pendientes
(extracto de ADRs existentes):

1. **Metodologia de cierre al 100%**: cobertura honesta, tests con citas
   oficiales, RLS, soft delete por defecto, patrones M1/M2 replicados.
2. **Freeze/unfreeze**: patron para entidades "documento vivo" (ver ADR
   motor2_freeze_unfreeze_vs_versioning.md).
3. **Importacion masiva**: determinista primero, LLM+RAG diferido a Motor 11
   (ver docs/decisions/llm_ingestion_pipeline.md).
4. **Naming honesto**: nunca prometer compatibilidad con formatos externos
   sin verificacion (ver docs/limitations/pilar_export.md).
5. **Modo acelerado con paradas criticas**: bug inesperado, hallazgo
   diagnostico, migracion Alembic nueva, test critico rojo.

---

## 8. Riesgos identificados

- **Riesgo 1 — Motor 6 Document Factory (~110 plantillas)**: trabajo manual
  de ofimatica. Mitigacion: dividir en "infraestructura Motor 6" +
  "plantillas progresivas" segun necesidad real.

- **Riesgo 2 — Motor 11 Copiloto LLM**: complejidad arquitectonica alta.
  Mitigacion: ADR previo decidiendo LLM remoto/local/hybrid + RAG strategy.

- **Riesgo 3 — Dependencias externas CCN**: PILAR .mgr, caso oficial CCN.
  Mitigacion: TODOs documentados, no bloquean el proyecto.

- **Riesgo 4 — Motor 8 Pentesting con 11 herramientas**: complejidad
  orquestacion. Mitigacion: se construye despues de tener M22 Discovery.

- **Riesgo 5 — Cliente piloto con plataforma incompleta**: algunos motores
  post-piloto son criticos para operacion (M10 Audit Sim, M23 Retainer).
  Mitigacion: el cliente piloto es mes 8-10 con ciclo completo minimo,
  no con plataforma total.

---

## 9. TODOs pendientes (vinculante al plan)

Referencia a `progress/todos.md` + lista resumen:

| TODO | Descripcion | Fase |
|---|---|---|
| TODO-9 | Caso oficial CCN/PILAR | Externo, no bloqueante |
| TODO-24 | Exportacion PILAR .mgr | Externo, no bloqueante |
| TODO-M26-CIERRE | Cerrar Motor 26 (8-12h) | Fase 1 |
| TODO-22 | Historico versiones MAGERIT | Diferido a cliente piloto |
| TODO-25 | LLM ingestion pipeline | Motor 11 (Fase 2) |
| TODO-26 | Estilizar XLSX exports M2 | Diferido a cliente piloto |
| TODO-27 | Coverage exporters.py M2 | Proxima sesion housekeeping |

---

## 10. Proximo paso inmediato

**Arrancar Bloque 13 — Motor 12 (Magic Link Engine)**, primera feature
de Fase 1.

Siguiente sesion:
1. Auditoria Motor 12 (modelo, tablas, estado real)
2. Decision criptografia (JWT Ed25519 + OTP segun spec)
3. Implementacion 9 tipos de magic link
4. Tests al 100% con patrones M1/M2
5. Re-integracion cierre gaps M1-G2 + M2-G6
