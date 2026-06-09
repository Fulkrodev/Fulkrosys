# DOCUMENTO E-217 — PROCEDIMIENTO DE EVALUACIÓN Y SEGUIMIENTO DE PROVEEDORES

**Es el procedimiento operativo de la Política E-112.** Define exactamente cómo se evalúa a un proveedor antes de contratar, durante la prestación y al finalizar la relación.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-217"
titulo: "Procedimiento de Evaluación y Seguimiento de Proveedores"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-112"
---

# PROCEDIMIENTO DE EVALUACIÓN Y SEGUIMIENTO DE PROVEEDORES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-217 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para la evaluación previa a la contratación, el seguimiento durante la relación y la salida controlada de los proveedores y terceros con acceso a información, sistemas o instalaciones de {{ cliente.razon_social }}, en desarrollo de la Política de Seguridad en las Relaciones con Proveedores ({{ proyecto.codigo_documento_base }}-112).

## 2. FASE 1 — EVALUACIÓN PREVIA A LA CONTRATACIÓN

### 2.1 Cuestionario de seguridad

**Responsable:** Responsable del Servicio que solicita la contratación, con apoyo del Responsable de la Seguridad.

**Acciones:**

1. Antes del inicio de cualquier negociación contractual con un proveedor de nivel **MEDIO** o superior conforme al apartado 3 de la Política {{ proyecto.codigo_documento_base }}-112, se le remitirá el **Cuestionario de Evaluación de Seguridad** del Anexo I, que contiene preguntas sobre:

- Certificaciones de seguridad vigentes (ISO 27001, ENS, SOC 2, etc.).
- Política interna de seguridad y gobierno del SGSI.
- Gestión de incidentes y notificación de brechas.
- Control de accesos y gestión de personal.
- Gestión de subcontratistas y cadena de suministro.
- Seguridad física e infraestructura.
- Continuidad del servicio y recuperación ante desastres.
- Protección de datos personales y cumplimiento del RGPD.
- Localización del tratamiento de datos.
- Mecanismos de cifrado utilizados.

2. El proveedor dispone de **15 días naturales** para devolver el cuestionario cumplimentado y firmado.

### 2.2 Verificación documental

**Acciones:**

3. El Responsable de la Seguridad **verifica** la información declarada por el proveedor, en particular:

- Vigencia de certificaciones declaradas, mediante consulta a las páginas oficiales de los organismos certificadores (ENAC, IAF, etc.).
- Existencia y vigencia del registro como Encargado del Tratamiento, cuando proceda.
- Solvencia económica y técnica.
- Reputación pública del proveedor, mediante consultas a fuentes abiertas y, cuando proceda, a registros sectoriales.

### 2.3 Análisis de riesgos específico

4. Se elabora un **análisis de riesgos específico** de la relación, conforme a la metodología MAGERIT v3 ({{ proyecto.codigo_documento_base }}-AR-001), considerando:

- Tipo de información a la que el proveedor tendrá acceso.
- Volumen y sensibilidad del tratamiento.
- Localización del tratamiento.
- Cadena de subcontratación prevista.
- Dependencias generadas para la Entidad.

### 2.4 Decisión de contratación

5. El Responsable de la Seguridad emite un **informe de evaluación** con valoración GLOBAL: **APTO**, **APTO CON CONDICIONES** o **NO APTO**.

6. Para proveedores de nivel **ALTO** o **CRÍTICO**, el informe se eleva al Comité de Seguridad para autorización formal antes de proceder a la contratación.

7. La decisión final corresponde al órgano competente para la contratación, quien deberá motivar cualquier decisión contraria al informe de seguridad.

### 2.5 Cláusulas contractuales

8. El contrato a suscribir incorporará las cláusulas mínimas de seguridad establecidas en el apartado 5.3 de la Política {{ proyecto.codigo_documento_base }}-112.

9. Cuando el proveedor vaya a tratar datos personales por cuenta de la Entidad, se suscribirá adicionalmente el **Contrato de Encargo del Tratamiento** conforme al artículo 28.3 del RGPD.

## 3. FASE 2 — INCORPORACIÓN

10. Antes del inicio efectivo de la prestación:

- Se asignan los accesos necesarios al proveedor según el procedimiento {{ proyecto.codigo_documento_base }}-231.
- Se realiza una **sesión de incorporación** en la que se le presentan las normas del SGSI aplicables.
- Se firman los acuerdos de confidencialidad correspondientes.
- Se le entrega copia de las políticas E-103 (Uso Aceptable) y E-104 (Clasificación) en lo aplicable.

## 4. FASE 3 — SEGUIMIENTO DURANTE LA PRESTACIÓN

### 4.1 Reuniones periódicas de seguridad

| Nivel del proveedor | Frecuencia mínima |
|---|---|
| CRÍTICO | Trimestral |
| ALTO | Semestral |
| MEDIO | Anual |

**Acciones:**

11. En cada reunión se revisarán, al menos:

- Cumplimiento de los SLA contractualmente comprometidos.
- Incidentes ocurridos en el periodo y acciones adoptadas.
- Cambios significativos en la organización del proveedor o en sus medidas de seguridad.
- Cambios en la cadena de subcontratación.
- Resultados de auditorías internas o externas del proveedor.
- Recomendaciones de mejora.

12. De cada reunión se levanta **acta** que firman ambas partes y queda incorporada al expediente del proveedor.

### 4.2 Auditorías

13. La Entidad podrá auditar al proveedor:

- **Auditoría documental anual** mediante actualización del cuestionario inicial del Anexo I.
- **Auditoría in situ** para proveedores CRÍTICOS con periodicidad mínima anual.
- **Auditoría reactiva** tras cualquier incidente significativo.

14. Las auditorías se realizan con preaviso razonable salvo en caso de incidente grave.

15. Los resultados se documentan en el **Informe de Auditoría de Proveedor** y, si se detectan no conformidades, se acuerda un **Plan de Acción** con plazos definidos.

### 4.3 Gestión de incidentes notificados por proveedores

16. Cuando un proveedor notifica un incidente que afecta a la Entidad, se aplica el procedimiento {{ proyecto.codigo_documento_base }}-204, considerando al proveedor como fuente del incidente.

17. Se evalúa el **impacto sobre la continuidad** del servicio prestado y la necesidad de activar planes de contingencia.

18. Se documenta la respuesta del proveedor, los tiempos de resolución y la eficacia de las medidas adoptadas.

## 5. FASE 4 — REEVALUACIÓN ANUAL

19. Con periodicidad **anual**, todos los proveedores activos de nivel MEDIO o superior son objeto de **reevaluación**, que incluye:

- Actualización del cuestionario inicial.
- Verificación de la vigencia de las certificaciones declaradas.
- Revisión de los incidentes y su gestión durante el año.
- Análisis del cumplimiento de los SLA.
- Reconfirmación o reclasificación del nivel del proveedor.

20. El resultado se incorpora al expediente del proveedor y se eleva al Comité de Seguridad.

## 6. FASE 5 — SALIDA Y EXTINCIÓN DE LA RELACIÓN

### 6.1 Planificación de la salida

21. Cuando se prevea la finalización de la relación con un proveedor crítico, se elabora con la antelación suficiente un **Plan de Salida** que contemple:

- Identificación del proveedor sustituto o de la internalización del servicio.
- Cronograma de transición.
- Plan de migración de datos y servicios.
- Pruebas de continuidad durante la transición.
- Comunicación a las partes interesadas afectadas.

### 6.2 Ejecución de la salida

22. Al finalizar efectivamente la relación, se ejecuta la **Lista de Comprobación de Salida de Proveedor** del Anexo II:

- Devolución o eliminación segura de toda la información de la Entidad en posesión del proveedor.
- Obtención del **Certificado de Destrucción de Datos** firmado por el proveedor.
- Revocación de todos los accesos del proveedor a sistemas, redes e instalaciones de la Entidad, conforme al procedimiento {{ proyecto.codigo_documento_base }}-231.
- Recuperación de credenciales, tarjetas, tokens y demás recursos.
- Verificación documental del cumplimiento de todas las obligaciones contractuales.
- Recordatorio escrito de las obligaciones que subsisten tras la extinción.

23. Se elabora el **Informe de Cierre de Proveedor** y se archiva el expediente conforme al procedimiento {{ proyecto.codigo_documento_base }}-221.

## 7. INDICADORES

| Indicador | Objetivo |
|---|---|
| Proveedores MEDIO+ con cuestionario vigente (< 12 meses) | 100% |
| Proveedores CRÍTICO con auditoría anual realizada | 100% |
| Proveedores con plan de acción abierto > 6 meses | 0 |
| Incidentes notificados por proveedores en plazo contractual | 100% |

## 8. ANEXOS

- **Anexo I:** Cuestionario de Evaluación de Seguridad de Proveedores
- **Anexo II:** Lista de Comprobación de Salida de Proveedor
- **Anexo III:** Plantilla de Acta de reunión periódica
- **Anexo IV:** Plantilla del Informe de Auditoría de Proveedor
- **Anexo V:** Modelo de Cláusulas de Seguridad para contratos
- **Anexo VI:** Modelo de Contrato de Encargo del Tratamiento (art. 28 RGPD)

---

**Documento {{ proyecto.codigo_documento_base }}-217 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
