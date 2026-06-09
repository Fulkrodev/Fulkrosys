# INFORME DE AUDITORÍA INTERNA PRE-EXTERNA DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-701 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Informe de Auditoría Interna Pre-Externa ha sido elaborado por {{ responsables.consultor.nombre }} en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

## 1. OBJETO

El presente Informe documenta la **Auditoría Interna Pre-Externa**, ejercicio dirigido al cierre preventivo de no conformidades antes de la **auditoría externa de certificación ENS por entidad acreditada ENAC**. Su finalidad es:

- Verificar que las No Conformidades detectadas en la Auditoría Interna Inicial (E-700) están cerradas con evidencia documental.
- Confirmar que la documentación está lista y consolidada para presentación al auditor externo.
- Identificar últimos puntos de riesgo en evidencias de los últimos 6-12 meses.
- Garantizar la coherencia interna entre Declaración de Aplicabilidad (DdA), política y procedimientos vigentes.

## 2. MARCO NORMATIVO

- **RD 311/2022 Art. 31** y medidas mp.aud.* del Anexo II.
- **CCN-STIC-802** Guía de auditoría del ENS.
- **Política de Auditoría Interna** del SGSI (E-216).

## 3. ALCANCE

| Campo | Valor |
|---|---|
| Sistema | {{ proyecto.sistema_principal }} |
| Alcance ENS | {{ proyecto.alcance }} |
| Categoría | {{ proyecto.categoria_ens }} |
| Fecha de ejecución | {{ auditoria.fecha_inicio }} a {{ auditoria.fecha_fin }} |
| Auditor jefe | {{ auditoria.auditor_jefe }} |
| Equipo auditor | {{ auditoria.equipo_auditor }} |
| E-700 referenciado | {{ auditoria.e700_ref }} |
| Auditoría externa programada | {{ auditoria.externa_fecha }} |

## 4. METODOLOGÍA

El ejercicio se ha conducido como auditoría dirigida con foco específico en:

- **Cierre de NCs E-700**: revisión documental + evidencia técnica + entrevista al responsable de cierre.
- **Evidencias frescas últimos 6-12 meses**: revisión por muestreo aleatorio de registros operativos del SGSI.
- **Documentación lista para ENAC**: revisión de Declaración de Aplicabilidad, política de seguridad, procedimientos vigentes, registros de Comité de Seguridad, plan de tratamiento de riesgos.
- **Coherencia interna**: detección de inconsistencias entre documentos del SGSI.

## 5. RESULTADO · CIERRE DE NCs DETECTADAS EN E-700

| ID NC | Tipo original | Descripción resumida | Acción ejecutada | Evidencia de cierre | Estado |
|---|:---:|---|---|---|:---:|
{% for cierre in cierre_ncs %}| {{ cierre.id }} | {{ cierre.tipo }} | {{ cierre.descripcion }} | {{ cierre.accion }} | {{ cierre.evidencia }} | {{ cierre.estado }} |
{% endfor %}

**Resumen**: {{ resumen.ncs_iniciales }} NCs originales · {{ resumen.ncs_cerradas }} cerradas · {{ resumen.ncs_pendientes }} pendientes · {{ resumen.ncs_nuevas }} nuevas detectadas.

## 6. NUEVAS NO CONFORMIDADES DETECTADAS

| ID | Medida | Tipo | Descripción | Severidad | Plazo cierre antes auditoría externa |
|---|:---:|:---:|---|:---:|:---:|
{% for nc in nuevas_ncs %}| {{ nc.id }} | {{ nc.medida }} | {{ nc.tipo }} | {{ nc.descripcion }} | {{ nc.severidad }} | {{ nc.plazo }} |
{% endfor %}

## 7. ESTADO DE LA DOCUMENTACIÓN

| Documento | Versión vigente | Aprobado por | Fecha aprobación | Coherencia con DdA |
|---|:---:|---|---|:---:|
{% for doc in documentos_revisados %}| {{ doc.nombre }} | {{ doc.version }} | {{ doc.aprobado_por }} | {{ doc.fecha }} | {{ doc.coherencia }} |
{% endfor %}

## 8. PUNTOS DE RIESGO IDENTIFICADOS

{% for riesgo in puntos_riesgo %}- **{{ riesgo.area }}**: {{ riesgo.descripcion }}. Mitigación propuesta: {{ riesgo.mitigacion }}. Plazo: {{ riesgo.plazo }}.
{% endfor %}

## 9. RECOMENDACIONES PRE-AUDITORÍA EXTERNA

{% for rec in recomendaciones %}- {{ rec }}
{% endfor %}

## 10. CONCLUSIÓN DEL AUDITOR JEFE

**Estado de preparación para auditoría externa**: {{ conclusion.estado }}.

{{ conclusion.texto }}

**Recomendación**: {{ conclusion.recomendacion }}.

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
