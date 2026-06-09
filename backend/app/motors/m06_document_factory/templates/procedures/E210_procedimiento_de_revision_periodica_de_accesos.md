# DOCUMENTO E-210 — PROCEDIMIENTO DE REVISIÓN PERIÓDICA DE ACCESOS

**Operativo de la Política de Control de Accesos (E-101). Cubre la revisión periódica que el auditor pide demostrar con evidencia de los últimos 3-6 meses.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-210"
titulo: "Procedimiento de Revisión Periódica de Accesos"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-101"
---

# PROCEDIMIENTO DE REVISIÓN PERIÓDICA DE ACCESOS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-210 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Verificar periódicamente que los derechos de acceso vigentes de todas las personas usuarias siguen siendo necesarios, proporcionados y conformes al principio de mínimo privilegio, detectando y corrigiendo accesos residuales, cuentas huérfanas y acumulación de privilegios.

## 2. PERIODICIDAD

| Tipo de acceso | Frecuencia mínima de revisión |
|---|---|
| Cuentas privilegiadas (administradores, root, DBA) | Trimestral |
| Accesos a información clasificada nivel ALTO | Trimestral |
| Accesos a información clasificada nivel MEDIO | Semestral |
| Accesos generales de usuarios | Anual |
| Cuentas de servicio | Semestral |
| Cuentas de emergencia (break-glass) | Trimestral (verificar que no se han usado sin registrar) |

## 3. FLUJO OPERATIVO

| Paso | Acción | Responsable | Plazo |
|---|---|---|---|
| 1 | Generar el **listado de accesos vigentes** desde el sistema de gestión de identidades, segregado por tipo | Resp. Sistema | Inicio del ciclo |
| 2 | Distribuir el listado a cada **propietario de recurso** (Resp. Información o Resp. Servicio según el activo) | Resp. Seguridad | 2 días hábiles |
| 3 | Cada propietario **revisa y valida**: ¿este usuario necesita este acceso? ¿el nivel de privilegio es el mínimo necesario? | Propietario del recurso | 15 días hábiles |
| 4 | Los accesos marcados como **innecesarios o excesivos** se revocan o ajustan | Resp. Sistema | 5 días hábiles |
| 5 | Las **cuentas inactivas > 90 días** se deshabilitan automáticamente, salvo justificación documentada | Resp. Sistema | Automático |
| 6 | Las **cuentas huérfanas** (sin persona asociada activa) se investigan y eliminan | Resp. Sistema + Resp. Seguridad | 5 días hábiles |
| 7 | Elaborar **Acta de Revisión de Accesos** con: fecha, alcance, nº accesos revisados, nº modificados, nº revocados, nº cuentas deshabilitadas | Resp. Seguridad | 5 días tras cierre |
| 8 | Elevar el Acta al Comité de Seguridad | Resp. Seguridad | Siguiente reunión ordinaria |

## 4. INDICADORES

| Indicador | Objetivo |
|---|---|
| Revisiones ejecutadas conforme al calendario | 100% |
| Cuentas inactivas > 90 días sin justificación | 0 |
| Cuentas huérfanas detectadas y eliminadas | 100% |
| Propietarios que responden en plazo (15 días) | ≥ 90% |

---

**Documento {{ proyecto.codigo_documento_base }}-210 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
