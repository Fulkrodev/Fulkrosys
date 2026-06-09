# CORRECCIONES C-3, C-4, C-7, C-8 — BLOQUE CONSOLIDADO

**Plan 100/100 FULKRO — Parche de auditoría**
**Fecha:** 10 de abril de 2026

---

# CORRECCIÓN C-3 — CLÁUSULA DE RECURSOS DEL CLIENTE PARA C-001

**v2.1 §3.1.6 la llama "lo más importante de la Fase −1 y lo que más proyectos salva". Esta cláusula se inserta en el contrato C-001 como nueva Cláusula Quinta Bis, entre la Quinta (Obligaciones del Cliente) y la Sexta (Incompatibilidad).**

```jinja

### QUINTA BIS — RECURSOS Y COMPROMISOS DEL CLIENTE (CLÁUSULA CRÍTICA)

5bis.1. **El Cliente reconoce que el éxito del proyecto depende de manera determinante de su colaboración activa y oportuna.** A tal efecto, el Cliente se compromete a proporcionar los siguientes recursos en los plazos y condiciones que se indican:

**A) Recursos humanos:**

a) Un **interlocutor único** con capacidad de decisión operativa sobre el proyecto, identificado con nombre y datos de contacto al inicio de la Fase 0, y con disponibilidad mínima garantizada de:
   - **4 horas semanales** durante las Fases 0 y 1 (Pre-arranque y Diagnóstico).
   - **8 horas semanales** durante las Fases 2 y 3 (Diseño e Implantación).
   - **4 horas semanales** durante las Fases 4 a 7 (Verificación a Auditoría).

b) Acceso al **Responsable TI o equivalente** del Cliente con disponibilidad suficiente para las entrevistas de diagnóstico, la configuración de controles técnicos y la respuesta a consultas técnicas del Consultor.

c) Acceso al **Responsable legal o DPO** cuando los servicios requieran coordinación en materia de protección de datos personales.

d) Acceso al **órgano superior** del Cliente para la firma formal de los documentos que así lo requieran (Política de Seguridad, Declaración de Aplicabilidad, acta de nombramiento de roles, acta de aceptación de riesgos residuales), en un plazo máximo de **15 días hábiles** desde que el Consultor los presente para firma.

**B) Recursos técnicos:**

a) Acceso de solo lectura a la CMDB, directorio activo, configuración cloud, SIEM y demás sistemas necesarios para el diagnóstico técnico, en los primeros **10 días hábiles** desde el inicio de la Fase 1.

b) Posibilidad de ejecutar los escaneos de seguridad autorizados durante las ventanas horarias pactadas, conforme al Anexo III del presente contrato.

c) Entrega de toda la documentación existente relevante (políticas previas, informes de auditoría, contratos con proveedores, inventarios) en los primeros **10 días hábiles** desde el inicio del proyecto.

**C) Recursos organizativos:**

a) Comunicación formal del CEO o máximo responsable del Cliente al personal de la organización anunciando el proyecto de certificación ENS, su importancia estratégica y la obligación de colaborar con el Consultor, en los primeros **5 días hábiles** desde la firma del contrato.

b) Disponibilidad del personal del Cliente para las entrevistas de diagnóstico en los plazos razonables que proponga el Consultor.

c) Acta de constitución del Comité de Seguridad de la Información firmada antes de finalizar la Fase 0.

**D) Consecuencias del incumplimiento:**

5bis.2. **Parones documentados.** Cada retraso imputable al Cliente en el cumplimiento de los compromisos descritos en los apartados A), B) y C) anteriores generará un **parón documentado del cronograma**, que el Consultor registrará por escrito indicando: compromiso incumplido, fecha comprometida, fecha real (o pendiente), impacto en el cronograma y acciones propuestas.

5bis.3. **Facturación del tiempo de espera.** Si un parón documentado supera los **10 días hábiles consecutivos**, el Consultor podrá facturar al Cliente en concepto de **tiempo de espera** una compensación equivalente al **50% de la tarifa horaria pactada** por cada hora de Marcos que quede bloqueada como consecuencia del parón, con un tope mensual equivalente al **25% de la cuota mensual** del proyecto. Esta compensación será exigible mediante factura adicional con desglose del parón y se abonará en el plazo de la cláusula tercera.

5bis.4. **Suspensión del proyecto.** Si un parón documentado supera los **30 días hábiles consecutivos**, el Consultor podrá **suspender formalmente el proyecto**, notificándolo por escrito al Cliente. La suspensión implicará:

a) Congelación del cronograma hasta que el Cliente resuelva los compromisos pendientes.

b) Recálculo del cronograma y, en su caso, del presupuesto al reanudar.

c) La suspensión no exime al Cliente del pago de los servicios ya prestados ni del tiempo de espera acumulado.

5bis.5. **Resolución por incumplimiento.** Si un parón documentado supera los **60 días hábiles consecutivos**, el Consultor podrá **resolver el contrato** conforme a la cláusula undécima, conservando el derecho a los pagos ya realizados y a la facturación de los servicios prestados hasta la fecha de resolución.

5bis.6. **Tracker de recursos.** La plataforma del Consultor mantendrá un registro automatizado de los compromisos del Cliente (`client_commitments`), con fecha comprometida, fecha real y desviaciones. Cada semana el Consultor podrá enviar al Cliente un **informe de cumplimiento de recursos** como recordatorio preventivo. Este informe no tiene carácter sancionador sino informativo, y su no emisión no exime al Cliente de los compromisos asumidos.

```

---

# CORRECCIÓN C-4 — RECONCILIACIÓN DEL EFFORT ESTIMATOR

**Las horas base del Entregable D+E (45/120/220) se actualizan a las de v2.1 Apéndice N (60/150/230). La tarifa de referencia se fija en 95 €/h como default pero con 110 €/h como alternativa para clientes premium.**

## Cambios concretos a aplicar en el fichero D+E

### Tabla de horas base (actualizar en §E.5)

| Categoría | D+E actual | v2.1 Apéndice N | **NUEVO VALOR** |
|---|---|---|---|
| Básica | 45 h | 60 h | **60 h** |
| Media | 120 h | 150 h | **150 h** |
| Alta | 220 h | 230 h | **230 h** |

### Tarifa de referencia (actualizar en §E.3 y §E.6)

| Concepto | D+E actual | v2.1 ejemplo | **DECISIÓN** |
|---|---|---|---|
| Tarifa default | 95 €/h | 110 €/h | **95 €/h se mantiene como default** (Marcos está empezando, 95 es su sweet spot para captar primeros clientes). El D+E ya contempla un rango 85-110 €/h que es correcto. **110 €/h se usa en los ejemplos de proyectos premium.** |

### Factor cloud (mantener)

El D+E incluye un `factor_cloud` que v2.1 no tiene. **Se mantiene** porque es una mejora real: los proyectos con entorno multi-cloud consumen más horas y el estimador debe reflejarlo.

### Líneas concretas a cambiar en el pseudocódigo Python del Motor 17 (§E.9)

```python
# ANTES (D+E actual):
HORAS_BASE = {
    CategoriaENS.BASICA: 45,
    CategoriaENS.MEDIA: 120,
    CategoriaENS.ALTA: 220,
}

# DESPUÉS (reconciliado con v2.1):
HORAS_BASE = {
    CategoriaENS.BASICA: 60,
    CategoriaENS.MEDIA: 150,
    CategoriaENS.ALTA: 230,
}
```

### Impacto en los 5 escenarios canónicos del §E.7

Los escenarios deben recalcularse con las nuevas horas base. Ejemplo del Escenario 2 (PYME mediana categoría MEDIA):

```
# ANTES: 120 × 1.00 × 1.15 × 1.00 × 1.00 × 1.00 = 138 h → 13.110 € 
# DESPUÉS: 150 × 1.00 × 1.15 × 1.00 × 1.00 × 1.00 = 172.5 h → 16.387 €
```

### Impacto en la propuesta P-001

Los honorarios calculados automáticamente por el Motor 17 subirán un ~20-25% con las nuevas horas base. Esto es más realista para el mercado español actual y se alinea con las tarifas que Marcos ha investigado.

---

# CORRECCIÓN C-7 — 8 PLANTILLAS COMERCIALES DEL APÉNDICE F

**v2.1 define 10 plantillas en el Apéndice F tabla F.11. Ya tenemos P-001 (F.2) y C-003 (F.9). Faltan 8.**

## F.1 — PLANTILLA DE REUNIÓN EXPLORATORIA

**Es la herramienta más valiosa del día a día de Marcos. v2.1 §3.1.3 le dedica 3 páginas con 6 bloques de preguntas.**

```jinja
---
codigo_documento: "F-001"
titulo: "Guión de Reunión Exploratoria Gratuita"
tipo: "plantilla_reunion"
duracion_estimada: "45-60 minutos"
---

# GUIÓN DE REUNIÓN EXPLORATORIA — {{ lead.empresa }}

**Fecha:** {{ reunion.fecha }}
**Asistentes cliente:** {{ reunion.asistentes_cliente }}
**Consultor:** Marcos Mata García — FULKRO

**REGLA DE ORO:** Si Marcos habla más del 40% del tiempo, lo está haciendo mal.

---

## BLOQUE A — CONTEXTO DE NEGOCIO (5-8 min)

| # | Pregunta | Respuesta |
|---|---|---|
| A.1 | ¿A qué se dedica exactamente la empresa? | {{ bloqueA.actividad }} |
| A.2 | ¿Cuántas personas son? | {{ bloqueA.empleados }} |
| A.3 | ¿Qué porcentaje del negocio depende del sector público? | {{ bloqueA.pct_sector_publico }}% |
| A.4 | ¿En qué comunidades autónomas operan? | {{ bloqueA.ccaa }} |
| A.5 | ¿Qué sectores públicos son clientes? (ayuntamientos, sanidad, educación, justicia) | {{ bloqueA.sectores_publicos }} |
| A.6 | ¿Hay contratos públicos en curso? ¿Cuántos? ¿Valor aproximado? | {{ bloqueA.contratos_en_curso }} |

## BLOQUE B — CONTEXTO DEL REQUISITO ENS (10-15 min)

| # | Pregunta | Respuesta |
|---|---|---|
| B.1 | ¿Cómo les ha llegado la obligación ENS? (pliego, cliente recurrente, proactividad) | {{ bloqueB.origen_obligacion }} |
| B.2 | ¿Tienen un pliego concreto donde se exija? → **Pedir que lo suban ahora** | {{ bloqueB.pliego_disponible }} |
| B.3 | ¿Qué categoría cree el cliente que necesita? | {{ bloqueB.categoria_percibida }} |
| B.4 | ¿Hay plazo marcado? ¿Penalización contractual si no se cumple? | {{ bloqueB.plazo_limite }} |
| B.5 | ¿Han intentado ya esta certificación con otro consultor? | {{ bloqueB.intento_previo }} |
| B.6 | ¿Conocen alguna empresa certificada ENS en su sector? | {{ bloqueB.referencia_sector }} |

## BLOQUE C — MADUREZ ACTUAL (10-15 min)

| # | Pregunta | Respuesta |
|---|---|---|
| C.1 | ¿Tienen ISO 27001, RGPD formalizado, otra certificación? | {{ bloqueC.certificaciones }} |
| C.2 | ¿Tienen política de seguridad escrita? ¿Cuándo se aprobó? | {{ bloqueC.politica_seguridad }} |
| C.3 | ¿Tienen DPO? ¿Interno o externo? | {{ bloqueC.dpo }} |
| C.4 | ¿Tienen un responsable de seguridad identificado? | {{ bloqueC.rseg }} |
| C.5 | ¿Tienen SIEM, EDR, MFA universal, backups probados? | {{ bloqueC.controles_tecnicos }} |
| C.6 | ¿Han sufrido un incidente grave en los últimos 3 años? | {{ bloqueC.incidente_previo }} |
| C.7 | ¿Han hecho pentest alguna vez? ¿Cuándo el último? | {{ bloqueC.pentest }} |
| C.8 | ¿Qué cloud usan? (AWS, Azure, GCP, M365, on-premise) | {{ bloqueC.cloud }} |

## BLOQUE D — ORGANIZACIÓN INTERNA (5-8 min)

| # | Pregunta | Respuesta |
|---|---|---|
| D.1 | ¿Quién es el sponsor del proyecto? | {{ bloqueD.sponsor }} |
| D.2 | ¿Tienen equipo TI interno? ¿Cuántas personas? ¿Perfil? | {{ bloqueD.equipo_ti }} |
| D.3 | ¿Tienen equipo legal? ¿Interno o externo? | {{ bloqueD.equipo_legal }} |
| D.4 | ¿Quién firma contratos? ¿Quién autoriza presupuestos? | {{ bloqueD.firmante }} |
| D.5 | ¿Hay algún tema político interno? (fusiones, reestructuraciones) | {{ bloqueD.contexto_politico }} |

## BLOQUE E — EXPECTATIVAS Y RESTRICCIONES (5-10 min)

| # | Pregunta | Respuesta |
|---|---|---|
| E.1 | ¿Qué plazo consideran razonable? | {{ bloqueE.plazo_esperado }} |
| E.2 | ¿Cuál sería el desastre en este proyecto? | {{ bloqueE.peor_escenario }} |
| E.3 | ¿Qué rango de presupuesto les parece razonable? | {{ bloqueE.presupuesto }} |
| E.4 | ¿Quieren solo declaración de conformidad o certificación ENAC formal? | {{ bloqueE.objetivo_certificacion }} |
| E.5 | ¿Necesitan mantenimiento post-certificación? | {{ bloqueE.retainer }} |

## BLOQUE F — CIERRE (5 min)

| # | Acción |
|---|---|
| F.1 | Marcos resume lo entendido en 2-3 frases |
| F.2 | Marcos promete enviar propuesta formal en **5 días hábiles** |
| F.3 | Marcos pregunta si tienen alguna duda |
| F.4 | Marcos confirma los próximos pasos y agradece el tiempo |

---

## PANEL EN VIVO DEL AGENTE 18 (se rellena automáticamente)

| Métrica | Valor estimado |
|---|---|
| Categoría ENS preliminar | {{ agente18.categoria_estimada }} |
| Madurez actual estimada (L0-L5) | {{ agente18.madurez_estimada }} |
| Horas Marcos estimadas | {{ agente18.horas_estimadas }} |
| Plazo viable | {{ agente18.plazo_viable }} |
| Riesgos del proyecto detectados | {{ agente18.riesgos }} |
| Quick wins potenciales | {{ agente18.quick_wins }} |

```

## F.3 — PLANTILLA DE REUNIÓN DE NEGOCIACIÓN

```jinja
---
codigo_documento: "F-003"
titulo: "Guión de Reunión de Negociación"
tipo: "plantilla_reunion"
---

# REUNIÓN DE NEGOCIACIÓN — {{ lead.empresa }}

**Propuesta enviada:** P-001 v{{ propuesta.version }} del {{ propuesta.fecha_emision }}

## PUNTOS NEGOCIABLES (rangos pre-cargados por Marcos)

| Punto | Valor propuesto | Rango aceptable Marcos | Petición del cliente |
|---|---|---|---|
| Precio total | {{ propuesta.honorarios_marcos }} € | {{ negociacion.precio_min }}-{{ negociacion.precio_max }} € | {{ negociacion.precio_cliente }} € |
| Plazo | {{ propuesta.duracion_meses }} meses | +{{ negociacion.plazo_flex_semanas }} semanas máx | {{ negociacion.plazo_cliente }} |
| Forma de pago | {{ propuesta.modalidad_pago }} | Flexible entre las 3 modalidades | {{ negociacion.pago_cliente }} |
| Alcance | Conforme a P-001 | Reducible si se reduce precio | {{ negociacion.alcance_cliente }} |

## REGLAS DEL AGENTE 20

Si un ajuste queda fuera del rango aceptable, el Agente 20 propone alternativas:
- Reducir alcance (excluir phishing, excluir pentesting, excluir retainer)
- Extender plazo (reduce presión, mismo coste)
- Pago diferido (50% inicio, 50% a 90 días)
- Eliminar entregables opcionales

## AL CIERRE → GENERAR CONTRATO C-001

```

## F.4 — CLÁUSULA RECURSOS DEL CLIENTE (ya entregada en C-3 arriba)

*Referencia: Corrección C-3 de este mismo documento.*

## F.5 — PLANTILLA DE PLAN DE PROYECTO

```jinja
---
codigo_documento: "F-005"
titulo: "Plan de Proyecto ENS"
tipo: "plan_proyecto"
---

# PLAN DE PROYECTO ENS — {{ cliente.razon_social }}

## 1. DATOS DEL PROYECTO

| Concepto | Valor |
|---|---|
| Cliente | {{ cliente.razon_social }} |
| Categoría ENS | {{ proyecto.categoria_ens }} |
| Duración | {{ proyecto.duracion_meses }} meses |
| Inicio | {{ proyecto.fecha_inicio }} |
| Fin previsto | {{ proyecto.fecha_fin }} |

## 2. WBS (Work Breakdown Structure)

{% for fase in proyecto.fases %}
### Fase {{ loop.index }} — {{ fase.nombre }} (S{{ fase.semana_inicio }}-S{{ fase.semana_fin }})

{% for tarea in fase.tareas %}
- [ ] {{ tarea.nombre }} — Resp: {{ tarea.responsable }} — Plazo: {{ tarea.plazo }}
{% endfor %}

**Hito de cierre:** {{ fase.hito }}
**Entregables:** {{ fase.entregables | join(', ') }}

{% endfor %}

## 3. DEPENDENCIAS CRÍTICAS

{% for dep in proyecto.dependencias %}
- {{ dep.tarea_origen }} → {{ dep.tarea_destino }} ({{ dep.tipo }})
{% endfor %}

## 4. RECURSOS DEL CLIENTE (conforme a Cláusula 5bis del C-001)

| Compromiso | Responsable cliente | Fecha límite | Estado |
|---|---|---|---|
| Comunicación CEO al personal | {{ cliente.firmante.nombre_completo }} | S+1 | {{ tracker.ceo_comunicacion }} |
| Entrega documentación existente | {{ cliente.persona_contacto.nombre }} | S+2 | {{ tracker.documentacion }} |
| Constitución Comité Seguridad | {{ cliente.persona_contacto.nombre }} | S+2 | {{ tracker.comite }} |
| Accesos técnicos diagnóstico | Resp. TI del cliente | S+3 | {{ tracker.accesos }} |

```

## F.6 — PLANTILLA DE PLAN DE COMUNICACIÓN

```jinja
---
codigo_documento: "F-006"
titulo: "Plan de Comunicación del Proyecto"
---

# PLAN DE COMUNICACIÓN — {{ cliente.razon_social }}

## CANALES

| Canal | Uso | Frecuencia |
|---|---|---|
| Email corporativo | Comunicaciones formales, envío de entregables | Según necesidad |
| Videoconferencia (LiveKit/Meet) | Reuniones de seguimiento, workshops | {{ comunicacion.frecuencia_reuniones }} |
| Plataforma FULKRO (magic links) | Firma de documentos, subida de evidencias, consultas | Continuo |
| Teléfono | Urgencias, escalado | Solo urgencias |

## REUNIONES PERIÓDICAS

| Tipo | Asistentes | Frecuencia | Duración |
|---|---|---|---|
| Seguimiento operativo | Marcos + interlocutor cliente | Semanal | 30 min |
| Revisión de hitos | Marcos + sponsor + interlocutor | Quincenal | 60 min |
| Comité de dirección | Marcos + dirección cliente | Mensual | 45 min |

## INFORMES

| Informe | Destinatario | Frecuencia |
|---|---|---|
| Ficha Resumen Ejecutivo (E-001) | Dirección del cliente | Por hito |
| Informe de cumplimiento de recursos | Interlocutor cliente | Semanal |
| Dashboard de avance | Sponsor | Continuo (FULKRO) |

```

## F.7 — PLANTILLA DE PLAN DE RIESGOS DEL PROYECTO

```jinja
---
codigo_documento: "F-007"
titulo: "Plan de Gestión de Riesgos del Proyecto"
---

# RIESGOS DEL PROYECTO ENS — {{ cliente.razon_social }}

**Nota:** Estos son riesgos del PROYECTO (gestión), no del SISTEMA (seguridad). El análisis de riesgos MAGERIT del sistema se hace en la Fase 1.

## REGISTRO DE RIESGOS

| ID | Riesgo | Probabilidad | Impacto | Nivel | Mitigación |
|---|---|---|---|---|---|
| R-01 | El cliente no proporciona la documentación existente en plazo | Media | Alto | 🟠 | Cláusula 5bis + escalado al sponsor |
| R-02 | El sponsor pierde interés o cambia de puesto | Baja | Muy Alto | 🔴 | Identificar sponsor alternativo en la exploratoria |
| R-03 | Madurez real muy inferior a la declarada en la exploratoria | Media | Alto | 🟠 | Diagnóstico exhaustivo en Fase 1 antes de comprometer el cronograma |
| R-04 | Cambio normativo durante el proyecto (modificación del RD 311/2022) | Baja | Medio | 🟡 | Motor 24 Regulatory Radar monitorizando BOE |
| R-05 | Auditor externo detecta NC mayor no prevista | Media | Alto | 🟠 | Auditoría interna exhaustiva en Fase 4 con simulacro |
| R-06 | Proveedor crítico del cliente no colabora (no entrega evidencias) | Media | Medio | 🟡 | Presionar vía cláusula contractual cliente-proveedor |
| R-07 | Presupuesto del cliente insuficiente para las inversiones técnicas identificadas | Media | Alto | 🟠 | Identificar alternativas open source / low cost |
{% for riesgo in proyecto.riesgos_adicionales %}
| R-{{ '%02d' % (loop.index + 7) }} | {{ riesgo.descripcion }} | {{ riesgo.probabilidad }} | {{ riesgo.impacto }} | {{ riesgo.nivel }} | {{ riesgo.mitigacion }} |
{% endfor %}

```

## F.8 — PLANTILLA DE KICK-OFF EJECUTIVO

```jinja
---
codigo_documento: "F-008"
titulo: "Presentación de Kick-Off del Proyecto ENS"
tipo: "presentacion"
duracion: "60 minutos"
---

# KICK-OFF — PROYECTO DE CERTIFICACIÓN ENS

## {{ cliente.razon_social }}

**Fecha:** {{ proyecto.fecha_inicio }}
**Asistentes:** Dirección del cliente + Marcos Mata García (FULKRO)

---

### AGENDA (60 min)

| Bloque | Contenido | Tiempo |
|---|---|---|
| 1 | Presentación de FULKRO y de Marcos | 5 min |
| 2 | Recordatorio del objetivo: certificación ENS {{ proyecto.categoria_ens }} | 5 min |
| 3 | Alcance confirmado (servicios, sistemas, sedes, exclusiones) | 10 min |
| 4 | Roles ENS: qué son, quién los asume, qué implica | 10 min |
| 5 | Cronograma de las {{ proyecto.fases | length }} fases con hitos | 10 min |
| 6 | Compromisos del cliente (Cláusula 5bis) — qué necesitamos y cuándo | 10 min |
| 7 | Próximos pasos inmediatos (Fase 0) | 5 min |
| 8 | Preguntas | 5 min |

### ACCIONES INMEDIATAS TRAS EL KICK-OFF

- [ ] CEO envía comunicación al personal anunciando el proyecto (≤ 5 días)
- [ ] Cliente entrega documentación existente (≤ 10 días)
- [ ] Se firma acta de constitución del Comité de Seguridad (≤ 10 días)
- [ ] Se designan formalmente los 4 roles ENS (≤ 10 días)
- [ ] Marcos recibe accesos técnicos para diagnóstico (≤ 10 días)

```

## F.10 — PLANTILLA DEL INFORME DE DIAGNÓSTICO (E-090)

```jinja
---
codigo_documento: "E-090"
titulo: "Informe de Diagnóstico Exhaustivo"
tipo: "entregable_fase_1"
---

# INFORME DE DIAGNÓSTICO EXHAUSTIVO — {{ cliente.razon_social }}

**Documento E-090 · Versión {{ diagnostico.version }} · {{ diagnostico.fecha }}**

---

## 1. RESUMEN EJECUTIVO

{{ diagnostico.resumen_ejecutivo }}

## 2. ALCANCE DEL DIAGNÓSTICO

| Concepto | Detalle |
|---|---|
| Periodo de diagnóstico | {{ diagnostico.fecha_inicio }} a {{ diagnostico.fecha_fin }} |
| Personas entrevistadas | {{ diagnostico.personas_entrevistadas }} |
| Sistemas analizados | {{ diagnostico.sistemas_analizados }} |
| Sedes visitadas | {{ diagnostico.sedes_visitadas }} |

## 3. HALLAZGOS POR DOMINIO

### 3.1 Organizativo (Motor 21)

- Mapa de stakeholders
- Procesos de negocio críticos
- Obligaciones legales y contractuales aplicables
- Estado de madurez organizativa: **{{ diagnostico.madurez_organizativa }}**

### 3.2 Técnico (Motor 22)

- Inventario de activos descubiertos: {{ diagnostico.activos_total }}
- Estado de identidades y accesos
- Estado de protección de datos
- Estado de configuraciones
- Vulnerabilidades detectadas: {{ diagnostico.vulnerabilidades_total }}
- Estado de logging y monitorización
- Estado de continuidad
- Madurez técnica: **{{ diagnostico.madurez_tecnica }}**

### 3.3 Proveedores

- Inventario: {{ diagnostico.proveedores_total }} proveedores identificados
- Críticos: {{ diagnostico.proveedores_criticos }}
- Cumplimiento estimado: **{{ diagnostico.cumplimiento_proveedores }}**

### 3.4 Documental

| Documento | Existe | Vigente | Conforme ENS |
|---|---|---|---|
{% for doc in diagnostico.documentacion %}
| {{ doc.nombre }} | {{ doc.existe }} | {{ doc.vigente }} | {{ doc.conforme }} |
{% endfor %}

## 4. MAPA DE CALOR DE CRITICIDAD

{{ diagnostico.heatmap }}

## 5. COMPARATIVA CONTRA ENS {{ proyecto.categoria_ens }}

### Por familia de medidas

| Familia | Aplicables | Conformes | % | Estado |
|---|---|---|---|---|
{% for familia in diagnostico.comparativa_ens %}
| {{ familia.codigo }} | {{ familia.aplicables }} | {{ familia.conformes }} | {{ familia.porcentaje }}% | {{ familia.estado }} |
{% endfor %}

### Nivel de madurez actual estimado por medida (L0-L5)

{{ diagnostico.tabla_madurez_por_medida }}

## 6. ESTIMACIÓN DE ESFUERZO

Conforme al Effort Estimator (Motor 17):

| Concepto | Valor |
|---|---|
| Horas Marcos estimadas | {{ diagnostico.horas_estimadas }} h |
| Plazo viable | {{ diagnostico.plazo_viable }} meses |
| Inversiones técnicas necesarias | ~{{ diagnostico.inversiones_estimadas }} € |

## 7. RIESGOS DEL PROYECTO IDENTIFICADOS

{% for riesgo in diagnostico.riesgos %}
- **{{ riesgo.id }}**: {{ riesgo.descripcion }} ({{ riesgo.probabilidad }} / {{ riesgo.impacto }})
{% endfor %}

## 8. QUICK WINS

{% for qw in diagnostico.quick_wins %}
- {{ qw }}
{% endfor %}

## 9. RECOMENDACIONES PARA FASE 2

{{ diagnostico.recomendaciones }}

```

---

# CORRECCIÓN C-8 — SYSTEM PROMPTS DE LOS AGENTES 17-20

**Estos son los 4 agentes de la Fase −1 (Pipeline Comercial) definidos en v2.1 §3.1.2-3.1.5.**

## AGENTE 17 — CUALIFICADOR COMERCIAL

```python
AGENT_17_SYSTEM_PROMPT = """Eres el Agente 17 de FULKRO: Cualificador Comercial.

Tu función: evaluar un lead entrante y producir un Lead Score de 0-100 con \
clasificación A/B/C y recomendación de acción.

DATOS QUE RECIBES:
- Información del lead: empresa, sector, tamaño, origen (Radar/referencia/frío)
- Respuestas de Marcos a las 8 preguntas de cualificación (puede haber "no sé")

LAS 8 PREGUNTAS DE CUALIFICACIÓN:
1. ¿Contrato adjudicado, licitando, o solo explorando?
2. ¿Categoría ENS que parece exigir el pliego?
3. ¿Plazo legal o contractual?
4. ¿Sponsor identificado con poder de decisión?
5. ¿Presupuesto asignado o "lo están estudiando"?
6. ¿Personal técnico propio o solo dirección?
7. ¿RGPD, ISO 27001 u otro marco existente?
8. ¿Lead por referencia o frío?

SCORING:
- Contrato adjudicado = +25 pts, licitando = +15, explorando = +5
- Categoría conocida = +10, desconocida = +5
- Plazo < 6 meses = +15, 6-12 meses = +10, sin plazo = +5
- Sponsor claro = +15, difuso = +5
- Presupuesto asignado = +10, "estudiando" = +3
- Equipo TI propio = +5
- ISO 27001 o equivalente = +10, RGPD formal = +5
- Referencia = +10, frío = +0

CLASIFICACIÓN:
- A (≥70): PRIORIZAR — agendar exploratoria esta semana
- B (40-69): REUNIÓN EXPLORATORIA — agendar en 2 semanas
- C (20-39): EDUCAR — enviar contenido, mantener en pipeline
- < 20: DESCARTAR o APARCAR

OUTPUT: JSON con lead_score, classification, recommendation, reasoning.
Sé conciso y directo. No inventes datos que no tienes.
"""
```

## AGENTE 18 — ASISTENTE DE REUNIÓN EXPLORATORIA

```python
AGENT_18_SYSTEM_PROMPT = """Eres el Agente 18 de FULKRO: Asistente de Reunión Exploratoria.

Tu función: mientras Marcos introduce las respuestas del cliente durante la \
reunión exploratoria (bloques A-F del guión F-001), tú calculas en tiempo real:

1. CATEGORÍA ENS PRELIMINAR:
   - Analiza las respuestas de los bloques A+B para estimar si el sistema \
     será BÁSICA, MEDIA o ALTA.
   - Factores clave: tipo de información tratada, si hay datos personales \
     de categorías especiales, si el servicio es crítico para el organismo público.

2. MADUREZ ACTUAL ESTIMADA (L0-L5):
   - L0: Sin nada. Ni política ni controles.
   - L1: Algo ad-hoc, sin documentar.
   - L2: Políticas básicas, RGPD parcial.
   - L3: RGPD ok + políticas + algunos controles técnicos.
   - L4: Equivalente ISO 27001 (alto).
   - L5: Certificado equivalente vigente.
   Usa las respuestas del bloque C.

3. ESTIMACIÓN PRELIMINAR DE ESFUERZO:
   - Aplica la fórmula del Apéndice N: horas_base(categoría) × factor_tamaño \
     × factor_madurez × factor_sector × factor_complejidad.
   - Base: BÁSICA=60h, MEDIA=150h, ALTA=230h.

4. PLAZOS VIABLES vs DESEADOS:
   - Si el cliente quiere 3 meses y la estimación dice 6: señalarlo como riesgo.

5. RIESGOS DEL PROYECTO DETECTADOS:
   - Sin sponsor claro → RIESGO ALTO
   - Plazo imposible → RIESGO ALTO
   - Presupuesto < estimación × 0.7 → RIESGO MEDIO
   - Sin equipo TI → impacta esfuerzo

6. QUICK WINS:
   - Si ya tienen RGPD formal → reutilizar para ENS
   - Si ya tienen ISO 27001 → mapear controles
   - Si ya tienen MFA → evidencia directa para op.acc.6

OUTPUT: JSON actualizado con cada campo tras cada bloque completado.
Nunca afirmes certezas: usa "estimación preliminar" y "sujeto a diagnóstico".
"""
```

## AGENTE 19 — REDACTOR DE PROPUESTAS COMERCIALES

```python
AGENT_19_SYSTEM_PROMPT = """Eres el Agente 19 de FULKRO: Redactor de Propuestas Comerciales.

Tu función: generar el contenido personalizado de la propuesta P-001 a partir \
de los datos recogidos en la reunión exploratoria (almacenados en \
exploratory_meetings) y de las estimaciones del Motor 17.

ESTRUCTURA DE P-001 (15 secciones conforme a v2.1):
1. Portada
2. Resumen ejecutivo
3. Contexto entendido (lo que hemos comprendido del cliente)
4. Alcance propuesto
5. Metodología (10 fases)
6. Fases con cronograma
7. Entregables por fase
8. Equipo
9. Supuestos y exclusiones
10. Condiciones económicas
11. Criterios de aceptación
12. Gestión de riesgos del proyecto
13. Política de confidencialidad
14. Validez de la oferta
15. Anexos

REGLAS DE REDACCIÓN:
- Español formal de usted, profesional pero no frío.
- La sección 3 (Contexto entendido) es donde el cliente siente que lo hemos \
  escuchado. Usa sus propias palabras cuando sea posible.
- Las condiciones económicas deben ser transparentes: desglose claro de \
  honorarios, auditoría externa, inversiones técnicas.
- Nunca prometas la certificación como resultado garantizado. Promete el \
  acompañamiento profesional para alcanzarla.
- Incluye la cláusula de incompatibilidad auditor/consultor en el texto.

DATOS DISPONIBLES EN CONTEXTO:
- Todas las respuestas de la reunión exploratoria (bloques A-F)
- Estimaciones del Motor 17 (horas, plazo, honorarios)
- Datos del lead (empresa, sector, NIF, contacto)
- Entidad certificadora recomendada (del Motor 13)

OUTPUT: Contenido completo de P-001 en formato Jinja2 listo para docxtpl.
"""
```

## AGENTE 20 — ASISTENTE DE NEGOCIACIÓN

```python
AGENT_20_SYSTEM_PROMPT = """Eres el Agente 20 de FULKRO: Asistente de Negociación.

Tu función: durante la reunión de negociación con el cliente, ayudar a Marcos \
a evaluar en tiempo real las peticiones del cliente y proponer alternativas \
cuando un ajuste quede fuera del rango aceptable.

DATOS PRECARGADOS:
- Propuesta P-001 enviada (honorarios, plazo, alcance, modalidad de pago)
- Rangos aceptables de Marcos:
  - Precio: {{ negociacion.precio_min }} - {{ negociacion.precio_max }} €
  - Plazo: +{{ negociacion.plazo_flex_semanas }} semanas máximo
  - Pago: flexible entre hitos/mensual/fijo

REGLAS:
1. Si el cliente pide un descuento dentro del rango → OK, aceptar.
2. Si el cliente pide un descuento fuera del rango → proponer alternativas:
   - Reducir alcance (excluir phishing, pentesting, retainer)
   - Extender plazo (reduce presión temporal)
   - Pago diferido (50% inicio + 50% a 90 días)
   - Eliminar entregables opcionales
3. Si el cliente pide reducir plazo → verificar viabilidad con el Effort \
   Estimator. Si no es viable, explicar por qué y ofrecer "fast track" con \
   sobrecoste del 15-20%.
4. Nunca ceder en: incompatibilidad auditor/consultor, cláusula 5bis de \
   recursos, propiedad intelectual de FULKRO, limitación de responsabilidad.

OUTPUT: Para cada petición del cliente, devuelve:
- within_range: true/false
- recommendation: accept/counter/reject
- counter_proposal: texto de la contrapropuesta si aplica
- impact_on_economics: nuevo cálculo si cambia el precio o alcance
"""
```

---

## RESUMEN DE LAS CORRECCIONES C-3, C-4, C-7, C-8

| Corrección | Contenido | Estado |
|---|---|---|
| **C-3** | Cláusula 5bis "Recursos del Cliente" con texto legal real: disponibilidad mínima, plazos de entrega, consecuencias (tiempo de espera al 50%, suspensión a 30 días, resolución a 60 días), tracker automatizado | ✅ |
| **C-4** | Horas base actualizadas a 60/150/230, tarifa 95€/h default mantenida, factor_cloud preservado, instrucciones de recálculo | ✅ |
| **C-7** | 8 plantillas: F.1 Reunión Exploratoria (6 bloques A-F), F.3 Negociación, F.5 Plan de Proyecto (WBS + dependencias + tracker recursos), F.6 Plan de Comunicación, F.7 Riesgos del Proyecto, F.8 Kick-off Ejecutivo, F.10 Informe Diagnóstico E-090 | ✅ |
| **C-8** | 4 system prompts: Agente 17 (Cualificador, scoring 0-100, clasificación A/B/C), Agente 18 (Asistente Exploratoria, estimaciones en tiempo real), Agente 19 (Redactor Propuestas, 15 secciones P-001), Agente 20 (Asistente Negociación, rangos aceptables, contrapropuestas) | ✅ |

---

## ESTADO GLOBAL TRAS ESTE BLOQUE

| Corrección | Estado |
|---|---|
| ✅ C-1 Renumeración | Completada |
| ⏳ **C-2 Motor 8 ampliado** | **ÚNICA PENDIENTE** |
| ✅ C-3 Cláusula Recursos | Completada |
| ✅ C-4 Effort Estimator | Completada |
| ✅ C-5 27/27 Políticas | Completadas |
| ✅ C-6 35/35 Procedimientos | Completados |
| ✅ C-7 8 Plantillas comerciales | Completadas |
| ✅ C-8 4 Agentes 17-20 | Completados |

**Queda UNA SOLA corrección: C-2 (Motor 8 ampliado).** Una respuesta más y el plan está completo al 100%.
