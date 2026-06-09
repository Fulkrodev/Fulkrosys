# DOCUMENTO E-219 — PROCEDIMIENTO DE REVISIÓN POR LA DIRECCIÓN

**Materializa el requisito ISO 27001:2022 cláusula 9.3 y el artículo 12 del RD 311/2022 sobre revisión periódica de la Política. Es la sesión anual donde el órgano de gobierno superior revisa el SGSI.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-219"
titulo: "Procedimiento de Revisión por la Dirección"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE REVISIÓN POR LA DIRECCIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-219 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el flujo mediante el cual {{ cliente.organo_aprobador_politicas }} revisa, al menos anualmente, el estado del SGSI, valora su adecuación, eficacia y alineación con los objetivos de la Entidad, y adopta las decisiones de mejora que procedan.

## 2. PERIODICIDAD

La revisión por la dirección se realizará con carácter ordinario **al menos una vez al año**, y con carácter extraordinario cuando lo requieran circunstancias excepcionales (incidente grave, cambio normativo mayor, reestructuración organizativa).

## 3. ENTRADAS (INPUT)

El Responsable de la Seguridad preparará y presentará a la dirección:

a) Estado de las acciones derivadas de revisiones anteriores.

b) Cambios en cuestiones internas y externas relevantes para el SGSI (contexto, normativa, amenazas, organización).

c) Resultados de las auditorías internas y externas.

d) Resumen de incidentes de seguridad del periodo y su gestión.

e) Estado del análisis de riesgos y del plan de tratamiento.

f) Estado de cumplimiento de las medidas del Anexo II (informe de la Declaración de Aplicabilidad).

g) Indicadores de rendimiento del SGSI (KPIs definidos en los procedimientos).

h) Resultados de las pruebas de continuidad.

i) Resultado de los simulacros de phishing y métricas de formación.

j) Oportunidades de mejora identificadas.

k) Estado del presupuesto de seguridad.

## 4. SALIDAS (OUTPUT)

La dirección adoptará decisiones documentadas sobre:

a) Oportunidades de mejora y acciones a emprender.

b) Necesidades de cambio en la Política de Seguridad o en la normativa interna.

c) Necesidades de recursos (humanos, técnicos, económicos).

d) Aceptación o no de los riesgos residuales actualizados.

e) Actualización de los objetivos de seguridad si procede.

## 5. REGISTRO

Las decisiones se documentarán en **acta de revisión por la dirección** firmada por el presidente de la sesión, que se conservará conforme al procedimiento de gestión documental ({{ proyecto.codigo_documento_base }}-221).

## 6. INDICADORES

| Indicador | Objetivo |
|---|---|
| Revisiones por la dirección realizadas en el año | ≥ 1 |
| Acciones derivadas cerradas en plazo | ≥ 90% |

---

**Documento {{ proyecto.codigo_documento_base }}-219 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
