# INFORME DE AUDITORÍA EXTERNA DEL ENS DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-708 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ auditoria_externa.entidad_auditora }} | Versión inicial emitida por la entidad certificadora |

## NATURALEZA DEL DOCUMENTO

El presente Informe es el documento **emitido por la entidad certificadora acreditada por ENAC** que ha conducido la auditoría externa del cumplimiento del Esquema Nacional de Seguridad sobre el sistema {{ proyecto.sistema_principal }} de {{ cliente.razon_social }}.

La plantilla refleja la **estructura formal del informe** que el auditor externo emitirá. {{ cliente.razon_social }} y su consultor ({{ responsables.consultor.nombre }}) **preparan la documentación de apoyo y las evidencias**; el auditor externo redacta, firma y emite el informe definitivo y eleva la propuesta de certificación al CCN.

## 1. ENTIDAD CERTIFICADORA Y EQUIPO AUDITOR

| Campo | Valor |
|---|---|
| Entidad certificadora | {{ auditoria_externa.entidad_auditora }} |
| Acreditación ENAC | {{ auditoria_externa.acreditacion }} |
| Auditor jefe | {{ auditoria_externa.auditor_jefe }} |
| Equipo auditor | {{ auditoria_externa.equipo }} |
| Fecha de la auditoría | {{ auditoria_externa.fecha_inicio }} a {{ auditoria_externa.fecha_fin }} |
| Ciclo de certificación | {{ auditoria_externa.ciclo }} |
| Modalidad | {{ auditoria_externa.modalidad }} |

## 2. ENTIDAD AUDITADA Y ALCANCE

| Campo | Valor |
|---|---|
| Razón social | {{ cliente.razon_social }} |
| NIF | {{ cliente.nif }} |
| Dirección | {{ cliente.direccion }} |
| Representante legal | {{ cliente.representante_legal }} |
| Responsable de Seguridad | {{ responsables.responsable_seguridad.nombre }} |
| Sistema certificado | {{ proyecto.sistema_principal }} |
| Alcance declarado | {{ proyecto.alcance }} |
| Categoría declarada | {{ proyecto.categoria_ens }} |

## 3. MARCO NORMATIVO DE REFERENCIA

- **Real Decreto 311/2022** de 3 de mayo, por el que se regula el ENS.
- **Anexo II** medidas de seguridad aplicables a la categoría declarada.
- **Anexo III** auditoría de la seguridad.
- **Guía CCN-STIC-802** Auditoría del ENS.
- **Guía CCN-STIC-808** Continuidad de servicios bajo el ENS.
- **Guía CCN-STIC-809** Declaración y certificación de conformidad con el ENS.

## 4. METODOLOGÍA DE LA AUDITORÍA EXTERNA

La auditoría externa se ha conducido conforme a la guía CCN-STIC-802, mediante:

- **Revisión documental** de la Declaración de Aplicabilidad (DdA), las políticas, los procedimientos y los registros del SGSI.
- **Entrevistas** al Responsable de Seguridad, a los responsables de procesos y al personal operativo seleccionado por muestreo.
- **Inspección directa** de los controles técnicos sobre la infraestructura.
- **Validación de evidencias** de los últimos 12 meses, incluyendo el ejercicio interno previo (E-700), la pre-externa (E-701), las pruebas de continuidad (E-405/E-406), las pruebas de restauración (E-707), los ejercicios tabletop (E-706) y las campañas de phishing (E-503/E-705).
- **Pruebas de cumplimiento** sobre una muestra representativa de medidas del Anexo II.

## 5. RESULTADOS POR FAMILIA DE MEDIDAS (ANEXO II)

| Familia | Medidas aplicables | Conformes | NC menores | NC mayores | No aplica |
|---|:---:|:---:|:---:|:---:|:---:|
{% for fam in resultados_externa_familia %}| {{ fam.nombre }} | {{ fam.aplicables }} | {{ fam.conformes }} | {{ fam.nc_menores }} | {{ fam.nc_mayores }} | {{ fam.no_aplica }} |
{% endfor %}

**Total medidas auditadas**: {{ resumen.total }}. **Conformidad global**: {{ resumen.conformidad_pct }}%.

## 6. NO CONFORMIDADES DETECTADAS POR EL AUDITOR EXTERNO

| ID | Medida | Tipo | Descripción | Plazo cierre exigido |
|---|:---:|:---:|---|:---:|
{% for nc in ncs_externas %}| {{ nc.id }} | {{ nc.medida }} | {{ nc.tipo }} | {{ nc.descripcion }} | {{ nc.plazo }} |
{% endfor %}

## 7. OBSERVACIONES Y OPORTUNIDADES DE MEJORA

{% for obs in observaciones_externas %}- **{{ obs.id }}** ({{ obs.medida }}): {{ obs.descripcion }}. Recomendación: {{ obs.recomendacion }}.
{% endfor %}

## 8. EVIDENCIAS REVISADAS

| Evidencia | Tipo | Periodo | Estado |
|---|:---:|:---:|:---:|
{% for ev in evidencias_revisadas %}| {{ ev.nombre }} | {{ ev.tipo }} | {{ ev.periodo }} | {{ ev.estado }} |
{% endfor %}

## 9. DICTAMEN DEL AUDITOR

**Dictamen**: {{ dictamen.resultado }}.

Valores posibles del dictamen:

- **FAVORABLE**: cumplimiento sin No Conformidades Mayores. Procede certificación.
- **FAVORABLE CON OBSERVACIONES**: cumplimiento con NCs menores u observaciones que no comprometen la certificación, exigibles para próximo ciclo.
- **DESFAVORABLE**: existencia de una o más NCs Mayores no cerradas que comprometen la certificación.

{{ dictamen.fundamentacion }}

## 10. RECOMENDACIÓN DE CERTIFICACIÓN

**Propuesta elevada al CCN**: {{ propuesta_certificacion }}.

Periodo de validez de la certificación propuesta: {{ vigencia_certificacion }}. Próxima auditoría de seguimiento: {{ proxima_auditoria }}.

## 11. PLAN DE ACCIONES CORRECTIVAS EXIGIDO

| ID | NC relacionada | Acción exigida | Plazo | Verificación |
|---|:---:|---|:---:|---|
{% for ac in acciones_correctivas_exigidas %}| {{ ac.id }} | {{ ac.nc_ref }} | {{ ac.descripcion }} | {{ ac.plazo }} | {{ ac.verificacion }} |
{% endfor %}

## 12. ANEXOS

- **Anexo A**: Plan de auditoría externa.
- **Anexo B**: Lista completa de entrevistados con fecha.
- **Anexo C**: Detalle de cada NC con evidencia asociada.
- **Anexo D**: Histórico de auditorías previas de la Entidad (si aplica).

## TABLA DE FIRMAS

| Función | Nombre | Entidad | Fecha | Firma |
|---|---|---|---|---|
| Auditor jefe externo | {{ auditoria_externa.auditor_jefe }} | {{ auditoria_externa.entidad_auditora }} | {{ auditoria_externa.fecha_fin }} | {{ firmas.auditor_externo }} |
| Responsable de Seguridad | {{ responsables.responsable_seguridad.nombre }} | {{ cliente.razon_social }} | {{ auditoria_externa.fecha_fin }} | {{ firmas.responsable_seguridad }} |
| Aprobación interna | {{ firmas.aprobado.nombre }} | {{ cliente.razon_social }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
