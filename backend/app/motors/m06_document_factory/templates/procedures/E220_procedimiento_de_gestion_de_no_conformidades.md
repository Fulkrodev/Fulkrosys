# DOCUMENTO E-220 — PROCEDIMIENTO DE GESTIÓN DE NO CONFORMIDADES

**Complementa E-218 (Auditoría Interna). Define cómo se gestionan las NC detectadas en auditorías, revisiones e inspecciones.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-220"
titulo: "Procedimiento de Gestión de No Conformidades y Acciones Correctivas"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE GESTIÓN DE NO CONFORMIDADES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-220 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método para el registro, análisis, tratamiento, seguimiento y cierre de las no conformidades detectadas en el SGSI, ya provengan de auditorías internas, auditorías externas, revisiones por la dirección, incidentes de seguridad o cualquier otra fuente.

## 2. CLASIFICACIÓN

| Tipo | Definición | Plazo máximo de corrección |
|---|---|---|
| **NC Mayor** | Incumplimiento sistemático, ausencia total de control crítico, fallo sistémico | 90 días |
| **NC Menor** | Incumplimiento puntual, fallo aislado no crítico | 180 días |
| **Observación** | Cumplimiento formal con potencial mejora | Análisis en 90 días, acción voluntaria |
| **Oportunidad de mejora** | Recomendación sin incumplimiento | Análisis por el Comité |

## 3. FLUJO OPERATIVO

| Paso | Acción | Responsable | Plazo |
|---|---|---|---|
| 1 | Registro de la NC en el **Registro de No Conformidades** con: fuente, descripción, evidencia, clasificación, área afectada | Quien la detecta | Inmediato |
| 2 | Asignación al **responsable del área afectada** | Resp. Seguridad | 5 días hábiles |
| 3 | **Análisis de causa raíz** (5 Whys, Ishikawa u otra técnica apropiada) | Responsable del área | 15 días hábiles |
| 4 | Elaboración del **Plan de Acción Correctiva (PAC)**: acciones a emprender, responsable de cada acción, plazo, indicador de cierre, acciones preventivas para evitar recurrencia | Responsable del área | 15 días tras análisis |
| 5 | **Aprobación del PAC** | Resp. Seguridad | 5 días hábiles |
| 6 | **Ejecución** de las acciones correctivas | Responsable del área | Según PAC |
| 7 | **Verificación de eficacia**: comprobar que la NC no recurrirá. Puede incluir: revisión documental, nueva inspección, nueva auditoría parcial | Resp. Seguridad (o auditor) | 30 días tras ejecución |
| 8 | **Cierre formal** de la NC en el registro | Resp. Seguridad | Tras verificación |

## 4. ESCALADO

Las NC Mayores no cerradas en plazo se escalan al Comité de Seguridad. Las NC Mayores recurrentes (misma causa raíz detectada en dos ciclos consecutivos) se escalan a {{ cliente.organo_aprobador_politicas }}.

## 5. INDICADORES

| Indicador | Objetivo |
|---|---|
| NC Mayores cerradas en 90 días | 100% |
| NC Menores cerradas en 180 días | ≥ 90% |
| NC recurrentes (misma causa raíz en 2 ciclos) | 0 |
| PAC aprobados en plazo | 100% |

---

**Documento {{ proyecto.codigo_documento_base }}-220 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

## RESUMEN DEL BLOQUE 6A

### 9 procedimientos nuevos PRIORIDAD ALTA entregados

| ID v2.1 | Título | Medidas/requisitos cubiertos |
|---|---|---|
| **E-200** | Alta de personal | mp.per.1, mp.per.2 |
| **E-201** | Baja de personal | mp.per.1, revocación accesos |
| **E-202** | Cambio de rol | op.acc.4, anti-privilege creep |
| **E-206** | Aplicación de parches | op.exp.4 (parte parches) |
| **E-209** | Pruebas de continuidad | op.cont.3 |
| **E-210** | Revisión periódica de accesos | op.acc.4, cuentas huérfanas |
| **E-211** | Gestión de cuentas privilegiadas | op.acc.3, op.acc.4, PAM |
| **E-212** | Respuesta a brechas RGPD | RGPD art. 33-34 |
| **E-213** | Notificación de brechas a la AEPD | RGPD art. 33, sede electrónica |
| **E-219** | Revisión por la dirección | ISO 27001 cláusula 9.3 |
| **E-220** | Gestión de no conformidades | ISO 27001 cláusula 10.1-10.2 |

*(Son 11, no 9 — he metido 2 extra porque eran cortos y dependían de los anteriores.)*

### Estado de los 35 procedimientos

| Estado | Cantidad |
|---|---|
| ✅ Existentes (renumerados de F2) | 8 |
| ✅ **Nuevos en este bloque 6A** | **11** |
| 🔲 Pendientes (bloque 6B + 6C) | 16 |

**Progreso: 19/35 procedimientos completos (54%).**

### Siguiente: Bloques 6B y 6C — los 16 procedimientos restantes

Si me dices "seguimos" arranco con el segundo lote.
