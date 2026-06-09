# DOCUMENTO E-100 — POLÍTICA DE SEGURIDAD DE LA INFORMACIÓN (SaaS Only)

**Variante específica `saas_only`** para entidades que operan 100% sobre
servicios SaaS de terceros, sin infraestructura física propia. Selecciona
esta variante automáticamente cuando `Project.archetype = saas_only`
(SAN-D MB-17.6 · ADR-036). Marco ENS RD 311/2022 +
**CCN-STIC 823** (utilización de servicios cloud).

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-100"
titulo: "Política de Seguridad de la Información (SaaS Only)"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
arquetipo: "saas_only"
---

# POLÍTICA DE SEGURIDAD DE LA INFORMACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-100 — Versión {{ proyecto.version_actual }}**
**Variante: SaaS Only (sin infraestructura propia)**

---

## 1. ALCANCE REDUCIDO POR MODELO SaaS

{{ cliente.razon_social }} opera al 100% sobre servicios SaaS de terceros y
**no posee**:

- Infraestructura física de procesamiento (medida `mp.if Instalaciones`
  **NO aplica**)
- Equipos servidores propios (medida `mp.eq Equipos` reducida a estaciones
  de trabajo cliente)
- Comunicaciones internas dedicadas (medida `mp.com Comunicaciones`
  gestionada principalmente por el proveedor SaaS)

Esta variante de la PSI documenta formalmente la **no aplicabilidad**
de las medidas físicas y centra el SGSI en el **outsourcing seguro**.

## 2. FOCO EN OPERACIÓN EXTERNA (`op.ext`)

Medidas reforzadas para `op.ext Servicios externos`:

| Medida | Descripción |
|---|---|
| Auditoría continua proveedores | Revisión SOC 2 Type II + certificaciones ENS/ISO 27001 |
| Cláusulas contractuales | CCN-STIC 823 obligatorias en contratos SaaS críticos |
| Plan de salida | Procedimiento documentado ante cese de servicio del proveedor |
| Soberanía de datos | Cláusulas Schrems II · datos en UE · DPA conforme art.28 RGPD |
| Notificación incidentes | Compromiso del proveedor de notificar en 24h |
| Right-to-audit | Derecho contractual a auditoría anual mínima |

## 3. CONTINUIDAD OPERATIVA

- Acuerdos de nivel de servicio (SLA) documentados con cada proveedor SaaS
  crítico
- Procedimientos de continuidad ante caída de proveedor (failover, planes
  de salida, datos exportables)
- Pruebas de restauración de respaldos exportables (no solo confiar en el
  proveedor) · CCN-STIC 821

## 4. RESTO DE CLÁUSULAS GENÉRICAS

> **Nota**: el resto de la política mantiene el contenido canónico de la
> versión genérica · esta variante destaca el arquetipo SaaS Only sin
> duplicar texto base.

```
