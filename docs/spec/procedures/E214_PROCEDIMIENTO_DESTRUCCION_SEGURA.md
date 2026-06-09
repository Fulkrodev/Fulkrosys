# DOCUMENTO E-214 — PROCEDIMIENTO DE DESTRUCCIÓN SEGURA

**Es el procedimiento operativo que ejecuta la Política de Borrado Seguro y Destrucción de Información ({{ proyecto.codigo_documento_base }}-126) y la Política de Gestión de Soportes ({{ proyecto.codigo_documento_base }}-122).** Garantiza que la información clasificada o de carácter personal queda inaccesible cuando los soportes que la contienen alcanzan el final de su vida útil o se reutilizan fuera del alcance original.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-214"
titulo: "Procedimiento de Destrucción Segura"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-126, {{ proyecto.codigo_documento_base }}-122"
medidas_ens: ["mp.si.5", "mp.info.6"]
---

# PROCEDIMIENTO DE DESTRUCCIÓN SEGURA DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-214 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para que la información almacenada en soportes electrónicos, físicos o documentales sea eliminada de forma irrecuperable cuando los soportes finalizan su vida útil, se reasignan, salen del alcance del SGSI o se devuelven al proveedor.

Este procedimiento desarrolla la medida **mp.si.5 (protección de soportes de información — borrado y destrucción)** del Anexo II del Real Decreto 311/2022, conforme a la guía CCN-STIC 804 y a la norma UNE-EN 15713 sobre destrucción segura de información.

## 2. ALCANCE

Aplica a:

- Discos duros (HDD, SSD, NVMe) de servidores, estaciones, portátiles.
- Soportes extraíbles (USB, tarjetas SD, discos ópticos, cintas).
- Dispositivos móviles corporativos.
- Equipamiento de red con memoria persistente (firewalls, routers, impresoras multifunción).
- Documentación en papel clasificada como INTERNA o superior.
- Soportes en custodia externa al final del contrato.

## 3. NIVELES DE BORRADO Y DESTRUCCIÓN

Conforme a la clasificación establecida en {{ proyecto.codigo_documento_base }}-104 (Política de Clasificación de la Información), se aplican las siguientes técnicas:

| Clasificación | Técnica mínima exigida | Estándar de referencia |
|---|---|---|
| **PÚBLICA** | Formateo lógico estándar | — |
| **INTERNA** | Sobreescritura única (1 paso, NIST SP 800-88 Clear) | NIST SP 800-88 r1 |
| **CONFIDENCIAL** | Sobreescritura múltiple (3 pasos) o destrucción física | DoD 5220.22-M / NIST 800-88 Purge |
| **RESTRINGIDA / ALTA** | **Destrucción física obligatoria** (trituración nivel H-5 o desmagnetización + trituración) | UNE-EN 15713 nivel H-5/H-6 |

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA del ENS:** todos los soportes que hayan alojado información de la categoría requieren destrucción física certificada por proveedor homologado, independientemente de la clasificación nominal de los datos. La sobreescritura lógica es insuficiente.
{% endif %}

## 4. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Responsable del Sistema** | Identificar soportes a destruir, mantener inventario, ejecutar borrado lógico de bajo nivel, custodiar soportes pendientes en zona segura. |
| **Responsable de la Seguridad** | Aprobar el método de destrucción, supervisar la cadena de custodia hasta destrucción definitiva, firmar las actas. |
| **Proveedor de destrucción certificada** | Ejecutar la destrucción física conforme a UNE-EN 15713, emitir certificado individual con número de serie y método. |
| **Testigo de destrucción** | Persona designada por el Responsable de la Seguridad que presencia la destrucción cuando se realiza in situ. |
| **DPO** | Validar la trazabilidad para soportes que han contenido datos personales. |

## 5. FLUJO OPERATIVO

### Fase 1 — Identificación y baja del soporte (T+0)

1. Cuando un soporte deja de utilizarse (fin de vida útil, sustitución, fin de contrato, fin del proyecto al que estaba asignado), el Responsable del Sistema lo da de baja en el **Inventario de Activos** ({{ proyecto.codigo_documento_base }}-AR-001) mediante el formulario **F-214 — Solicitud de Destrucción**.

2. El formulario incluye:
   - Identificador único del soporte (número de serie, etiqueta de inventario).
   - Tipo de soporte (HDD/SSD/USB/papel/etc.) y capacidad.
   - Clasificación de la información que ha contenido (la máxima nunca albergada).
   - Datos personales (categoría ordinaria / categoría especial RGPD art. 9 / no aplica).
   - Sistema o servicio en el que se utilizaba.
   - Persona que lo entrega y fecha.

### Fase 2 — Custodia previa a destrucción (T+0 a T+30 días)

3. Los soportes pendientes de destrucción se almacenan en una **zona de soportes a destruir** físicamente segura:
   - Acceso restringido a personal autorizado mediante {{ proyecto.codigo_documento_base }}-101 (Control de Accesos).
   - Cierre con llave o cerradura electrónica, con registro de aperturas.
   - Separación visual entre soportes pendientes de borrado lógico y soportes pendientes de destrucción física.
   - Tiempo máximo de custodia: **30 días naturales** desde la baja.

4. Cada soporte se etiqueta con la clasificación máxima de información albergada y la fecha límite de destrucción.

### Fase 3 — Borrado lógico previo (cuando proceda)

5. Para soportes con clasificación INTERNA o CONFIDENCIAL que vayan a ser reutilizados internamente, el Responsable del Sistema ejecuta el borrado lógico mediante:
   - **Discos magnéticos (HDD):** sobreescritura completa con `shred -vfz -n N` (Linux) o `cipher /w` (Windows) o herramienta certificada equivalente.
   - **Discos sólidos (SSD/NVMe):** orden ATA Secure Erase (`hdparm --security-erase`) o NVMe Format con cripto-borrado.
   - **Soportes USB / tarjetas:** sobreescritura completa con datos aleatorios.

6. El borrado lógico se registra en el **log L-214** con fecha, herramienta utilizada, número de pasos, hash de verificación post-borrado y operador.

### Fase 4 — Destrucción física (CONFIDENCIAL / RESTRINGIDA / ALTA)

7. Para soportes que requieran destrucción física, el Responsable de Seguridad selecciona el método:

| Soporte | Método físico recomendado |
|---|---|
| Discos magnéticos | Desmagnetización (degausser certificado) + trituración H-5 |
| Discos SSD/NVMe | Trituración H-6 (la desmagnetización no funciona en estado sólido) |
| Cintas magnéticas | Desmagnetización + trituración |
| Discos ópticos | Trituración H-5 mínimo |
| Papel CONFIDENCIAL | Trituración corte cruzado nivel P-4 mínimo |
| Papel RESTRINGIDA / ALTA | Trituración nivel P-5 / P-7 |

8. **Dos modalidades** según el volumen:

   - **Destrucción in situ:** el proveedor acude con vehículo trituradora; el testigo de destrucción presencia la operación; se firma acta en el momento.
   
   - **Destrucción en planta:** los soportes se entregan al proveedor mediante furgoneta sellada con precinto numerado; se firma albarán de retirada; el proveedor envía certificado individual en un máximo de **5 días hábiles**.

9. Toda salida de soportes hacia destrucción externa queda registrada conforme al procedimiento {{ proyecto.codigo_documento_base }}-215 (Gestión de Soportes Extraíbles), generando un **registro de salida** que cierra el ciclo de vida del soporte.

### Fase 5 — Verificación, certificación y archivo (T+5 días hábiles tras destrucción)

10. Recepción del **certificado de destrucción** del proveedor con:
    - Número de serie de cada soporte destruido.
    - Método empleado.
    - Fecha y hora.
    - Identificación del operario.
    - Nivel de seguridad alcanzado conforme a UNE-EN 15713.
    - Firma del responsable del proveedor.

11. Verificación de coherencia: el Responsable de Seguridad coteja los números de serie del certificado con la lista de soportes entregados (formulario F-214).

12. Cumplimentación del **registro R-214 — Acta de Destrucción**, que asocia el formulario de solicitud, el certificado del proveedor y el cierre del activo en el inventario.

13. Archivo de la documentación con conservación mínima de **6 años** (12 años cuando los soportes contenían datos personales conforme al criterio AEPD).

## 6. CASOS ESPECIALES

### 6.1. Equipos en arrendamiento o renting

Cuando un equipo en renting se devuelve al proveedor, el Responsable de Seguridad **debe garantizar la extracción y destrucción del soporte de almacenamiento ANTES de la devolución**, salvo que el contrato establezca cláusula de borrado seguro certificado por el proveedor con derecho de auditoría.

### 6.2. Cloud público y SaaS

En servicios cloud no aplica destrucción física de soportes. La eliminación se ejecuta mediante:

- API/UI del proveedor para borrado de objetos, snapshots y backups.
- Verificación de la política de retención y cripto-borrado del proveedor (eliminación de claves de cifrado del cliente).
- Confirmación documental por parte del proveedor cuando esté disponible (DSAR / certificado).
- Registro en R-214 con anotación `medio: cloud` y referencia al servicio.

### 6.3. Dispositivos móviles personales (BYOD)

Conforme a la Política BYOD ({{ proyecto.codigo_documento_base }}-118), al cesar el uso corporativo de un dispositivo personal se ejecuta **borrado selectivo** del perímetro corporativo (MDM container wipe) sin afectar a los datos personales del usuario. Se documenta en R-214 con tipo `borrado_selectivo_mdm`.

### 6.4. Soportes asociados a evidencias judiciales o auditorías en curso

**No se destruyen** mientras existan procedimientos judiciales, administrativos o auditorías abiertos que puedan requerirlos. El asesor legal o el Responsable de Cumplimiento mantiene un registro de soportes en custodia legal.

## 7. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| F-214 | Solicitud de Destrucción | 6 años |
| R-214 | Acta de Destrucción + certificado del proveedor | 6 años (12 si datos personales) |
| L-214 | Log técnico de borrado lógico | 12 meses |
| INV-update | Baja en inventario de activos | Permanente |

## 8. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| Cobertura de destrucción certificada | soportes destruidos con certificado / soportes dados de baja | 100 % para CONFIDENCIAL+ |
| Tiempo medio de custodia previa a destrucción | media(T_destruccion - T_baja) | ≤ 30 días |
| Soportes pendientes de destruir > 30 días | recuento absoluto | 0 |
| % cumplimiento UNE-EN 15713 | métodos auditados conformes / total | 100 % |

## 9. AUDITORÍA Y SUPERVISIÓN

- **Trimestralmente**, el Responsable de Seguridad realiza una **revisión cruzada** entre las bajas de inventario y los registros R-214 para detectar soportes desaparecidos sin destrucción documentada.
- **Anualmente**, durante la auditoría interna del SGSI ({{ proyecto.codigo_documento_base }}-218), se verifica una muestra del 10 % de los certificados emitidos por el proveedor de destrucción.
- En caso de desviación crítica (soporte sin trazabilidad), se abre **No Conformidad** conforme a {{ proyecto.codigo_documento_base }}-220 e incidente de seguridad nivel ALTO conforme a {{ proyecto.codigo_documento_base }}-204.

## 10. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Se modifique la guía CCN-STIC 804 en lo relativo a mp.si.5.
- Se cambie de proveedor de destrucción certificada.
- Aparezcan nuevos tipos de soporte en el inventario (memoria persistente embebida, etc.).
- Cambien los criterios AEPD sobre conservación o destrucción de datos personales.

Responsabilidad de la revisión: **Responsable de la Seguridad**, con aprobación del **Comité de Seguridad**.
