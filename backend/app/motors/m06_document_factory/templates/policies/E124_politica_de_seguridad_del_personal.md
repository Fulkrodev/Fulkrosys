# DOCUMENTO E-124 — POLÍTICA DE SEGURIDAD DEL PERSONAL

**Materializa mp.per.1 (Caracterización del puesto de trabajo), mp.per.2 (Deberes y obligaciones), mp.per.3 (Concienciación) y mp.per.4 (Formación) del Anexo II.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-124"
titulo: "Política de Seguridad del Personal"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE SEGURIDAD DEL PERSONAL DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-124 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los requisitos de seguridad aplicables al ciclo de vida de la relación de las personas con {{ cliente.razon_social }} (selección, incorporación, desempeño, cambio de funciones y desvinculación), en cumplimiento de las medidas **mp.per.1 a mp.per.4** del Anexo II del Real Decreto 311/2022.

## 2. ANTES DE LA INCORPORACIÓN [mp.per.1]

a) Los puestos de trabajo con acceso a información del alcance del SGSI tendrán documentados sus requisitos de seguridad (accesos necesarios, nivel de habilitación, formación requerida).

b) Los candidatos a puestos con acceso a información CONFIDENCIAL o superior serán objeto de verificación de antecedentes proporcional al riesgo, conforme a la legislación laboral aplicable y con respeto a la normativa de protección de datos.

## 3. DURANTE LA RELACIÓN [mp.per.2, mp.per.3, mp.per.4]

a) Todo el personal firmará un **compromiso de confidencialidad** y un **acuse de recibo** de la Política de Uso Aceptable ({{ proyecto.codigo_documento_base }}-103) como parte de su proceso de incorporación.

b) Se impartirá una **sesión de acogida en seguridad** durante la primera semana, conforme al Plan de Formación (E-PF-001).

c) El personal recibirá **formación y concienciación periódica** conforme al Plan de Formación, con contenidos adaptados a su perfil (técnico, directivo, roles ENS).

d) Los deberes de seguridad se incluirán, cuando sea posible, en la descripción del puesto de trabajo y en los criterios de evaluación del desempeño.

## 4. CAMBIO DE FUNCIONES

Cuando una persona cambie de puesto o funciones, se revisarán sus accesos y privilegios conforme al procedimiento de gestión de identidades ({{ proyecto.codigo_documento_base }}-231), aplicando el principio de mínimo privilegio al nuevo puesto y revocando los accesos del puesto anterior que dejen de ser necesarios.

## 5. DESVINCULACIÓN

Al término de la relación laboral o contractual se aplicará el procedimiento de baja ({{ proyecto.codigo_documento_base }}-201), incluyendo: revocación de accesos, devolución de equipos y soportes, recordatorio de las obligaciones de confidencialidad subsistentes y, cuando proceda, entrevista de salida.

## 6. PERSONAL EXTERNO

Los requisitos de seguridad aplicables al personal externo (contratistas, consultores, becarios) serán equivalentes a los del personal interno con acceso análogo. Las cláusulas de confidencialidad y los requisitos de formación se incluirán en los contratos con los proveedores correspondientes conforme a la Política de Gestión de Proveedores ({{ proyecto.codigo_documento_base }}-112).

## 7. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-124 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
