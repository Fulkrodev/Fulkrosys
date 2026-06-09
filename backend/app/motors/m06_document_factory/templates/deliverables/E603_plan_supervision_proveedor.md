# E-603 · PLAN DE SUPERVISIÓN DE PROVEEDOR

{% set codigo = documento.codigo if documento.codigo else 'E-603' %}
{% set version = documento.version if documento.version else '1.0' %}
{% set fecha_emision = documento.fecha_emision if documento.fecha_emision else '—' %}
{% set periodo_inicio = plan_supervision.periodo_inicio if plan_supervision.periodo_inicio else fecha_emision %}
{% set periodo_fin = plan_supervision.periodo_fin if plan_supervision.periodo_fin else '—' %}
{% set nivel_proveedor = proveedor.nivel_criticidad if proveedor.nivel_criticidad else 'POR DETERMINAR' %}
{% set responsable_nombre = plan_supervision.responsable.nombre if plan_supervision.responsable and plan_supervision.responsable.nombre else cliente.responsable_seguridad.nombre if cliente.responsable_seguridad else '—' %}
{% set responsable_cargo = plan_supervision.responsable.cargo if plan_supervision.responsable and plan_supervision.responsable.cargo else 'Responsable de Seguridad' %}
{% set contacto_email = cliente.contacto_compliance.email if cliente.contacto_compliance and cliente.contacto_compliance.email else '—' %}
{% set notificacion_horas = plan_supervision.notificacion_horas if plan_supervision.notificacion_horas else 24 %}

**Documento:** {{ codigo }}
**Versión:** {{ version }}
**Fecha de emisión:** {{ fecha_emision }}
**Entidad:** {{ cliente.razon_social }} ({{ cliente.nif }})
**Proveedor objeto:** {{ proveedor.razon_social }} ({{ proveedor.nif }})
**Servicio:** {{ proveedor.servicio_descripcion }}
**Nivel de criticidad asignado:** {{ nivel_proveedor }}
**Periodo cubierto por el plan:** {{ periodo_inicio }} — {{ periodo_fin }}
**Clasificación:** Uso Interno

---

## 1. OBJETO DEL PLAN

El presente Plan de Supervisión establece la planificación y los mecanismos de control que {{ cliente.razon_social }} aplicará durante la vigencia del servicio prestado por **{{ proveedor.razon_social }}**, a efectos de:

a) Verificar el **mantenimiento sostenido** de las capacidades de seguridad evaluadas en el Informe E-602.

b) Detectar **desviaciones, degradaciones o incumplimientos** materiales en el servicio o en su entorno de seguridad.

c) Documentar las **revisiones efectuadas** conforme exige la medida `op.ext.2` (Gestión diaria) del Anexo II del RD 311/2022.

d) Cumplir la obligación de **supervisión continuada de la cadena de suministro** derivada de la NIS2 Art. 21.2.d) cuando aplique.

e) Soportar la **trazabilidad documental** requerida por los auditores ENS internos y externos.

## 2. MARCO DE REFERENCIA

Este plan se enmarca en:

- **Real Decreto 311/2022, Art. 18 y Anexo II medidas `op.ext.1` y `op.ext.2`**.
- **Reglamento (UE) 2016/679 (RGPD) Art. 28** cuando aplica.
- **Directiva (UE) 2022/2555 (NIS2) Art. 21.2.d)** cuando aplica.
- **Reglamento (UE) 2022/2554 (DORA) Art. 28-30** cuando aplica.
- Política E-112 y procedimiento E-217 vigentes en {{ cliente.razon_social }}.

## 3. FRECUENCIAS Y TIPOS DE SUPERVISIÓN

La frecuencia de las actividades de supervisión se determina conforme al nivel de criticidad **{{ nivel_proveedor }}** asignado al proveedor en el Inventario E-600:

| Tipo de actividad | Frecuencia mínima |
|-------------------|-------------------|
| Revisión documental (recertificaciones, informes auditoría) | Anual |
| Reuniones operativas con el proveedor | {% if nivel_proveedor == 'CRITICO' %}Mensual{% elif nivel_proveedor == 'ALTO' %}Trimestral{% elif nivel_proveedor == 'MEDIO' %}Semestral{% else %}Anual{% endif %} |
| Pruebas técnicas (cuando aplicable) | {% if nivel_proveedor == 'CRITICO' or nivel_proveedor == 'ALTO' %}Anual{% else %}Bienal{% endif %} |
| Revisión ad-hoc (cambios materiales, incidentes) | Inmediata al evento desencadenante |
| Reevaluación integral (re-cumplimentación E-601 abreviado) | {% if nivel_proveedor == 'CRITICO' %}Anual{% elif nivel_proveedor == 'ALTO' %}Bienal{% else %}Trienal{% endif %} |

## 4. REVISIONES DOCUMENTALES PROGRAMADAS

{% if plan_supervision.revisiones_documentales %}
| Tipo | Periodicidad | Próxima fecha | Responsable |
|------|--------------|---------------|-------------|
{% for rd in plan_supervision.revisiones_documentales %}
| {{ rd.tipo }} | {{ rd.periodicidad }} | {{ rd.proxima_fecha }} | {{ rd.responsable }} |
{% endfor %}

Documentación que el proveedor debe aportar en cada revisión documental:

{% if plan_supervision.documentos_requeridos %}
{% for doc in plan_supervision.documentos_requeridos %}
- {{ doc }}
{% endfor %}
{% else %}
- Certificaciones ISO 27001 / ENS / SOC 2 vigentes (renovadas)
- Informes de auditoría interna del periodo cerrado
- Registro de incidentes que hayan podido afectar al servicio
- Cambios materiales en subcontrataciones o transferencias internacionales
- Estado actualizado de las medidas técnicas del Anexo II del ENS
{% endif %}
{% else %}
*El calendario detallado de revisiones documentales se confirmará tras la formalización de la adenda E-604 y se registrará en el sistema FULKRO con los plazos correspondientes al nivel de criticidad asignado.*
{% endif %}

## 5. REUNIONES OPERATIVAS PROGRAMADAS

{% if plan_supervision.reuniones_operativas %}
| Frecuencia | Participantes Entidad | Participantes Proveedor | Agenda mínima |
|------------|----------------------|------------------------|---------------|
{% for r in plan_supervision.reuniones_operativas %}
| {{ r.frecuencia }} | {{ r.participantes_entidad }} | {{ r.participantes_proveedor }} | {{ r.agenda }} |
{% endfor %}
{% else %}
Las reuniones operativas se mantendrán con la frecuencia indicada en la sección 3 e incluirán, como mínimo:

- Revisión del cumplimiento de SLAs en el periodo
- Análisis de incidentes ocurridos o intentos detectados
- Estado de las medidas de mejora acordadas en revisiones anteriores
- Comunicación de cambios materiales en cualquiera de las partes
- Planificación operativa del siguiente periodo
{% endif %}

## 6. PRUEBAS TÉCNICAS

{% if plan_supervision.pruebas_tecnicas %}
| Tipo prueba | Periodicidad | Coordinación |
|-------------|--------------|--------------|
{% for pt in plan_supervision.pruebas_tecnicas %}
| {{ pt.tipo }} | {{ pt.periodicidad }} | {{ pt.coordinacion }} |
{% endfor %}
{% else %}
{% if nivel_proveedor == 'CRITICO' or nivel_proveedor == 'ALTO' %}
La Entidad se reserva el derecho a realizar las siguientes pruebas técnicas, con preaviso al proveedor de al menos 15 días naturales y coordinación operativa para evitar afectaciones al servicio:

- **Test de penetración** sobre las interfaces y servicios expuestos por el proveedor a la Entidad
- **Escaneo de vulnerabilidades** sobre los activos del proveedor que soportan el servicio
- **Revisión técnica** de configuraciones de seguridad relevantes (cifrado, controles de acceso, retención de logs)
- **Auditoría de los registros** de acceso y operación del servicio durante un periodo seleccionado
{% else %}
*Las pruebas técnicas se limitarán a la verificación documental de los informes de auditoría aportados por el proveedor, sin perjuicio de la realización de pruebas específicas en caso de incidentes o cambios materiales que las justifiquen.*
{% endif %}
{% endif %}

## 7. INDICADORES Y SLAs SUPERVISADOS

### 7.1 Indicadores SLA contractuales

{% if plan_supervision.kpis_sla %}
| Indicador | Objetivo | Umbral de alerta | Origen del dato |
|-----------|---------:|------------------|-----------------|
{% for k in plan_supervision.kpis_sla %}
| {{ k.nombre }} | {{ k.objetivo }} | {{ k.umbral_alerta }} | {{ k.origen }} |
{% endfor %}
{% else %}
| Indicador | Objetivo orientativo |
|-----------|---------------------:|
| Disponibilidad mensual del servicio | ≥ 99,5% |
| Tiempo medio de resolución incidentes | ≤ 8 horas hábiles |
| Cumplimiento ventana de notificación incidentes graves | ≤ {{ notificacion_horas }}h desde detección |
| Tiempo medio de respuesta a solicitudes operativas | ≤ 2 días hábiles |
{% endif %}

### 7.2 Indicadores específicos del cumplimiento ENS

| Indicador | Objetivo | Frecuencia medición |
|-----------|---------:|---------------------|
| Certificaciones vigentes acreditadas | 100% | Anual |
| Personal asignado al servicio con formación seguridad documentada | ≥ 95% | Anual |
| Incidentes no notificados en plazo a la Entidad | 0 | Continuo |
| Cambios materiales no comunicados previamente | 0 | Continuo |
| Subcontrataciones no autorizadas | 0 | Continuo |

## 8. NOTIFICACIÓN Y GESTIÓN DE INCIDENTES

El proveedor deberá notificar a {{ cliente.razon_social }} todo incidente que afecte o pueda afectar al servicio o a la información tratada, en un plazo máximo de **{{ notificacion_horas }} horas desde la detección**, dirigiendo la notificación al contacto operativo de compliance ({{ contacto_email }}).

Contenido mínimo de la notificación inicial:

a) Descripción del incidente y servicios afectados
b) Hora estimada de inicio y de detección
c) Tipo de información o sistemas potencialmente comprometidos
d) Medidas inmediatas adoptadas
e) Punto de contacto en el proveedor para el seguimiento

Cuando el incidente sea **significativo conforme al ENS** o afecte a **datos personales**, el proveedor colaborará con la Entidad en los procesos de notificación obligatorios a CCN-CERT, AEPD, INES, o cualquier otra autoridad competente, aportando la información requerida en los plazos legalmente aplicables.

## 9. ESCALADO ANTE HALLAZGOS Y DESVIACIONES

Cuando en el ejercicio de las actividades de supervisión se detecten desviaciones o hallazgos materiales, se aplicará el siguiente protocolo de escalado:

| Severidad | Acción | Plazo |
|-----------|--------|-------|
| **BAJA** | Comunicación operativa al proveedor solicitando subsanación | 30 días naturales |
| **MEDIA** | Apertura formal de hallazgo + plan de subsanación firmado | 15 días naturales para el plan; 60 días para la subsanación |
| **ALTA** | Reunión extraordinaria + plan de subsanación + supervisión reforzada | 5 días para reunión; 15 días para plan |
| **CRÍTICA** | Análisis interno de continuidad del contrato + activación procedimiento de salida si procede | Inmediato |

## 10. RESPONSABILIDADES INTERNAS

| Rol | Responsabilidad |
|-----|-----------------|
| Responsable de Seguridad ({{ responsable_nombre }}) | Aprobación del plan; supervisión global; decisión sobre hallazgos CRÍTICOS |
| Responsable de Compliance | Coordinación operativa con el proveedor; recepción notificaciones |
| Responsable de Sistemas | Verificación técnica; coordinación pruebas técnicas |
| Comité de Seguridad de la Información | Revisión periódica del estado del plan; aprobación cambios estructurales |

## 11. REVISIÓN DEL PLAN

El presente plan será revisado:

a) **Anualmente** con carácter ordinario por el Responsable de Seguridad.

b) **De forma extraordinaria** cuando se produzcan cambios materiales en:

- El nivel de criticidad asignado al proveedor
- El alcance del servicio prestado
- El marco normativo aplicable
- La estructura organizativa del proveedor (fusión, adquisición, cambio de control)

## 12. APROBACIÓN

| Rol | Nombre | Cargo | Fecha | Firma |
|-----|--------|-------|-------|-------|
| Elaborado por | {{ responsable_nombre }} | {{ responsable_cargo }} | {{ fecha_emision }} | |
| Revisado por | {% if cliente.responsable_sistemas %}{{ cliente.responsable_sistemas.nombre }}{% else %}—{% endif %} | {% if cliente.responsable_sistemas %}{{ cliente.responsable_sistemas.cargo }}{% else %}Responsable de Sistemas{% endif %} | | |
| Aprobado por | {% if cliente.direccion %}{{ cliente.direccion.nombre }}{% else %}—{% endif %} | {% if cliente.direccion %}{{ cliente.direccion.cargo }}{% else %}Dirección{% endif %} | | |

---

*Documento generado por FULKRO · plataforma de gestión ENS · {{ fecha_emision }}*
*Trazabilidad: este plan se vincula al `provider_id={{ proveedor.id if proveedor.id else '—' }}` y registra sus ejecuciones en las columnas `last_reviewed_at`, `next_review_date` y `next_review_owner` de la tabla `providers`.*
