# INFORME FORMAL DE CAMPAÑA DE PHISHING DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-705 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Informe formal de Campaña de Phishing ha sido elaborado por {{ responsables.consultor.nombre }} en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

## 1. OBJETO Y NATURALEZA DEL DOCUMENTO

El presente Informe documenta de forma **formal y exhaustiva** una campaña de phishing ejecutada como ejercicio singular de medición de la resiliencia humana de {{ cliente.razon_social }}, dirigido principalmente al auditor externo en categorías **MEDIA y ALTA** del ENS.

Este Informe se diferencia del **E-503 Informe de Simulacros de Phishing** (vinculado al ciclo trimestral del LMS) en que:

- Documenta una campaña singular con profundidad técnica completa (metodología, infraestructura, indicadores de compromiso simulados).
- Incluye benchmarks sectoriales comparativos.
- Aporta análisis de comportamiento más detallado al equipo auditor.
- Suele realizarse en el último trimestre del año previo a la auditoría externa.

## 2. MARCO NORMATIVO Y REFERENCIAS

- **RD 311/2022** Anexo II: **mp.per.3 Concienciación** + **mp.per.4 Formación**.
- **NIS2 Art. 21.2** (medidas de gestión de riesgos · pruebas periódicas).
- **DORA Art. 24-26** si la Entidad opera bajo el ámbito financiero.
- **CCN-STIC-481** Guía de concienciación bajo el ENS.

## 3. ALCANCE DE LA CAMPAÑA

| Campo | Valor |
|---|---|
| Identificador | {{ campania.id }} |
| Periodo de ejecución | {{ campania.fecha_inicio }} a {{ campania.fecha_fin }} |
| Duración total | {{ campania.duracion }} |
| Plataforma | {{ campania.plataforma }} |
| Tipo de campaña | {{ campania.tipo }} |
| Sector objetivo de la suplantación | {{ campania.sector_simulado }} |
| Modalidad | {{ campania.modalidad }} |
| Autorización | {{ campania.autorizacion }} |
| Total destinatarios | {{ campania.total_destinatarios }} |

## 4. METODOLOGÍA TÉCNICA DETALLADA

### 4.1 Diseño del escenario

El escenario reproduce un ataque realista basado en TTPs documentados (MITRE ATT&CK):

- **T1566.001 Spearphishing Attachment** (si aplica).
- **T1566.002 Spearphishing Link** (si aplica).
- **T1078 Valid Accounts** mediante suplantación visual.

Descripción del escenario: {{ escenario.descripcion }}.

### 4.2 Infraestructura empleada

- **Dominio remitente**: {{ infraestructura.dominio_remitente }} (registrado expresamente para la campaña).
- **Plataforma de envío**: {{ infraestructura.plataforma_envio }}.
- **Página de landing controlada**: {{ infraestructura.landing }}.
- **Sistema de captura de credenciales** (simulado, sin retención real): {{ infraestructura.captura }}.
- **Sistema de tracking**: {{ infraestructura.tracking }}.

### 4.3 Configuración técnica

- **SPF/DKIM/DMARC del dominio simulado**: configurados para no marcar como spam el mensaje en el alcance interno.
- **Bypass de filtros corporativos**: coordinado con el departamento de IT-Sec para permitir la llegada al buzón objetivo.
- **Trazabilidad temporal**: cada acción del usuario queda registrada con timestamp en UTC.

## 5. POBLACIÓN OBJETIVO Y SEGMENTACIÓN

| Segmento | Justificación | Nº destinatarios |
|---|---|:---:|
{% for seg in segmentacion %}| {{ seg.nombre }} | {{ seg.justificacion }} | {{ seg.numero }} |
{% endfor %}

## 6. RESULTADOS CUANTITATIVOS GLOBALES

| Métrica | Valor absoluto | % sobre destinatarios | Benchmark sectorial |
|---|:---:|:---:|:---:|
| Entregados con éxito | {{ resultados.entregados }} | 100% | — |
| Abiertos | {{ resultados.abiertos }} | {{ resultados.tasa_abierto }}% | {{ resultados.benchmark_abierto }} |
| Clicks en enlace | {{ resultados.clicks }} | {{ resultados.tasa_click }}% | {{ resultados.benchmark_click }} |
| Credenciales introducidas | {{ resultados.credenciales }} | {{ resultados.tasa_credenciales }}% | {{ resultados.benchmark_credenciales }} |
| Reportes correctos a Seguridad | {{ resultados.reportes }} | {{ resultados.tasa_reporte }}% | {{ resultados.benchmark_reporte }} |
| Tiempo medio hasta primer reporte | {{ resultados.tiempo_primer_reporte }} | — | {{ resultados.benchmark_tiempo }} |

## 7. ANÁLISIS COMPARATIVO CON CAMPAÑAS PREVIAS

| Campaña | Fecha | Tasa click | Tasa reporte | Variación interanual |
|---|:---:|:---:|:---:|:---:|
{% for prev in campanyas_previas %}| {{ prev.id }} | {{ prev.fecha }} | {{ prev.tasa_click }}% | {{ prev.tasa_reporte }}% | {{ prev.variacion }} |
{% endfor %}

**Tendencia identificada**: {{ tendencia_texto }}.

## 8. ANÁLISIS CUALITATIVO

### 8.1 Comportamiento por segmento

{% for analisis in analisis_segmentos %}- **{{ analisis.segmento }}**: {{ analisis.descripcion }}.
{% endfor %}

### 8.2 Señales que los empleados detectaron correctamente

{% for señal in señales_detectadas %}- {{ señal }}
{% endfor %}

### 8.3 Señales que pasaron desapercibidas

{% for señal in señales_no_detectadas %}- {{ señal }}
{% endfor %}

## 9. ACCIONES POSTERIORES

### 9.1 Acciones individuales

Los empleados que han hecho click reciben formación de refuerzo conforme al protocolo del Plan E-500.

### 9.2 Acciones colectivas

| ID | Acción | Audiencia | Responsable | Plazo |
|---|---|---|---|---|
{% for ac in acciones_colectivas %}| {{ ac.id }} | {{ ac.descripcion }} | {{ ac.audiencia }} | {{ ac.responsable }} | {{ ac.plazo }} |
{% endfor %}

## 10. CONCLUSIONES Y RECOMENDACIONES PARA EL AUDITOR

**Valoración global**: {{ valoracion }}.

{{ conclusion_texto }}

Recomendaciones para el siguiente ciclo:

{% for rec in recomendaciones %}- {{ rec }}
{% endfor %}

## 11. ANEXOS PARA EL AUDITOR

- **Anexo A**: Plantilla del email simulado con metadatos completos.
- **Anexo B**: Capturas de la página de landing post-click.
- **Anexo C**: Logs anonimizados completos.
- **Anexo D**: Comunicación previa al Comité de Seguridad autorizando la campaña.
- **Anexo E**: Evidencias de la formación de refuerzo entregada tras la campaña.

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
