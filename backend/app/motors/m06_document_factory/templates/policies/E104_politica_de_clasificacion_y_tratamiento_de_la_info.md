# DOCUMENTO E-104 — POLÍTICA DE CLASIFICACIÓN Y TRATAMIENTO DE LA INFORMACIÓN

**La política transversal a todas las demás.** Materializa las medidas mp.info.1 (Datos personales), mp.info.2 (Calificación de la información), mp.info.3 (Firma electrónica), mp.info.4 (Sellos de tiempo) y mp.info.5 (Limpieza de documentos) del Anexo II del ENS, así como los controles A.5.12, A.5.13, A.5.14 (Information classification, labelling, transfer) y A.8.10, A.8.12 (Information deletion, Data leakage prevention) de ISO/IEC 27001:2022. Sin clasificación correcta de la información, ninguna otra medida puede aplicarse de forma proporcionada.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-104"
titulo: "Política de Clasificación y Tratamiento de la Información"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE CLASIFICACIÓN Y TRATAMIENTO DE LA INFORMACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-104 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento establece los principios y reglas aplicables a la **clasificación de la información** tratada por {{ cliente.razon_social }}, así como los criterios y obligaciones para su **tratamiento, etiquetado, conservación, transmisión, almacenamiento y destrucción** a lo largo de todo su ciclo de vida, con la finalidad de garantizar que la información reciba en cada momento un nivel de protección proporcional a su valor, sensibilidad y criticidad.

Esta Política da cumplimiento a las medidas **mp.info.1 (Datos personales)**, **mp.info.2 (Calificación de la información)**, **mp.info.3 (Firma electrónica)**, **mp.info.4 (Sellos de tiempo)** y **mp.info.5 (Limpieza de documentos)** del Anexo II del Real Decreto 311/2022, y se complementa con el Reglamento (UE) 2016/679 (RGPD), la Ley Orgánica 3/2018 (LOPDGDD) y, cuando proceda, el Reglamento (UE) 910/2014 (eIDAS).

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a:

a) Toda la información tratada por la Entidad, en cualquier formato (electrónico, impreso, audiovisual u otros).

b) Todo soporte que contenga información de la Entidad, incluyendo equipos, dispositivos móviles, soportes extraíbles, archivos físicos y servicios cloud.

c) Toda la información en cualquier estado del ciclo de vida: creación, captura, recepción, almacenamiento, uso, transmisión, archivado y destrucción.

d) Todo el personal y los terceros con acceso a información de la Entidad.

## 3. PRINCIPIOS

### 3.1 Proporcionalidad de las medidas

Las medidas de protección aplicables a cada conjunto de información serán proporcionales a su clasificación, evitando tanto la sobreprotección innecesaria de información poco sensible como la subprotección de información crítica.

### 3.2 Necesidad de saber

El acceso a la información se rige por el principio de necesidad de saber, conforme se desarrolla en el documento {{ proyecto.codigo_documento_base }}-101.

### 3.3 Trazabilidad del ciclo de vida

Toda actuación relevante sobre la información (creación, modificación, transmisión, eliminación) será trazable en función de su clasificación.

### 3.4 Etiquetado obligatorio

Toda información clasificada como sensible llevará un etiquetado claramente visible que permita a su receptor identificar el nivel de protección requerido y las restricciones aplicables.

### 3.5 Responsabilidad del propietario

Cada conjunto de información tendrá un **propietario** identificado, responsable de su clasificación, de su mantenimiento y de la autorización de los accesos.

## 4. NIVELES DE CLASIFICACIÓN

A los efectos de la presente Política, la información tratada por la Entidad se clasifica en los siguientes niveles, alineados con las dimensiones de seguridad del Anexo I del ENS y con las prácticas habituales del sector:

### 4.1 PÚBLICA

**Definición.** Información cuya difusión sin restricciones no genera ningún perjuicio para la Entidad ni para sus partes interesadas y que ha sido formalmente autorizada para su difusión pública.

**Ejemplos:** comunicaciones de prensa publicadas, información disponible en la página web pública, estadísticas anonimizadas publicadas, normativa interna aprobada para difusión externa.

**Etiqueta sugerida:** PÚBLICA

### 4.2 INTERNA

**Definición.** Información cuyo destinatario natural es el personal de la Entidad y cuya divulgación no autorizada al exterior no produciría un perjuicio significativo, pero cuya difusión amplia tampoco está justificada por las necesidades del servicio.

**Ejemplos:** organigramas internos, comunicaciones internas no confidenciales, manuales de procedimiento operativos, normativa interna de uso ordinario.

**Etiqueta sugerida:** INTERNA

### 4.3 CONFIDENCIAL

**Definición.** Información cuya divulgación no autorizada produciría un perjuicio relevante para la Entidad, sus partes interesadas o terceros, y cuyo acceso debe restringirse a las personas que la necesiten estrictamente para el desempeño de sus funciones.

**Ejemplos:** contratos con clientes y proveedores, información financiera no publicada, planes estratégicos, datos personales de carácter ordinario, información comercial sensible, código fuente de aplicaciones propias, configuraciones detalladas de sistemas.

**Etiqueta sugerida:** CONFIDENCIAL

### 4.4 RESTRINGIDA

**Definición.** Información de máxima sensibilidad cuya divulgación no autorizada produciría un perjuicio grave, irreversible o de muy difícil reparación para la Entidad, sus partes interesadas o terceros, y cuyo acceso debe restringirse a un número muy reducido de personas debidamente autorizadas.

**Ejemplos:** datos personales de categorías especiales conforme al artículo 9 del RGPD, secretos comerciales o industriales, claves criptográficas maestras, información clasificada como nivel ALTO en cualquier dimensión del ENS, información sometida a obligación de secreto profesional.

**Etiqueta sugerida:** RESTRINGIDA

### 4.5 Correspondencia con las dimensiones del ENS

A efectos del cumplimiento del ENS, la correspondencia entre los niveles de clasificación de la presente Política y los niveles de las dimensiones de seguridad del Anexo I del ENS será la siguiente:

| Nivel de clasificación | Confidencialidad ENS | Integridad ENS | Disponibilidad ENS | Autenticidad ENS | Trazabilidad ENS |
|---|---|---|---|---|---|
| PÚBLICA | Sin requisito | BAJO | BAJO | BAJO | BAJO |
| INTERNA | BAJO | BAJO/MEDIO | BAJO/MEDIO | BAJO | BAJO |
| CONFIDENCIAL | MEDIO | MEDIO | MEDIO/ALTO | MEDIO | MEDIO |
| RESTRINGIDA | ALTO | ALTO | ALTO | ALTO | ALTO |

Esta tabla constituye una guía general; la asignación específica de niveles a cada conjunto de información concreto se realizará en el correspondiente análisis del Anexo I del ENS.

## 5. PROCESO DE CLASIFICACIÓN

### 5.1 Responsabilidad

La clasificación inicial de la información corresponde al **Responsable de la Información** (rol del artículo 11 del ENS), conforme se desarrolla en el documento {{ proyecto.codigo_documento_base }}-100 (Anexo de Roles), en coordinación con quien la haya generado o capturado.

### 5.2 Criterios de decisión

Para clasificar la información, el Responsable de la Información considerará, al menos:

a) La naturaleza intrínseca de la información (datos personales, secretos comerciales, información financiera, etc.).

b) Las obligaciones legales o contractuales aplicables.

c) El impacto potencial de su divulgación no autorizada para la Entidad y para terceros.

d) El periodo de validez de la clasificación, que puede ser limitado en el tiempo (información embargada que pasa a pública en una fecha determinada, por ejemplo).

### 5.3 Revisión de la clasificación

La clasificación de la información será objeto de revisión cuando:

a) Cambien las circunstancias que motivaron la clasificación inicial.

b) Transcurra el periodo de validez establecido en su caso.

c) Se produzcan modificaciones en el marco legal aplicable.

d) Se proceda a la revisión periódica del Análisis de Riesgos.

### 5.4 Reclasificación

Cualquier persona que considere que una información concreta está clasificada incorrectamente podrá proponer su reclasificación al Responsable de la Información, quien adoptará la decisión motivada que proceda.

## 6. ETIQUETADO

### 6.1 Documentos electrónicos

Los documentos electrónicos clasificados como CONFIDENCIAL o RESTRINGIDO incluirán una marca de clasificación visible en, al menos:

a) La cabecera o el pie de cada página.

b) Los metadatos del documento, cuando el formato lo permita.

Los documentos clasificados como PÚBLICA o INTERNA podrán llevar marca de clasificación, pero no es obligatorio salvo que lo establezca un procedimiento específico.

### 6.2 Documentos en papel

Los documentos en papel clasificados como CONFIDENCIAL o RESTRINGIDO llevarán la marca de clasificación claramente visible en el anverso y, cuando sean documentos de varias páginas, en cada una de ellas.

### 6.3 Mensajes de correo electrónico

Los mensajes de correo electrónico que contengan información CONFIDENCIAL o RESTRINGIDA incluirán la indicación correspondiente en el asunto del mensaje, mediante prefijos del tipo `[CONFIDENCIAL]` o `[RESTRINGIDA]`, y, cuando técnicamente sea posible, llevarán cifrado de extremo a extremo.

### 6.4 Soportes extraíbles

Todo soporte extraíble (memoria USB, disco duro externo, óptico u otros) que contenga información CONFIDENCIAL o RESTRINGIDA llevará una etiqueta física visible que indique su nivel de clasificación.

## 7. TRATAMIENTO POR ESTADO DEL CICLO DE VIDA

### 7.1 Almacenamiento

Las medidas de protección durante el almacenamiento se aplicarán según el siguiente cuadro:

| Nivel | Medidas mínimas de almacenamiento |
|---|---|
| PÚBLICA | Sin requisitos específicos |
| INTERNA | Acceso restringido a personal de la Entidad. Sistemas con autenticación. |
| CONFIDENCIAL | Acceso restringido por necesidad de saber. Cifrado en reposo recomendable. Copias de seguridad cifradas. |
| RESTRINGIDA | Acceso limitado a un número reducido de personas autorizadas. Cifrado obligatorio en reposo. Copias de seguridad cifradas y en ubicación física separada. Trazabilidad completa de los accesos. |

### 7.2 Transmisión

La transmisión de información se ajustará al siguiente cuadro:

| Nivel | Medidas mínimas de transmisión |
|---|---|
| PÚBLICA | Sin requisitos específicos |
| INTERNA | Canales corporativos. Cifrado en tránsito recomendable cuando atraviese redes externas. |
| CONFIDENCIAL | Cifrado obligatorio en tránsito (TLS 1.2 o superior, VPN, etc.). Verificación de la identidad del destinatario. |
| RESTRINGIDA | Cifrado obligatorio extremo a extremo. Verificación reforzada del destinatario. Confirmación de recepción. Limitación del número de copias. |

### 7.3 Duplicación

Se evitará la creación innecesaria de copias de información clasificada como CONFIDENCIAL o RESTRINGIDA. Cuando sea necesario duplicar dicha información, las copias estarán sujetas a las mismas medidas de protección que el original y serán objeto de control de inventario.

### 7.4 Almacenamiento en dispositivos personales

Queda prohibido el almacenamiento de información clasificada como CONFIDENCIAL o RESTRINGIDA en dispositivos personales del personal, salvo en los supuestos expresamente autorizados por el documento {{ proyecto.codigo_documento_base }}-117 (Política de Trabajo a Distancia y Movilidad) y siempre que se apliquen medidas de protección equivalentes a las exigidas para los dispositivos corporativos.

### 7.5 Limpieza de metadatos

Antes de la difusión externa de un documento, especialmente cuando contenga información sensible, se procederá a la **limpieza de metadatos** que pudieran revelar información no destinada a la difusión, conforme a la medida mp.info.5 (Limpieza de documentos) del Anexo II del ENS.

## 8. CONSERVACIÓN Y ARCHIVO

### 8.1 Periodos de conservación

La información se conservará durante el tiempo estrictamente necesario para los fines para los que ha sido tratada, y en todo caso durante los plazos legalmente establecidos.

Los periodos de conservación específicos para los principales tipos de información se documentarán en el **Calendario de Conservación**, mantenido por el Responsable de la Información en coordinación con el Responsable de la Seguridad y, cuando proceda, con el Delegado de Protección de Datos.

### 8.2 Datos personales

Los plazos de conservación de los datos personales atenderán a las exigencias del principio de limitación del plazo de conservación previsto en el artículo 5.1.e) del RGPD, así como a las obligaciones legales específicas aplicables.

### 8.3 Bloqueo

En el caso de los datos personales, transcurridos los plazos de conservación pertinentes, los datos serán bloqueados conforme al artículo 32 de la LOPDGDD, manteniéndose a disposición exclusiva de jueces, tribunales, Ministerio Fiscal o Administraciones Públicas competentes durante el plazo de prescripción de las acciones legales que pudieran derivarse del tratamiento, transcurrido el cual procederá a la supresión definitiva.

### 8.4 Archivo histórico

La información que deba conservarse por su valor histórico, jurídico, contable o documental se transferirá al archivo histórico de la Entidad conforme a los procedimientos correspondientes, manteniendo el nivel de clasificación que corresponda en cada momento.

## 9. DESTRUCCIÓN Y ELIMINACIÓN

### 9.1 Principio general

La eliminación de la información se realizará mediante procedimientos que garanticen la imposibilidad de su recuperación, en proporción a su nivel de clasificación.

### 9.2 Métodos por nivel

| Nivel | Métodos admitidos de destrucción |
|---|---|
| PÚBLICA | Eliminación ordinaria |
| INTERNA | Eliminación ordinaria. En soportes electrónicos: borrado lógico. |
| CONFIDENCIAL | Soportes electrónicos: borrado seguro mediante sobreescritura múltiple o desmagnetización. Papel: trituración con corte cruzado de seguridad mínima nivel P-3 conforme a UNE-EN 15713. |
| RESTRINGIDA | Soportes electrónicos: destrucción física del soporte o borrado seguro acreditado. Papel: trituración nivel P-5 o superior. Acta de destrucción documentada y firmada. |

### 9.3 Destrucción por proveedores especializados

Cuando la destrucción se confíe a proveedores especializados, estos cumplirán las exigencias del documento {{ proyecto.codigo_documento_base }}-112 (Política de Seguridad en las Relaciones con Proveedores) y emitirán los correspondientes certificados de destrucción.

### 9.4 Datos personales

La eliminación de datos personales atenderá a lo establecido en el artículo 17 del RGPD (derecho de supresión) y al apartado 8.3 anterior en lo relativo al bloqueo previo a la supresión definitiva.

## 10. FIRMA ELECTRÓNICA Y SELLOS DE TIEMPO

Cuando la integridad o autenticidad de la información así lo requieran, se utilizará la firma electrónica conforme a las exigencias del Reglamento (UE) 910/2014 (eIDAS) y de la guía CCN-STIC 807 Anexo 1 sobre Prestadores de Servicios de Confianza.

Los sellos de tiempo cualificados se utilizarán cuando sea necesario acreditar fehacientemente la existencia de la información en una fecha y hora determinadas, especialmente para evidencias en procedimientos administrativos o judiciales.

La gestión operativa de la firma electrónica y los sellos de tiempo se desarrolla en el documento {{ proyecto.codigo_documento_base }}-119 (Política de Firma Electrónica y Sellos de Tiempo).

## 11. INCUMPLIMIENTO

El tratamiento de información en contradicción con la presente Política, en particular el tratamiento, copia, transmisión o difusión no autorizada de información clasificada como CONFIDENCIAL o RESTRINGIDA, podrá dar lugar a la apertura del correspondiente expediente disciplinario, conforme al régimen sancionador interno aplicable y a la legislación laboral o estatutaria vigente, sin perjuicio de las responsabilidades civiles, administrativas o penales que correspondan.

## 12. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo.

---

**Documento {{ proyecto.codigo_documento_base }}-104 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```
