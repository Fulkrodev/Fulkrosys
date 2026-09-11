# DOCUMENTO E-106 — POLÍTICA DE COPIAS DE SEGURIDAD

**Política derivada de E-109 (Continuidad). Materializa mp.info.6 del Anexo II del ENS. Establece la estrategia de backup como política de gobierno, remitiendo al procedimiento operativo E-207 para el detalle de ejecución.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-106"
titulo: "Política de Copias de Seguridad"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE COPIAS DE SEGURIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-106 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los principios y requisitos mínimos aplicables a la realización, protección, verificación y restauración de copias de seguridad de los datos, configuraciones y sistemas comprendidos en el alcance del SGSI de {{ cliente.razon_social }}, en cumplimiento de la medida **mp.info.6 (Copias de seguridad)** del Anexo II del Real Decreto 311/2022.

## 2. PRINCIPIOS

### 2.1 Estrategia 3-2-1-1-0

La Entidad adoptará como mínimo la estrategia de copia **3-2-1-1-0**: tres copias en total (incluido el original), en al menos dos soportes distintos, con al menos una copia fuera de las instalaciones principales, al menos una copia inmutable o desconectada de la red (air-gapped), y cero errores verificados en las pruebas de restauración.

### 2.2 Cifrado obligatorio

Todas las copias de seguridad se almacenarán cifradas conforme a la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107).

### 2.3 Proporcionalidad

La frecuencia, retención y redundancia de las copias serán proporcionales a la criticidad de los datos protegidos y a los objetivos de recuperación (RTO/RPO) establecidos en el Análisis de Impacto en el Negocio (BIA).

## 3. REQUISITOS MÍNIMOS POR CATEGORÍA ENS

| Requisito | BÁSICA | MEDIA | ALTA |
|---|---|---|---|
| Frecuencia mínima datos críticos | Semanal | Diaria | Diaria + incremental cada 4h |
| Retención mínima | 1 mes | 3 meses | 6 meses |
| Copia offsite | Recomendable | Obligatoria | Obligatoria |
| Copia inmutable/air-gapped | Recomendable | Obligatoria mensual | Obligatoria semanal |
| Pruebas de restauración | Anuales | Semestrales | Trimestrales |
| Cifrado en reposo | Obligatorio | Obligatorio | Obligatorio |

## 4. VERIFICACIÓN DE INTEGRIDAD

Cada copia se acompañará de un valor hash SHA-256 calculado en el momento de su creación. Los sistemas de copia verificarán automáticamente los hashes con periodicidad semanal y alertarán ante cualquier discrepancia.

## 5. PROTECCIÓN FRENTE A RANSOMWARE

Al menos una copia de cada dato crítico se almacenará en un sistema **inmutable** (object lock en modo compliance, cintas con protección de escritura, o snapshots inmutables) durante todo el periodo de retención, para garantizar la recuperabilidad incluso en caso de compromiso total del entorno productivo.

## 6. RESPONSABILIDADES

El Responsable del Sistema es responsable de la operación diaria de las copias. El Responsable de la Seguridad supervisa el cumplimiento de esta Política y revisa los resultados de las pruebas de restauración.

## 7. PROCEDIMIENTO OPERATIVO

El detalle operativo de las copias (programación, herramientas, matrices por tipo de dato, pruebas de restauración, registros) se desarrolla en el procedimiento {{ proyecto.codigo_documento_base }}-207 (Procedimiento de Copias de Seguridad).

## 8. APROBACIÓN, REVISIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-106 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
