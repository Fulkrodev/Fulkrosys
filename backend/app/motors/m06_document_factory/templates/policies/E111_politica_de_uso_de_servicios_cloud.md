# DOCUMENTO E-111 — POLÍTICA DE USO DE SERVICIOS CLOUD

**Política nueva. Desarrolla las medidas op.ext.1 a op.ext.4 y las especificidades del CCN-STIC 887 (Perfil de Cumplimiento Específico de Servicios Cloud) para la contratación y uso de servicios cloud.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-111"
titulo: "Política de Uso de Servicios Cloud"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE USO DE SERVICIOS CLOUD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-111 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los principios, criterios de selección, requisitos de seguridad y condiciones de uso de los servicios cloud (IaaS, PaaS, SaaS) contratados por {{ cliente.razon_social }}, garantizando que el tratamiento de información en infraestructuras de terceros cumple con las exigencias del Real Decreto 311/2022 y, en particular, con el **Perfil de Cumplimiento Específico de Servicios Cloud (CCN-STIC 887)** del Centro Criptológico Nacional.

## 2. PRINCIPIOS

### 2.1 Modelo de responsabilidad compartida

La Entidad reconoce que la seguridad en entornos cloud es una responsabilidad compartida entre el proveedor y el cliente. La distribución de responsabilidades varía según el modelo de servicio (IaaS > PaaS > SaaS) y se documentará expresamente en cada contratación.

### 2.2 Prohibición de Shadow IT

Queda **expresamente prohibida** la utilización de servicios cloud no autorizados previamente por el Responsable de la Seguridad. Todo servicio cloud utilizado para tratar información del alcance del SGSI debe estar inventariado, evaluado y aprobado.

### 2.3 Preferencia de localización EEE

Se priorizarán los proveedores que garanticen el tratamiento de la información dentro del **Espacio Económico Europeo**, evitando transferencias internacionales innecesarias.

## 3. REQUISITOS DE SEGURIDAD PARA PROVEEDORES CLOUD

### 3.1 Certificaciones exigibles

{% if proyecto.categoria_ens in ["MEDIA", "ALTA"] %}
Los servicios cloud que traten información comprendida en el alcance del SGSI deberán acreditar conformidad con el ENS en categoría igual o superior a la del sistema servido, mediante:

a) Certificado de conformidad ENS emitido por entidad acreditada por ENAC, o

b) Cumplimiento del **Perfil de Cumplimiento Específico CCN-STIC 887**, acreditado mediante auditoría independiente, o

c) Certificación equivalente reconocida (CSA STAR Level 2, SOC 2 Type II + ISO 27001 + ISO 27017 + ISO 27018) cuando las opciones anteriores no estén disponibles para el servicio concreto, previa autorización del Responsable de la Seguridad.
{% else %}
Los servicios cloud deberán disponer, como mínimo, de certificación ISO 27001 vigente y declarar su cumplimiento con las medidas de seguridad aplicables a la categoría del sistema.
{% endif %}

### 3.2 Cifrado

Los datos de la Entidad se cifrarán conforme a la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107) tanto en reposo como en tránsito. Cuando sea técnicamente viable, se exigirá que las claves de cifrado estén bajo control de la Entidad mediante mecanismos **BYOK (Bring Your Own Key)** o **HYOK (Hold Your Own Key)**.

### 3.3 Trazabilidad de accesos

El proveedor deberá proporcionar registros de acceso de su personal a las infraestructuras que alojen información de la Entidad, accesibles bajo demanda y en auditoría.

### 3.4 Plan de salida y portabilidad

Antes de la contratación se verificará la existencia de un **plan de salida documentado** que garantice la portabilidad de los datos y servicios al término de la relación, en formatos abiertos y en plazos razonables.

## 4. PROCESO DE APROBACIÓN DE NUEVOS SERVICIOS CLOUD

La incorporación de cualquier nuevo servicio cloud seguirá el siguiente flujo:

a) **Solicitud** del área funcional al Responsable de la Seguridad, indicando servicio, proveedor, tipo de información a tratar y finalidad.

b) **Evaluación de seguridad** conforme al procedimiento de evaluación de proveedores ({{ proyecto.codigo_documento_base }}-217), incluyendo el análisis del modelo de responsabilidad compartida.

c) **Aprobación o denegación** del Responsable de la Seguridad, documentada y trazable.

d) **Revisión periódica** conforme al ciclo de evaluación de proveedores.

## 5. TIPOS DE INFORMACIÓN ADMITIDOS EN CLOUD

| Nivel de clasificación (Política E-104) | Admisión en cloud | Condiciones |
|---|---|---|
| PÚBLICA | Sí | Sin restricciones especiales |
| INTERNA | Sí | Cifrado en tránsito |
| CONFIDENCIAL | Sí con autorización | Cifrado reposo + tránsito + BYOK recomendable + proveedor evaluado |
| RESTRINGIDA | Solo con autorización expresa del Comité de Seguridad | Cifrado HYOK obligatorio + localización EEE + auditoría reforzada |

## 6. MONITORIZACIÓN

El Responsable del Sistema monitorizará el uso de los servicios cloud aprobados y, cuando sea técnicamente posible, implementará herramientas CASB (Cloud Access Security Broker) o equivalentes para detectar el uso no autorizado de servicios cloud.

## 7. APROBACIÓN, REVISIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual y siempre que se contrate un nuevo servicio cloud significativo.

---

**Documento {{ proyecto.codigo_documento_base }}-111 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
