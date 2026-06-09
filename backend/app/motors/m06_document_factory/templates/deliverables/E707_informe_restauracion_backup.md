# INFORME DE PRUEBA DE RESTAURACIÓN DESDE COPIA DE SEGURIDAD DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-707 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Informe de Prueba de Restauración desde Copia de Seguridad ha sido elaborado por {{ responsables.consultor.nombre }} en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

## 1. OBJETO Y MARCO NORMATIVO

El presente Informe documenta la ejecución y los resultados de una **prueba real de restauración desde copia de seguridad** sobre el sistema {{ proyecto.sistema_principal }}, ejecutada para validar:

- La **integridad** de las copias de seguridad almacenadas.
- La **operatividad efectiva** del procedimiento de restauración.
- El **cumplimiento del RPO** declarado por el sistema crítico.
- La **trazabilidad** del proceso para evidencia de auditoría.

Este Informe es la evidencia auditable específica de las medidas:

- **RD 311/2022 Anexo II**: **mp.info.6 Copias de seguridad** + **op.cont.3 Pruebas periódicas** + **op.exp.10 Protección de los registros de actividad**.
- **CCN-STIC-808** Continuidad de servicios bajo el ENS.
- **Política de Copias de Seguridad (E-106)** del SGSI.

Se diferencia del **E-406 Informe de Pruebas de Continuidad** en que este Informe se centra **exclusivamente en la operación técnica de restauración** y no en el ejercicio agregado de continuidad de negocio.

## 2. FICHA DE LA PRUEBA

| Campo | Valor |
|---|---|
| Identificador de la prueba | {{ prueba.id }} |
| Sistema/dataset restaurado | {{ prueba.sistema }} |
| Tipo de prueba | {{ prueba.tipo }} |
| Modalidad | {{ prueba.modalidad }} |
| Fecha de ejecución | {{ prueba.fecha }} |
| Hora de inicio | {{ prueba.hora_inicio }} |
| Hora de finalización | {{ prueba.hora_fin }} |
| Duración total | {{ prueba.duracion }} |
| Operador técnico | {{ prueba.operador }} |
| Observador / verificador | {{ prueba.verificador }} |

## 3. BACKUP DE ORIGEN

| Campo | Valor |
|---|---|
| Identificador de backup | {{ backup.id }} |
| Tipo (completa/incremental/transaccional) | {{ backup.tipo }} |
| Fecha del backup | {{ backup.fecha }} |
| Tamaño total | {{ backup.tamaño }} |
| Ubicación | {{ backup.ubicacion }} |
| Cifrado en reposo | {{ backup.cifrado }} |
| Algoritmo / política | {{ backup.algoritmo }} |
| Integridad pre-restauración (hash) | {{ backup.hash_verificado }} |

## 4. ENTORNO DE RESTAURACIÓN

| Campo | Valor |
|---|---|
| Tipo de entorno | {{ entorno.tipo }} |
| Aislamiento | {{ entorno.aislamiento }} |
| Recursos asignados | {{ entorno.recursos }} |
| Aislamiento de red | {{ entorno.red }} |
| Confirmación de no interferencia con producción | {{ entorno.no_interferencia }} |

## 5. CRONOLOGÍA DE LA RESTAURACIÓN

{% for evento in cronologia %}- **{{ evento.timestamp }}** — {{ evento.descripcion }}.
{% endfor %}

## 6. MÉTRICAS RTO Y RPO REALES VS OBJETIVOS

| Métrica | Objetivo | Valor obtenido | Cumplimiento |
|---|:---:|:---:|:---:|
| RTO técnico | {{ metricas.rto_objetivo }} | {{ metricas.rto_real }} | {{ metricas.rto_cumplimiento }} |
| RPO técnico | {{ metricas.rpo_objetivo }} | {{ metricas.rpo_real }} | {{ metricas.rpo_cumplimiento }} |
| Tiempo de descifrado | — | {{ metricas.tiempo_descifrado }} | — |
| Tiempo de validación de integridad | — | {{ metricas.tiempo_validacion }} | — |
| Tiempo de validación funcional | — | {{ metricas.tiempo_funcional }} | — |

## 7. VALIDACIÓN DE INTEGRIDAD DEL DATO RESTAURADO

| Prueba | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|:---:|
{% for v in validaciones_integridad %}| {{ v.prueba }} | {{ v.esperado }} | {{ v.obtenido }} | {{ v.estado }} |
{% endfor %}

## 8. VALIDACIÓN FUNCIONAL DEL SISTEMA RESTAURADO

| Funcionalidad clave | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|:---:|
{% for f in validaciones_funcionales %}| {{ f.funcionalidad }} | {{ f.esperado }} | {{ f.obtenido }} | {{ f.estado }} |
{% endfor %}

## 9. INCIDENCIAS DURANTE LA PRUEBA

| ID | Descripción | Causa | Impacto en la prueba | Resolución |
|---|---|---|---|---|
{% for inc in incidencias %}| {{ inc.id }} | {{ inc.descripcion }} | {{ inc.causa }} | {{ inc.impacto }} | {{ inc.resolucion }} |
{% endfor %}

## 10. HALLAZGOS Y ACCIONES CORRECTIVAS

| Gap | Severidad | Acción correctiva | Responsable | Plazo | Estado |
|---|:---:|---|---|---|:---:|
{% for h in hallazgos %}| {{ h.descripcion }} | {{ h.severidad }} | {{ h.accion }} | {{ h.responsable }} | {{ h.plazo }} | {{ h.estado }} |
{% endfor %}

## 11. DESTRUCCIÓN DEL ENTORNO Y DATOS RESTAURADOS

Tras la finalización de la prueba se ha procedido a la **destrucción segura** del entorno de restauración y de cualquier copia residual de los datos restaurados, conforme al procedimiento de eliminación segura (E-204) del SGSI. Esta acción queda registrada con timestamp y firma del operador.

## 12. CONCLUSIÓN

**Valoración global**: {{ valoracion }}.

{{ conclusion_texto }}

Recomendaciones para el siguiente ciclo:

{% for rec in recomendaciones %}- {{ rec }}
{% endfor %}

## 13. ANEXOS

- **Anexo A**: Logs completos de la restauración con timestamps.
- **Anexo B**: Capturas de pantalla de las validaciones funcionales.
- **Anexo C**: Hashes pre y post restauración para verificación de integridad.
- **Anexo D**: Lista de personas con acceso al entorno aislado durante la prueba.
- **Anexo E**: Certificado de destrucción del entorno.

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
