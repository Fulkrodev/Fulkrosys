# INFORME DE SIMULACROS DE PHISHING DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-503 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Informe de Simulacros de Phishing ha sido elaborado por {{ responsables.consultor.nombre }} en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

Este Informe constituye evidencia auditable del programa de concienciación frente a phishing en cumplimiento de las medidas **mp.per.3 Concienciación** del Anexo II del RD 311/2022 y de las obligaciones derivadas de NIS2 Art. 21.

## 1. FICHA DE LA CAMPAÑA

| Campo | Valor |
|---|---|
| Identificador de campaña | {{ campania.id }} |
| Nombre interno | {{ campania.nombre }} |
| Trimestre · año | {{ campania.trimestre }} · {{ campania.anyo }} |
| Plataforma | {{ campania.plataforma }} |
| Fecha de envío | {{ campania.fecha_envio }} |
| Duración de la ventana de monitorización | {{ campania.duracion }} |
| Tipo de escenario | {{ campania.tipo_escenario }} |
| Dificultad estimada | {{ campania.dificultad }} |
| Plantillas empleadas | {{ campania.plantillas }} |

## 2. OBJETIVOS DE LA CAMPAÑA

{% for obj in campania.objetivos %}- {{ obj }}
{% endfor %}

## 3. ALCANCE Y POBLACIÓN OBJETIVO

| Segmento | Nº objetivo | Justificación de la selección |
|---|:---:|---|
{% for seg in segmentos %}| {{ seg.nombre }} | {{ seg.num_destinatarios }} | {{ seg.justificacion }} |
{% endfor %}

**Total destinatarios**: {{ campania.total_destinatarios }}.

Las campañas se ejecutan con autorización previa del Comité de Seguridad y, cuando los destinatarios incluyen personal con representación sindical, se respeta el protocolo de notificación interna aplicable.

## 4. RESULTADOS GLOBALES

| Métrica | Valor | Tasa | Objetivo Plan E-500 |
|---|:---:|:---:|:---:|
| Emails entregados | {{ resultados.entregados }} | 100% | — |
| Emails abiertos | {{ resultados.abiertos }} | {{ resultados.tasa_abierto }}% | — |
| Clicks en el enlace | {{ resultados.clicks }} | {{ resultados.tasa_click }}% | < 10% (ideal 5%) |
| Credenciales introducidas (si aplica) | {{ resultados.credenciales }} | {{ resultados.tasa_credenciales }}% | < 2% |
| Reportes a IT-Sec / Seguridad | {{ resultados.reportes }} | {{ resultados.tasa_reporte }}% | ≥ 50% |
| Acción nula (ignorado) | {{ resultados.ignorados }} | {{ resultados.tasa_ignorados }}% | — |

## 5. ANÁLISIS POR SEGMENTO

| Segmento | Tasa click | Tasa reporte | Comparativa con campaña anterior |
|---|:---:|:---:|:---:|
{% for seg in segmentos_analisis %}| {{ seg.nombre }} | {{ seg.tasa_click }}% | {{ seg.tasa_reporte }}% | {{ seg.delta_anterior }} |
{% endfor %}

## 6. PATRONES IDENTIFICADOS

- **Empleados con click recurrente** (≥ 2 campañas consecutivas): {{ patrones.recurrentes }}.
- **Áreas con tasa de click superior a la media**: {{ patrones.areas_alta }}.
- **Áreas con mejora respecto al periodo anterior**: {{ patrones.areas_mejora }}.
- **Empleados destacados por reporte temprano**: {{ patrones.early_reporters }}.

## 7. ACCIONES INDIVIDUALES Y COLECTIVAS

### 7.1 Acciones individuales

Los empleados que han hecho click reciben una intervención formativa individualizada conforme al protocolo del Plan E-500:

- **Primera ocurrencia**: módulo de refuerzo M-G1-002 (Concienciación frente al phishing) más feedback escrito.
- **Segunda ocurrencia consecutiva**: sesión individual con el Responsable de Seguridad y plan personalizado.
- **Reincidencia** (tres campañas consecutivas con click): elevación al Comité de Seguridad y análisis de necesidades específicas del rol.

### 7.2 Acciones colectivas

| ID | Acción | Audiencia | Responsable | Plazo |
|---|---|---|---|---|
{% for ac in acciones_colectivas %}| {{ ac.id }} | {{ ac.descripcion }} | {{ ac.audiencia }} | {{ ac.responsable }} | {{ ac.plazo }} |
{% endfor %}

## 8. PÁGINA DE LANDING POST-CLICK

A los empleados que hacen click se les presenta una página de aprendizaje (no de sanción) con:

- Mensaje formativo que explica las señales de phishing que debían identificarse.
- Recordatorio del procedimiento correcto de reporte.
- Enlace a recursos formativos adicionales.
- Mensaje claro de que la simulación es interna y sin consecuencias disciplinarias.

## 9. CONCLUSIONES Y RECOMENDACIONES

**Valoración global de la campaña**: {{ valoracion_global }}.

{{ conclusion_texto }}

Recomendaciones para la siguiente campaña:

{% for rec in recomendaciones %}- {{ rec }}
{% endfor %}

## 10. EVIDENCIAS CONSERVADAS

Para cada campaña se conservan, durante un mínimo de **3 años**, las siguientes evidencias:

- Plantilla del email simulado con metadatos (asunto, remitente, dominio).
- Logs completos de la plataforma (impactos, clicks, reportes con timestamp).
- Material formativo entregado tras el click.
- Lista anonimizada de KPIs por área (para análisis trend).
- Comunicación interna previa al Comité de Seguridad.

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
