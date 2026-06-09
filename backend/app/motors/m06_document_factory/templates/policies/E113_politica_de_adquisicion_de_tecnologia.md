# DOCUMENTO E-113 — POLÍTICA DE ADQUISICIÓN DE TECNOLOGÍA

**Materializa op.pl.3 (Adquisición de nuevos componentes) y op.pl.5 (Componentes certificados / CPSTIC) del Anexo II.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-113"
titulo: "Política de Adquisición de Tecnología"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE ADQUISICIÓN DE TECNOLOGÍA DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-113 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los criterios de seguridad que {{ cliente.razon_social }} aplicará en la adquisición, contratación e incorporación de componentes tecnológicos (hardware, software, servicios y productos de seguridad) a los sistemas comprendidos en el alcance del SGSI, en cumplimiento de las medidas **op.pl.3** y **op.pl.5** del Anexo II del Real Decreto 311/2022.

## 2. PRINCIPIOS

**2.1 Evaluación previa de seguridad.** Ningún componente tecnológico se incorporará al entorno productivo sin una evaluación previa de su impacto en la seguridad del sistema, proporcional a su criticidad.

**2.2 Soporte vigente.** Solo se adquirirán productos con soporte activo del fabricante, salvo excepción documentada y autorizada conforme al apartado 9 de la Política de Seguridad ({{ proyecto.codigo_documento_base }}-100).

**2.3 Preferencia CPSTIC.** {% if proyecto.categoria_ens in ["MEDIA", "ALTA"] %}Para los productos de seguridad TIC (criptografía, cortafuegos, IDS/IPS, antimalware, gestión de identidades, SIEM), se dará **preferencia** a los productos incluidos en el **Catálogo de Productos y Servicios de Seguridad TIC (CPSTIC)** del Centro Criptológico Nacional, conforme a la medida op.pl.5 del Anexo II.{% else %}Se valorará la inclusión de los productos en el CPSTIC del Centro Criptológico Nacional como criterio positivo de selección.{% endif %}

**2.4 Cadena de suministro.** Se valorará el origen del fabricante, la existencia de obligaciones legales en su jurisdicción que pudieran afectar a la seguridad de la información, y la transparencia de su cadena de suministro.

## 3. PROCESO DE ADQUISICIÓN

Toda solicitud de adquisición de tecnología para sistemas del alcance del SGSI seguirá este flujo:

a) **Solicitud** del área funcional con justificación de necesidad.

b) **Evaluación de seguridad** por el Responsable de la Seguridad, considerando: compatibilidad con la arquitectura, impacto en la superficie de ataque, requisitos de hardening, disponibilidad de parches, certificaciones de seguridad.

c) **Verificación CPSTIC** cuando el producto sea de seguridad TIC y la categoría sea MEDIA o ALTA.

d) **Aprobación** del Responsable de la Seguridad (o del Comité de Seguridad para adquisiciones de impacto ALTO).

e) **Integración controlada** mediante el procedimiento de gestión de cambios ({{ proyecto.codigo_documento_base }}-203) y hardening conforme a las baselines aplicables.

## 4. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-113 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
