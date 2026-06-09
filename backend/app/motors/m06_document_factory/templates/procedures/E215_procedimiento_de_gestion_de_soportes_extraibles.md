# DOCUMENTO E-215 — PROCEDIMIENTO DE GESTIÓN DE SOPORTES EXTRAÍBLES

**Es el procedimiento operativo que ejecuta la Política de Gestión de Soportes ({{ proyecto.codigo_documento_base }}-122).** Regula el ciclo de vida —marcado, custodia, transporte y entrega— de cualquier soporte físico extraíble que entre o salga del alcance del SGSI conteniendo información del cliente.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-215"
titulo: "Procedimiento de Gestión de Soportes Extraíbles"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-122"
medidas_ens: ["mp.si.1", "mp.si.2", "mp.si.3", "mp.si.4"]
---

# PROCEDIMIENTO DE GESTIÓN DE SOPORTES EXTRAÍBLES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-215 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para el marcado, almacenamiento, custodia, transporte y entrega de los soportes extraíbles que contienen información dentro del alcance del SGSI de {{ cliente.razon_social }}, garantizando la trazabilidad y la confidencialidad durante todo su ciclo de vida.

Este procedimiento desarrolla las medidas **mp.si.1 (marcado), mp.si.2 (criptografía), mp.si.3 (custodia) y mp.si.4 (transporte)** del Anexo II del Real Decreto 311/2022 y se alinea con la guía CCN-STIC 804 y la guía CCN-STIC 807 para los aspectos criptográficos.

## 2. ALCANCE

Aplica a todo soporte extraíble que contenga o pueda contener información clasificada como INTERNA o superior, incluyendo:

- Memorias USB y discos externos.
- Tarjetas SD/microSD.
- Cintas magnéticas de backup.
- Discos ópticos (CD/DVD/Blu-ray).
- Discos duros extraídos en mantenimiento o reemplazo.
- Tokens criptográficos y dispositivos HSM portables.

Quedan **excluidos** los dispositivos personales (BYOD), regulados por el procedimiento {{ proyecto.codigo_documento_base }}-228, así como los soportes destinados a destrucción regulados por {{ proyecto.codigo_documento_base }}-214.

## 3. AUTORIZACIÓN DE USO DE SOPORTES EXTRAÍBLES

### 3.1. Política base

Por defecto, los puertos USB de los puestos de trabajo están **bloqueados** para almacenamiento masivo mediante GPO/MDM, conforme al hardening descrito en {{ proyecto.codigo_documento_base }}-230. Se permite el uso de:

- Periféricos no de almacenamiento (teclado, ratón).
- Tokens corporativos identificados (smart cards, llaves FIDO2).

### 3.2. Solicitud de excepción

El uso de soportes USB de almacenamiento requiere autorización expresa, gestionada conforme al procedimiento de excepciones {{ proyecto.codigo_documento_base }}-222:

1. El usuario solicita la excepción mediante el formulario **F-215.1 — Autorización de Uso de Soporte Extraíble** indicando:
   - Justificación operativa.
   - Tipo de información a transferir.
   - Origen y destino.
   - Duración prevista de la autorización.
2. El Responsable del Sistema verifica que el dispositivo solicitado es uno de los **modelos corporativos cifrados por hardware** (lista mantenida en el Catálogo de Hardware Aprobado).
3. El Responsable de Seguridad aprueba o rechaza la solicitud con plazo máximo de **2 días hábiles**.

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** las excepciones para uso de soportes extraíbles requieren aprobación dual (Responsable de Seguridad + Responsable del Servicio) y se otorgan por un máximo de 30 días, renovables explícitamente.
{% endif %}

## 4. MARCADO DE SOPORTES (mp.si.1)

Todo soporte aprobado se marca **antes de su primera utilización** con:

| Elemento de marcado | Forma |
|---|---|
| Identificador único | Etiqueta resistente con código `S-AAAA-NNNN` |
| Clasificación máxima admitida | Etiqueta de color: blanco (PÚBLICA), azul (INTERNA), amarillo (CONFIDENCIAL), rojo (RESTRINGIDA) |
| Propietario corporativo | "{{ cliente.razon_social }}" o NIF |
| Contacto en caso de pérdida | Email de seguridad de la organización |

El marcado físico se complementa con metadatos lógicos en el sistema de gestión de soportes (etiqueta de volumen del filesystem, atributo extendido o fichero de manifest según tecnología).

## 5. CIFRADO DE SOPORTES (mp.si.2)

Todo soporte que pueda contener información de clasificación INTERNA o superior **debe estar cifrado**:

| Tipo de soporte | Mecanismo aprobado |
|---|---|
| Disco USB / disco externo | BitLocker To Go (Windows) / LUKS (Linux) / FileVault (macOS) — AES-256 |
| Tarjeta SD | Cifrado a nivel de filesystem o cifrado fichero a fichero |
| Cinta de backup | Cifrado en origen por la solución de backup (clave gestionada por KMS corporativo) |
| Disco óptico | Únicamente para información PÚBLICA o cifrado de fichero a fichero |
| Token / HSM | Operación nativa del propio dispositivo |

Los algoritmos y longitudes de clave deben ajustarse a la guía **CCN-STIC 807** y al procedimiento de gestión de claves {{ proyecto.codigo_documento_base }}-232.

**Las claves de cifrado de soportes se custodian en el KMS corporativo** y se entregan al usuario autorizado mediante el procedimiento {{ proyecto.codigo_documento_base }}-211 (cuentas privilegiadas / claves). Está prohibido escribir contraseñas o claves en el propio soporte o en notas físicas adjuntas.

## 6. CUSTODIA (mp.si.3)

### 6.1. Custodia en uso

Mientras un soporte está asignado a un usuario:

- **Nunca se deja desatendido** en zonas no controladas (sala de reuniones vacía, vehículo sin custodia, hotel).
- En oficina, fuera de horario laboral, se guarda bajo llave en cajonera personal o armario cerrado conforme a {{ proyecto.codigo_documento_base }}-125 (Mesa Limpia y Pantalla Limpia).
- En transporte, se mantiene siempre con el usuario o, si no es posible, se cifra y se envía conforme al apartado 7.

### 6.2. Custodia en armario corporativo

Los soportes no asignados a usuario individual (cintas de backup, discos de plantilla maestra, soportes en cuarentena) se custodian en un **armario ignífugo** con:

- Acceso restringido a personal autorizado mediante llave maestra o cerradura electrónica con log de aperturas.
- Inventario actualizado del contenido (formulario F-215.2 — Hoja de Custodia).
- Separación física entre soportes de distintas clasificaciones cuando sea operativamente factible.

### 6.3. Inventario y revisión

El Responsable del Sistema mantiene el **Inventario de Soportes Extraíbles** integrado con el inventario general de activos. Se revisa **mensualmente** y se concilia con los registros físicos.

## 7. TRANSPORTE (mp.si.4)

### 7.1. Transporte interno (entre sedes propias)

- Soporte cifrado obligatoriamente conforme al apartado 5.
- Sobre o maletín cerrado, identificado solo con código (no descripción de contenido).
- Persona autorizada y conocida por origen y destino.
- Acuse de recibo firmado en destino.

### 7.2. Transporte externo (cliente, proveedor, mensajería)

| Clasificación | Modalidad de transporte mínima |
|---|---|
| INTERNA | Mensajería estándar con seguimiento, sobre cerrado, contenido cifrado |
| CONFIDENCIAL | Mensajería certificada con firma en destino, sobre antivioloancia, contenido cifrado |
| RESTRINGIDA / ALTA | Mensajería acreditada por el CCN o transporte propio con custodia continua, doble sobre, cifrado AES-256 |

Toda expedición se registra en el formulario **F-215.3 — Albarán de Expedición** con:

- Identificador del soporte.
- Origen (persona, sede).
- Destino (persona, organización, dirección).
- Fecha y hora de salida.
- Empresa de mensajería y número de referencia.
- Acuse de recibo del destinatario (PoD) — escaneado y archivado al regreso.

### 7.3. Recepción de soportes externos

Los soportes recibidos del exterior se procesan en una **estación de cuarentena aislada de la red corporativa**:

1. Inspección física en busca de signos de manipulación.
2. Análisis antimalware con dos motores diferentes.
3. Verificación de la firma o hash si fue acordado con el remitente.
4. Solo tras superar los tres controles se autoriza la copia al entorno productivo y se registra la entrada en el inventario.

## 8. ENTREGA Y DEVOLUCIÓN

### 8.1. Entrega a usuario interno

El Responsable del Sistema entrega el soporte mediante el formulario **F-215.4 — Acta de Entrega/Devolución** firmado por ambas partes. La entrega solo se realiza tras la autorización vigente conforme al apartado 3.

### 8.2. Devolución

Al cesar la necesidad operativa, vencer la autorización o producirse el cese de la relación con la persona, el soporte se devuelve obligatoriamente. El Responsable del Sistema:

1. Verifica el estado físico y el cifrado.
2. Realiza borrado lógico conforme al apartado 5 de {{ proyecto.codigo_documento_base }}-214.
3. Decide reasignación, almacenamiento en armario corporativo o destrucción.

### 8.3. Pérdida o sustracción

Si un soporte se pierde o es sustraído, el usuario lo comunica **inmediatamente** al Responsable de Seguridad. Se activa el procedimiento de gestión de incidentes {{ proyecto.codigo_documento_base }}-204 con clasificación mínima ALTO. Si la información implicaba datos personales, se valora la activación del procedimiento de notificación de brechas {{ proyecto.codigo_documento_base }}-213 (notificación a la AEPD en menos de 72 horas).

## 9. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| F-215.1 | Autorización de Uso de Soporte | 3 años desde fin |
| F-215.2 | Hoja de Custodia | Permanente mientras el soporte exista |
| F-215.3 | Albarán de Expedición + PoD | 3 años |
| F-215.4 | Acta de Entrega/Devolución | 3 años |
| INV-soportes | Inventario de Soportes Extraíbles | Permanente |
| L-215 | Log de aperturas del armario | 12 meses |

## 10. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| Soportes inventariados / soportes en uso | reconciliación mensual | 100 % |
| % de soportes cifrados | soportes con cifrado activo / total INTERNA+ | 100 % |
| Pérdidas de soporte por trimestre | recuento | 0 |
| Cumplimiento de devolución en bajas | devoluciones < 24 h tras baja / total bajas | ≥ 95 % |

## 11. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Cambien las medidas mp.si.1-4 en la guía CCN-STIC 804.
- Se incorporen nuevos tipos de soporte al inventario.
- Cambie el catálogo de hardware aprobado.
- Se detecte una incidencia con soportes que requiera ajuste del control.

Responsabilidad de la revisión: **Responsable de la Seguridad**, con aprobación del **Comité de Seguridad** y notificación al **Responsable del Sistema**.
