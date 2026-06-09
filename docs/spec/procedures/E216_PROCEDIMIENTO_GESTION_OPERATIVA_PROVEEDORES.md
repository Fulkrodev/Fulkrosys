# DOCUMENTO E-216 — PROCEDIMIENTO DE GESTIÓN OPERATIVA DE PROVEEDORES

**Es el procedimiento operativo que ejecuta la Política de Seguridad en las Relaciones con Proveedores ({{ proyecto.codigo_documento_base }}-112).** Define cómo se gestionan en el día a día los proveedores TIC y de seguridad: alta, configuración del acceso, monitorización del SLA, gestión de incidentes compartidos, finalización de contrato.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-216"
titulo: "Procedimiento de Gestión Operativa de Proveedores"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_sistema.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-112"
medidas_ens: ["op.ext.1", "op.ext.2", "op.ext.3"]
---

# PROCEDIMIENTO DE GESTIÓN OPERATIVA DE PROVEEDORES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-216 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para gestionar de forma segura el ciclo de vida de los proveedores que prestan servicios TIC, de seguridad o que tratan información del alcance del SGSI: alta, asignación de accesos, supervisión del cumplimiento contractual, gestión de incidentes que les involucren y baja al finalizar la relación.

Este procedimiento desarrolla las medidas **op.ext.1 (acuerdos con terceros), op.ext.2 (gestión diaria) y op.ext.3 (cadena de suministro)** del Anexo II del Real Decreto 311/2022, y se complementa con el procedimiento {{ proyecto.codigo_documento_base }}-217 (Evaluación y Seguimiento de Proveedores).

## 2. ALCANCE

Aplica a todo proveedor o tercero que:

- Acceda físicamente a instalaciones del alcance.
- Acceda lógicamente a sistemas o información del alcance.
- Trate datos personales por cuenta de {{ cliente.razon_social }} (encargados de tratamiento RGPD art. 28).
- Suministre productos o servicios cuyo fallo afecte a la disponibilidad o seguridad del SGSI.
- Sea proveedor de proveedores principales (subencargados, subcontratistas), considerados parte de la cadena de suministro.

## 3. CLASIFICACIÓN DE PROVEEDORES

Cada proveedor se clasifica al alta y se revisa anualmente:

| Clase | Criterio | Tratamiento exigido |
|---|---|---|
| **CRÍTICO** | Servicios cuya caída produce parada total del servicio principal del cliente, o acceso a información ALTA. | Doble proveedor o plan de continuidad obligatorio, evaluación anual presencial, derecho de auditoría activado. |
| **ALTO** | Acceso a información CONFIDENCIAL o tratamiento de datos personales de categoría especial. | Evaluación anual remota, ANS con KPIs trimestrales, auditoría documental. |
| **MEDIO** | Acceso a sistemas no críticos, tratamiento de datos personales ordinarios. | Evaluación bienal, revisión SLA semestral. |
| **BAJO** | Sin acceso a información, productos genéricos no integrados en producción. | Verificación anual de vigencia del contrato. |

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** los proveedores CRÍTICOS deben acreditar certificación ENS o ISO 27001 en vigor. La pérdida o suspensión de la certificación es motivo de revisión inmediata del contrato.
{% endif %}

## 4. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Responsable de Compras / Contratación** | Tramitar alta y baja contractual, mantener vigencia de cláusulas obligatorias. |
| **Responsable del Sistema** | Validar accesos técnicos, supervisar SLA operativo, integrar al proveedor en herramientas de monitorización. |
| **Responsable de la Seguridad** | Aprobar la clasificación del proveedor, validar el contrato desde la óptica de seguridad, autorizar accesos sensibles. |
| **DPO** | Validar contrato Art. 28 RGPD, transferencias internacionales, notificación de brechas. |
| **Propietario del servicio** (interno) | Recibir entregables, validar SLA, escalar incidentes operativos. |

## 5. FLUJO OPERATIVO

### Fase 1 — Alta de proveedor (T-30 días antes del go-live)

**Responsable:** Responsable de Compras con apoyo del Responsable del Sistema y Responsable de Seguridad.

1. **Solicitud interna:** el área que requiere el servicio cumplimenta el formulario **F-216.1 — Solicitud de Alta de Proveedor** indicando objeto, ámbito, datos a tratar, criticidad estimada y referencia a la oferta económica.

2. **Verificaciones previas:**
   - Solvencia jurídica y financiera (Registro Mercantil, AEAT, Seguridad Social).
   - Inexistencia en listas de sanciones internacionales si tiene actividad fuera UE.
   - Certificaciones de seguridad declaradas (ENS, ISO 27001, SOC 2, etc.) — verificadas en el organismo emisor.
   - Histórico de incidentes públicos relevantes (búsqueda OSINT estructurada).

3. **Evaluación de seguridad inicial** mediante el cuestionario **F-216.2 — Cuestionario de Seguridad para Proveedores** (60 preguntas alineadas con el Anexo II del ENS y RGPD). Las respuestas se contrastan con la criticidad asignada.

4. **Clasificación formal** (apartado 3) por el Responsable de Seguridad.

5. **Negociación del contrato** incorporando el clausulado mínimo:
   - Cláusula ENS de op.ext.1 (definición de servicios, ANS, gestión de incidentes).
   - Cláusula RGPD Art. 28 si tratan datos personales.
   - Derecho de auditoría con preaviso máximo de 30 días.
   - Notificación de incidentes en plazo máximo de **24 horas** desde detección.
   - Subencargados / subcontratistas autorizados con preaviso de cambios.
   - Devolución o destrucción certificada de información al fin del contrato.
   - Penalizaciones por incumplimiento de SLA.

6. Firma del contrato y registro en el **Repositorio de Contratos** con fecha de inicio, vencimiento y alertas a 90/30 días antes del vencimiento.

### Fase 2 — Configuración de accesos (T-15 días antes del go-live)

**Responsable:** Responsable del Sistema con autorización del Responsable de Seguridad.

7. **Accesos físicos:** alta en el sistema de control de acceso de las sedes que requiera, con vigencia limitada al período contractual.

8. **Accesos lógicos:**
   - Creación de cuentas nominativas para cada técnico del proveedor (no se admiten cuentas compartidas).
   - Asignación de privilegios mínimos conforme al procedimiento {{ proyecto.codigo_documento_base }}-211.
   - MFA obligatorio para todos los accesos remotos.
   - VPN dedicada para proveedores o bastion host con grabación de sesión para accesos privilegiados.
   - Restricción horaria si el servicio no es 24x7.

9. **Bring Your Own Identity (BYOI):** si el proveedor utiliza su propio IdP federado, validación de la confianza del IdP y registro en el directorio corporativo.

10. **Notificación al proveedor** del catálogo de accesos concedidos, de la política de uso aceptable corporativa y de las sanciones por incumplimiento.

### Fase 3 — Operación diaria (T+0 → fin de contrato)

**Responsable:** Responsable del Sistema y Propietario del servicio.

11. **Monitorización de SLA:** los KPIs comprometidos se monitorizan mediante dashboards con frecuencia mínima:
    - CRÍTICO: en tiempo real, alertado.
    - ALTO: diaria.
    - MEDIO: semanal.
    - BAJO: mensual.

12. **Reuniones de seguimiento:**

| Clase de proveedor | Frecuencia mínima |
|---|---|
| CRÍTICO | Mensual + revisión trimestral con dirección del proveedor |
| ALTO | Trimestral |
| MEDIO | Semestral |
| BAJO | Anual |

   Cada reunión genera **acta R-216.1** con asistentes, asuntos tratados, decisiones y acciones con responsable y plazo.

13. **Gestión de cambios solicitados por el proveedor:** todo cambio en el servicio (subencargados, ubicación de procesamiento, tecnología) se canaliza por el procedimiento de cambios {{ proyecto.codigo_documento_base }}-203 con análisis de impacto en seguridad.

14. **Revisión periódica de accesos:** trimestralmente para CRÍTICO y ALTO, semestralmente para los demás, conforme a {{ proyecto.codigo_documento_base }}-210.

15. **Notificación de incidentes desde el proveedor:** los incidentes se reciben en el buzón de seguridad y se gestionan conforme a {{ proyecto.codigo_documento_base }}-204. El plazo de notificación contractual es de 24 horas, pero el equipo interno escala inmediatamente al Coordinador del ERI sin esperar el detalle completo.

16. **Notificación de incidentes al proveedor:** cuando un incidente afecta a sus credenciales, accesos o información que custodia, se le comunica formalmente con plazo y acciones requeridas.

### Fase 4 — Renovación / cese de contrato

**Responsable:** Responsable de Compras con visto bueno del Responsable del Sistema.

17. **Renovación:** 90 días antes del vencimiento, el Responsable de Compras recibe alerta automática. Se valida la continuidad del servicio, se actualiza la evaluación de seguridad y se renegocian cláusulas obsoletas.

18. **Plan de salida:** desde el alta, todo proveedor CRÍTICO o ALTO debe tener documentado un **Plan de Salida** que incluya:
    - Devolución de información en formato estándar.
    - Borrado certificado conforme a {{ proyecto.codigo_documento_base }}-214.
    - Periodo de transición técnica al sucesor.
    - Continuidad del servicio durante la transición.

19. **Baja efectiva:**
    - Revocación inmediata de accesos físicos y lógicos.
    - Retirada de equipos cedidos.
    - Recepción del certificado de devolución/destrucción.
    - Cierre del registro en el inventario de proveedores.

## 6. CADENA DE SUMINISTRO (op.ext.3)

Los proveedores **CRÍTICO** y **ALTO** declaran a sus subencargados/subcontratistas relevantes:

- Lista actualizada al menos anualmente.
- Notificación con preaviso de 30 días de cualquier alta o baja de subencargado.
- Acuerdos por defecto que extienden las cláusulas de seguridad y RGPD a la cadena.
- Para componentes software, mantenimiento de un **SBOM** básico que el proveedor entrega bajo demanda.

## 7. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| F-216.1 | Solicitud de Alta de Proveedor | 6 años tras baja |
| F-216.2 | Cuestionario de Seguridad para Proveedores | 6 años tras baja |
| INV-prov | Inventario de Proveedores | Permanente |
| R-216.1 | Actas de reunión de seguimiento | 3 años |
| R-216.2 | Actas de revisión de accesos | 3 años |
| R-216.3 | Plan de Salida (uno por proveedor crítico) | Vigente + 6 años |

## 8. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| Cobertura contractual ENS/RGPD | proveedores con cláusulas vigentes / total | 100 % |
| Cumplimiento de SLA | media ponderada del cumplimiento por proveedor | ≥ 95 % |
| Tiempo medio de notificación de incidentes desde proveedor | media | ≤ 24 h |
| Proveedores con evaluación anual completada | evaluados / requeridos | 100 % |
| Subencargados declarados al día | al día / total proveedores ALTO+ | 100 % |

## 9. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Cambien las medidas op.ext.1-3 de la guía CCN-STIC 804.
- Cambie significativamente la cartera de proveedores (M&A, internalización masiva).
- Se incorpore nuevo régimen normativo aplicable a la contratación pública o financiera (DORA, NIS2 transpuesta).
- Se detecten desviaciones reiteradas en proveedores críticos.

Responsabilidad: **Responsable del Sistema** + **Responsable de Compras**, con aprobación del **Responsable de Seguridad** y elevación al **Comité de Seguridad**.
