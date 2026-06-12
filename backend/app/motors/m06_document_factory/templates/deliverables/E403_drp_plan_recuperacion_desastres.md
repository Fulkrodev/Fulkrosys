# PLAN DE RECUPERACIÓN DE DESASTRES TIC DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-403 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Plan de Recuperación de Desastres TIC (DRP) ha sido elaborado por {{ responsables.consultor.nombre }}, en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

## 1. OBJETO

El presente DRP define los procedimientos técnicos para la recuperación de los sistemas TIC del sistema {{ proyecto.sistema_principal }} tras una disrupción que comprometa su disponibilidad, en cumplimiento de la medida **op.cont.3 Pruebas periódicas** y **op.cont.2 Plan de continuidad** del Anexo II del Real Decreto 311/2022 y conforme a UNE-ISO 22301:2020 (gestión de la continuidad del negocio).

El DRP es el componente técnico del Plan de Continuidad del Negocio (E-402 BCP) y se activa en coordinación con éste.

## 2. ALCANCE TÉCNICO

El DRP cubre los siguientes activos del sistema:

- Servidores físicos y virtuales del alcance ENS.
- Bases de datos y almacenamiento crítico.
- Servicios cloud bajo el alcance.
- Red interna, comunicaciones perimetrales y conectividad de respaldo.
- Aplicaciones críticas identificadas en el BIA E-400.
- Datos sensibles bajo tratamiento conforme al RGPD y la política E-105.

## 3. CLASIFICACIÓN DE DESASTRES

| Nivel | Denominación | Descripción | Tiempo recuperación esperado |
|---|---|---|---|
| D1 | Menor | Indisponibilidad parcial de un componente con redundancia automática | < 1h |
| D2 | Mayor | Pérdida de un servicio o componente sin redundancia inmediata | 1h - 24h |
| D3 | Catastrófico | Pérdida de la ubicación primaria o de múltiples sistemas críticos simultáneamente | > 24h |

## 4. RTO/RPO POR SISTEMA CRÍTICO

Los objetivos técnicos de recuperación derivados del BIA se concretan para cada sistema crítico:

{% for sis in sistemas_criticos %}
- **{{ sis.nombre }}** — Función: {{ sis.funcion }} · RTO técnico: {{ sis.rto }} · RPO técnico: {{ sis.rpo }} · Mecanismo de recuperación: {{ sis.mecanismo }}
{% endfor %}

## 5. ARQUITECTURA DE RECUPERACIÓN

### 5.1 Sitios de operación

- **Sitio primario**: {{ ubicaciones.primario.nombre }}. Ubicación: {{ ubicaciones.primario.direccion }}. Operación habitual.
- **Sitio secundario**: {{ ubicaciones.secundario.nombre }}. Ubicación: {{ ubicaciones.secundario.direccion }}. Modalidad: {{ ubicaciones.secundario.modalidad }} (cold/warm/hot). Tiempo de activación: {{ ubicaciones.secundario.tiempo_activacion }}.

### 5.2 Replicación de datos

- **Mecanismo**: replicación asíncrona con frecuencia configurada para cumplir el RPO objetivo por sistema crítico.
- **Validación**: verificación automatizada diaria de integridad de réplicas y consistencia.
- **Monitorización**: alertas configuradas ante fallo de replicación superior a una hora.

### 5.3 Estrategia de copias de seguridad

- **Política aplicable**: E-106 Política de Copias de Seguridad.
- **Tipos**: completas semanales + incrementales diarias + transaccionales según sistema.
- **Retención**: conforme a la política E-106 (mínimo: 30 días granulares + 12 meses mensuales para sistemas críticos).
- **Ubicación**: copia primaria en sitio principal + copia secundaria en sitio alterno o servicio gestionado externo.
- **Cifrado**: en reposo y en tránsito conforme a la política E-107.
- **Pruebas de restauración**: trimestrales conforme al E-405 Plan de Pruebas.

## 6. RUNBOOKS DE RECUPERACIÓN POR SISTEMA

Cada sistema crítico cuenta con un runbook técnico documentado, accesible al personal autorizado y validado mediante ejercicios periódicos. Los runbooks incluyen:

- Diagrama de dependencias del sistema.
- Pre-requisitos y comprobaciones previas.
- Pasos detallados de recuperación con responsable asignado.
- Puntos de validación y rollback.
- Criterios de finalización exitosa.

Los runbooks operativos se mantienen en el repositorio documental técnico del sistema bajo control de versiones.

## 7. PROCEDIMIENTO DE FAILOVER, VALIDACIÓN Y FAILBACK

### 7.1 Failover

1. Confirmación formal de activación del DRP por parte del Coordinador BCP.
2. Activación del sitio secundario conforme al runbook correspondiente.
3. Reorientación del tráfico mediante DNS, balanceadores o redirección manual según diseño.
4. Validación funcional del sistema en sitio secundario.
5. Comunicación a stakeholders conforme al E-404.

### 7.2 Validación operativa

- Comprobación de integridad de datos restaurados frente al RPO esperado.
- Validación de funcionalidades críticas mediante checklist predefinido.
- Confirmación de rendimiento mínimo aceptable.
- Validación de seguridad (controles de acceso, cifrado, logging).

### 7.3 Failback

Cuando se restablece la operación normal del sitio primario:

1. Sincronización inversa de datos desde el sitio secundario.
2. Ventana de mantenimiento planificada y comunicada a stakeholders.
3. Retorno del tráfico al sitio primario.
4. Verificación funcional y operativa.
5. Cierre formal del incidente.

## 8. PRUEBAS DEL DRP

La eficacia del DRP se valida mediante el calendario de pruebas detallado en el **E-405 Plan de Pruebas de Continuidad**. Como mínimo:

- **Anuales**: ejercicio completo de failover sobre sitio secundario en ventana planificada.
- **Trimestrales**: pruebas de restauración desde copias de seguridad sobre entorno aislado.
- **Mensuales**: validación automatizada de integridad de réplicas y backups.

Los resultados se documentan en el **E-406 Informe de Pruebas de Continuidad**.

## 9. INVENTARIO DE HARDWARE/SOFTWARE CRÍTICO

El inventario actualizado de activos críticos se mantiene en el CMDB de la Entidad y se sincroniza con el alcance ENS conforme al procedimiento E-203 Gestión de Cambios. Incluye:

- Servidores físicos y virtuales con sus dependencias.
- Software con versión, licencia, fecha de fin de soporte.
- Equipos de red críticos.
- Sistemas de almacenamiento y backup.
- Sistemas de seguridad (firewalls, SIEM, EDR).

## 10. ANEXOS

- **Anexo A**: Contactos técnicos 24/7 (interno + proveedores).
- **Anexo B**: Lista de proveedores TIC críticos con cláusulas DRP en contrato.
- **Anexo C**: Licencias, claves y certificados críticos en repositorio seguro (vault corporativo).
- **Anexo D**: Diagramas de arquitectura de recuperación.
- **Anexo E**: Histórico de pruebas y lecciones aprendidas.

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
