# ESTRATEGIAS DE CONTINUIDAD DE NEGOCIO DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-401 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente documento de Estrategias de Continuidad ha sido elaborado por {{ responsables.consultor.nombre }}, en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

## 1. OBJETO Y MARCO NORMATIVO

El presente documento define las estrategias de continuidad de negocio de {{ cliente.razon_social }} (en adelante, "la Entidad") aplicables al sistema {{ proyecto.sistema_principal }} en su alcance {{ proyecto.alcance }}, en cumplimiento de las siguientes obligaciones:

- **Esquema Nacional de Seguridad** (Real Decreto 311/2022), Anexo II, medida **op.cont.1 Análisis de impacto** y **op.cont.2 Plan de continuidad**.
- **UNE-ISO 22301:2020** Sistemas de gestión de la continuidad del negocio.
- **UNE-ISO 22301:2020** Sistemas de gestión de la continuidad del negocio.

Este documento se complementa con el Análisis de Impacto sobre el Negocio (E-400 BIA), el Plan de Continuidad del Negocio (E-402 BCP), el Plan de Recuperación de Desastres TIC (E-403 DRP) y el Plan de Pruebas (E-405).

## 2. ALCANCE

Las estrategias documentadas aplican a los procesos de negocio críticos identificados en el BIA E-400 y a los servicios TIC sobre los que se sustentan, incluyendo personal, sistemas, instalaciones, proveedores críticos y datos.

Quedan fuera del alcance los procesos no críticos cuyo cese durante una disrupción no compromete la viabilidad del servicio principal.

## 3. PROCESOS CRÍTICOS DEL NEGOCIO

A partir del BIA se han identificado los siguientes procesos críticos con sus objetivos de recuperación:

{% for proc in procesos_criticos %}
- **{{ proc.nombre }}** ({{ proc.criticidad }}) — RTO objetivo: {{ proc.rto }} · RPO objetivo: {{ proc.rpo }}. {{ proc.descripcion }}
{% endfor %}

**RTO** (Recovery Time Objective): tiempo máximo aceptable entre la disrupción y la recuperación operativa del proceso.
**RPO** (Recovery Point Objective): pérdida máxima aceptable de datos medida en tiempo.

## 4. ESTRATEGIAS POR PROCESO CRÍTICO

Para cada proceso crítico identificado se ha definido al menos una estrategia de continuidad alineada con su RTO/RPO:

{% for est in estrategias %}
- **{{ est.proceso }}** — Estrategia: {{ est.estrategia }} · Coste estimado: {{ est.coste_estimado }} · Responsable: {{ est.responsable }} · Plazo: {{ est.plazo }}
{% endfor %}

Las estrategias contempladas por la Entidad incluyen, según aplique:

- **Redundancia activa**: duplicación de componentes críticos en operación continua (active-active).
- **Sitio alterno (cold/warm/hot)**: infraestructura en ubicación distinta capaz de asumir la carga total o parcial.
- **Acuerdos de servicio con terceros**: contratos de respaldo con proveedores capaces de prestar el servicio temporalmente.
- **Recuperación desde copias de seguridad**: reconstrucción desde backups conforme a la política de copias E-106.
- **Procedimiento manual de contingencia**: ejecución del proceso sin sistemas TIC durante un tiempo acotado.
- **Reducción controlada del servicio**: prestación parcial priorizando funciones esenciales.

## 5. RECURSOS MÍNIMOS REQUERIDOS

La activación de las estrategias anteriores requiere disponibilidad asegurada de los siguientes recursos:

### 5.1 Personas

- Equipo de gestión de la crisis (Comité de Continuidad).
- Equipos operativos por proceso crítico con suplentes designados.
- Personal técnico TIC con acceso a procedimientos de recuperación.
- Personal autorizado para la toma de decisiones financieras y contractuales.

### 5.2 Sistemas e infraestructura

- Sistemas redundantes o de respaldo conforme al BIA.
- Copias de seguridad accesibles y validadas (política E-106).
- Conectividad de respaldo (líneas alternas, 4G/5G de emergencia).
- Inventario actualizado de software crítico y licencias.

### 5.3 Localizaciones alternas

{% for ubic in ubicaciones_alternas %}- **{{ ubic.nombre }}**: {{ ubic.direccion }}. Capacidad: {{ ubic.capacidad }}. Tiempo de activación: {{ ubic.tiempo_activacion }}.
{% endfor %}

### 5.4 Proveedores críticos

{% for prov in proveedores_criticos %}- **{{ prov.nombre }}** ({{ prov.tipo_servicio }}). SLA contractual: {{ prov.sla }}. Contacto de emergencia: {{ prov.contacto_emergencia }}.
{% endfor %}

## 6. INVERSIÓN Y PLAN FINANCIERO

La Entidad asigna anualmente una partida presupuestaria específica para la continuidad de negocio, que incluye:

- Mantenimiento de la infraestructura de respaldo.
- Renovación de contratos con proveedores críticos y sitios alternos.
- Ejercicios de prueba conforme al E-405.
- Formación y concienciación al personal involucrado.
- Auditoría externa periódica del BCMS.

El presupuesto anual estimado para el período en vigor asciende a la cantidad consignada en el plan económico aprobado por {{ cliente.organo_aprobador_politicas }}.

## 7. COMUNICACIÓN A STAKEHOLDERS

Las estrategias de continuidad se comunican a:

- **Personal interno**: vía Intranet y sesiones de concienciación.
- **Clientes**: cláusulas contractuales SLA y portal cliente cuando proceda.
- **Proveedores críticos**: contratos de encargo y acuerdos de nivel de servicio.
- **Autoridades**: cuando se requiera notificación (op.exp.7, RGPD-ART-33, NIS2-ART-23).

El detalle del proceso de comunicación durante la activación de una contingencia se desarrolla en el Plan de Comunicaciones en Crisis E-404.

## 8. REVISIÓN Y ACTUALIZACIÓN

Las presentes estrategias se revisan con periodicidad **anual** y siempre que se produzcan:

- Cambios significativos en los procesos críticos identificados.
- Incorporación o baja de proveedores críticos.
- Modificación del alcance del sistema bajo ENS.
- Lecciones aprendidas tras un ejercicio (E-406) o incidente real.
- Cambios normativos relevantes (ENS, NIS2, DORA).

La aprobación de cada revisión corresponde a {{ cliente.organo_aprobador_politicas }}, previa propuesta de {{ responsables.responsable_seguridad.nombre }}.

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
