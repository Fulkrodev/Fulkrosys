---
codigo_documento: "E-010"
titulo: "Acta de Decisión de Adecuación al ENS de la Dirección"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "INTERNA"
norma_aplicable: "RD 311/2022 Anexo II · org.1 (Política de seguridad) + art. 11 + art. 12 (compromiso de la Dirección)"
---

# ACTA DE DECISIÓN DE ADECUACIÓN AL ESQUEMA NACIONAL DE SEGURIDAD · {{ cliente.razon_social | upper }}

**Documento E-010 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: INTERNA**

---

{% set fecha = proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '[fecha]' %}
{% set cat = proyecto.categoria_ens if proyecto.categoria_ens else 'MEDIA' %}

## 1. DATOS DEL ACTA

| Campo | Valor |
|-------|-------|
| Entidad | **{{ cliente.razon_social }}** |
| NIF | {{ cliente.nif if cliente.nif else '—' }} |
| Fecha | **{{ fecha }}** |
| Órgano que decide | {{ cliente.organo_aprobador_politicas if cliente.organo_aprobador_politicas else 'Órgano de gobierno superior (Dirección)' }} |
| Naturaleza | Decisión formal de adecuación · permanente en expediente SGSI |

## 2. ANTECEDENTES

La Dirección de **{{ cliente.razon_social }}**, consciente de la dependencia de la Entidad respecto de los sistemas y servicios de información y de las obligaciones derivadas de su relación con el sector público, examina la necesidad de adecuar dichos sistemas al **Esquema Nacional de Seguridad (Real Decreto 311/2022, de 3 de mayo)**.

Conforme a la medida **org.1 (Política de seguridad)** del Anexo II del RD 311/2022 y al compromiso de la Dirección exigido por el propio Esquema, la adecuación al ENS requiere una **decisión expresa y documentada del órgano de gobierno** que la impulse, dote de recursos y respalde.

## 3. DECISIONES ADOPTADAS

La Dirección **ACUERDA**:

a) **Impulsar la adecuación** de los sistemas de información de la Entidad al Esquema Nacional de Seguridad, en la **categoría {{ cat }}** resultante de la categorización (acta E-012).

b) **Aprobar la Política de Seguridad de la Información** (E-100) y la normativa de seguridad que la desarrolla, asumiendo su contenido como marco de obligado cumplimiento para toda la organización.

c) **Designar al Responsable de la Seguridad** y los demás roles ENS del artículo 11 del RD 311/2022, formalizados en el acta de nombramiento de roles (E-002).

d) **Dotar de los recursos** humanos, técnicos y económicos necesarios para implantar y mantener las medidas del Anexo II aplicables a la categoría {{ cat }}, conforme al Plan de Adecuación (E-150).

e) **Comprometerse con la mejora continua** del Sistema de Gestión de Seguridad de la Información y con la revisión periódica de su conformidad.

## 4. COMPROMISO DE LA DIRECCIÓN

La Dirección asume el **liderazgo y la responsabilidad última** sobre la seguridad de la información de la Entidad, respalda al Responsable de la Seguridad en el ejercicio de sus funciones y se compromete a revisar periódicamente la eficacia del SGSI conforme al RD 311/2022.

## 5. APROBACIÓN Y FIRMA

Esta decisión se adopta por el órgano de gobierno de **{{ cliente.razon_social }}** y se incorpora con carácter permanente al expediente del SGSI. Es **firmable** por la Dirección (E-signature TIER 1 · m05_signing).

| Función | Nombre | Cargo | Fecha |
|---------|--------|-------|-------|
| Aprobado (Dirección) | {{ firmas.aprobado.nombre if firmas and firmas.aprobado else '—' }} | {{ firmas.aprobado.cargo if firmas and firmas.aprobado else 'Órgano de gobierno superior' }} | {{ firmas.aprobado.fecha if firmas and firmas.aprobado else fecha }} |

---

_Documento generado por Fulkro · {{ consultor.footer_text if consultor and consultor.footer_text else 'Fulkro' }}_
