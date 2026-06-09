# DOCUMENTO E-204-A — PROCEDIMIENTO DE RECOPILACIÓN Y CUSTODIA DE EVIDENCIAS

**Materializa la medida op.exp.8 (Registro de la actividad) del Anexo II del ENS** en su vertiente forense, y desarrolla el apartado 5.3 del procedimiento de gestión de incidentes ({{ proyecto.codigo_documento_base }}-204). Sin un procedimiento sólido de cadena de custodia, las evidencias recopiladas durante un incidente pueden carecer de validez en sede judicial.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-204-A"
titulo: "Procedimiento de Recopilación y Custodia de Evidencias"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-108"
---

# PROCEDIMIENTO DE RECOPILACIÓN Y CUSTODIA DE EVIDENCIAS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-204-A — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método mediante el cual {{ cliente.razon_social }} recopila, identifica, preserva, analiza y custodia las evidencias derivadas de incidentes de seguridad, investigaciones internas o requerimientos legales, garantizando su integridad, autenticidad y trazabilidad a lo largo de toda la cadena de custodia, de modo que conserven su valor probatorio en sede administrativa, judicial o disciplinaria.

## 2. ALCANCE

Aplica a toda evidencia, en cualquier formato, recopilada en el contexto de:

a) La gestión de un incidente de seguridad conforme al procedimiento {{ proyecto.codigo_documento_base }}-204.

b) Una investigación interna por sospecha de incumplimiento de la normativa interna.

c) Un requerimiento de autoridad administrativa o judicial.

d) Una auditoría interna o externa que requiera evidencias específicas.

## 3. DEFINICIONES OPERATIVAS

a) **Evidencia digital:** cualquier información o dato de valor probatorio almacenado, recibido o transmitido por un dispositivo electrónico.

b) **Cadena de custodia:** documentación cronológica que registra todas las personas y procesos que han manipulado una evidencia desde su recopilación hasta su uso final, garantizando su integridad.

c) **Hash:** función criptográfica que produce una huella única de un conjunto de datos, permitiendo verificar posteriormente que no han sido modificados.

d) **Integridad:** propiedad de la evidencia de no haber sido alterada desde su recopilación.

e) **Volátil:** información que se pierde cuando el sistema se apaga o reinicia (memoria RAM, conexiones de red activas, procesos en ejecución).

f) **No volátil:** información que persiste tras el apagado del sistema (discos duros, ficheros, logs almacenados).

## 4. PRINCIPIOS GENERALES

### 4.1 No alteración de la evidencia original

Cuando sea técnicamente posible, las acciones de análisis se realizarán sobre **copias** de la evidencia, preservando el original sin alteraciones. Cuando no sea posible, se documentarán meticulosamente todas las acciones realizadas sobre el original.

### 4.2 Documentación exhaustiva

Toda actuación realizada sobre una evidencia se documentará de inmediato, incluyendo persona, fecha, hora exacta, herramientas utilizadas y resultado obtenido.

### 4.3 Cadena de custodia ininterrumpida

La cadena de custodia debe ser **continua y completa** desde el momento de la recopilación hasta el destino final de la evidencia. Cualquier interrupción o transferencia se documenta.

### 4.4 Mínima intervención

Solo el personal autorizado y debidamente formado intervendrá en la recopilación y manipulación de evidencias. Se evitará en todo momento la intervención de personas no autorizadas.

### 4.5 Orden de volatilidad

En la recopilación de evidencias se respetará el principio del **orden de volatilidad**, priorizando la captura de la información más volátil antes de que se pierda.

## 5. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Coordinador de evidencias** ({{ responsables.responsable_seguridad.nombre }}) | Coordinación general, autorización de las acciones, custodia del registro de cadena de custodia |
| **Analista forense interno** | Ejecución técnica de la recopilación y análisis preliminar |
| **Analista forense externo** (si procede) | Análisis forense en profundidad |
| **Asesor legal** | Asesoramiento sobre validez probatoria y requerimientos formales |
| **Testigo independiente** | Cuando proceda, presencia durante la recopilación para refrendar la integridad del procedimiento |

## 6. ORDEN DE VOLATILIDAD

La recopilación de evidencias debe seguir el siguiente orden, de mayor a menor volatilidad:

1. Registros de CPU, caché y registros del sistema.
2. Memoria RAM.
3. Estado de la red: conexiones activas, tablas de enrutamiento, ARP, sesiones.
4. Procesos en ejecución.
5. Información de discos: ficheros temporales, swap, slack space.
6. Datos en discos duros y otros soportes no volátiles.
7. Logs locales del sistema.
8. Configuración del sistema y software instalado.
9. Información de soportes físicos extraídos.
10. Backups y archivos remotos.

## 7. PROCESO DE RECOPILACIÓN

### 7.1 Decisión y autorización

**Paso 1.** Cuando en el contexto de un incidente o investigación se decida iniciar la recopilación de evidencias, el Coordinador de evidencias emite una **autorización formal** que indique:

- Identificador del caso (vinculado al `INC-AAAA-NNNN` del incidente, si procede).
- Sistemas o activos sobre los que se va a actuar.
- Tipo de evidencia a recopilar.
- Personal autorizado para intervenir.
- Acciones autorizadas y restricciones específicas.

### 7.2 Preparación

**Paso 2.** Antes de iniciar la recopilación, el equipo asignado prepara:

- Herramientas forenses verificadas (write blockers, software forense con versiones documentadas).
- Soportes vírgenes y verificados para almacenar las copias.
- Plantilla de la cadena de custodia (Anexo I).
- Material de identificación y embalaje seguro.
- Reloj sincronizado con fuente fiable para anotación de marcas de tiempo.

### 7.3 Llegada al sistema y observación inicial

**Paso 3.** Al llegar al sistema o ubicación, el equipo:

- Documenta el estado encontrado (encendido/apagado, sesión activa, mensajes en pantalla).
- Captura fotografías del estado físico cuando proceda.
- Identifica testigos presentes.
- Anota la fecha y hora exactas de inicio de la actuación.

### 7.4 Recopilación de evidencias volátiles (solo si el sistema está encendido)

**Paso 4.** Si el sistema está encendido, **antes de cualquier otra acción**, se procede a la recopilación de evidencias volátiles siguiendo el orden de volatilidad:

- Captura de la memoria RAM mediante herramienta forense.
- Listado de procesos en ejecución.
- Captura de conexiones de red activas.
- Captura de tablas ARP y enrutamiento.
- Captura del estado del sistema.

**Paso 5.** Cada captura se almacena en soporte externo verificado y se calcula su hash SHA-256 inmediatamente.

### 7.5 Aislamiento del sistema

**Paso 6.** Tras la recopilación de evidencias volátiles, el sistema se **aisla de la red** desconectando físicamente los cables de red y deshabilitando interfaces inalámbricas, evitando que un atacante remoto pueda destruir evidencias.

**Paso 7.** No se debe apagar el sistema mediante el procedimiento normal del sistema operativo, salvo decisión expresa del Coordinador. Si se debe apagar, se hará desconectando la alimentación para preservar el estado del disco.

### 7.6 Recopilación de evidencias no volátiles

**Paso 8.** Las evidencias no volátiles (discos duros, soportes extraíbles) se obtienen preferentemente mediante:

- Imagen forense bit a bit del soporte completo, utilizando write-blocker.
- Cálculo del hash SHA-256 del original y de la imagen para verificar la copia.
- Verificación de que ambos hashes coinciden.

**Paso 9.** Si el sistema está en producción y no puede ser apagado, se realiza una **adquisición en caliente** del disco mediante herramientas que permitan obtener una imagen consistente del sistema en uso.

### 7.7 Recopilación de evidencias lógicas

**Paso 10.** Cuando la evidencia consista en ficheros o registros específicos (logs, capturas de tráfico, mensajes de correo, registros de aplicaciones), se exportan estos elementos preservando su contexto y metadatos.

**Paso 11.** Se calcula y registra el hash SHA-256 de cada fichero exportado.

### 7.8 Identificación y embalaje

**Paso 12.** Cada evidencia recopilada recibe una **etiqueta de identificación única** que incluye:

- Identificador único en formato `EVI-AAAA-NNNN` (donde AAAA es el año y NNNN un correlativo).
- Identificador del caso.
- Descripción breve.
- Hash SHA-256.
- Fecha, hora y persona que la recopila.

**Paso 13.** Las evidencias físicas se embalan en bolsas o sobres antiestáticos, debidamente sellados y firmados por la persona que las custodia.

## 8. CADENA DE CUSTODIA

### 8.1 Apertura del registro

**Paso 14.** Para cada evidencia se abre un **registro de cadena de custodia** (Anexo I) que se mantiene desde la recopilación hasta el destino final.

### 8.2 Registro de movimientos

**Paso 15.** Cada vez que la evidencia cambia de manos, lugar, estado o se le aplica cualquier acción, se registra en la cadena de custodia:

- Fecha y hora exactas.
- Persona que entrega y persona que recibe (con firma).
- Acción realizada.
- Lugar de destino.
- Verificación del hash en cada transferencia (cuando sea técnicamente posible).
- Observaciones relevantes.

### 8.3 Almacenamiento

**Paso 16.** Las evidencias se custodian en un lugar seguro con acceso restringido, preferentemente:

- Caja fuerte o armario blindado con control de acceso.
- Sala con acceso restringido y monitorización.
- Para evidencias digitales, repositorio cifrado con control de acceso.

**Paso 17.** El acceso al almacenamiento se documenta y se restringe al personal estrictamente autorizado.

## 9. ANÁLISIS

### 9.1 Análisis sobre copias

**Paso 18.** El análisis se realiza sobre **copias de trabajo**, nunca sobre el original, salvo casos excepcionales debidamente justificados.

**Paso 19.** Las copias de trabajo se generan a partir de la imagen forense original y se verifica que su hash coincide con el original.

### 9.2 Documentación del análisis

**Paso 20.** Cada acción de análisis se documenta indicando:

- Herramienta utilizada y versión.
- Comando o procedimiento ejecutado.
- Salida obtenida.
- Interpretación de los resultados.
- Persona que realiza el análisis y fecha.

### 9.3 Informe forense

**Paso 21.** Al finalizar el análisis se elabora un **Informe Forense** que incluye:

- Resumen ejecutivo.
- Antecedentes del caso.
- Descripción de las evidencias analizadas.
- Metodología utilizada.
- Hallazgos detallados.
- Conclusiones.
- Anexos técnicos.

**Paso 22.** El informe se firma electrónicamente y se conserva junto con las evidencias.

## 10. DESTINO FINAL DE LAS EVIDENCIAS

**Paso 23.** Las evidencias se conservan durante el plazo necesario para cumplir su finalidad y, en cualquier caso, durante el **plazo de prescripción** de las acciones legales que pudieran derivarse del caso.

**Paso 24.** Transcurrido el plazo de conservación, las evidencias se destruyen mediante procedimientos que garanticen la imposibilidad de recuperación, conforme al apartado 9 de la Política de Clasificación ({{ proyecto.codigo_documento_base }}-104).

**Paso 25.** La destrucción se documenta en la propia cadena de custodia y mediante **acta de destrucción** firmada por dos personas.

## 11. INDICADORES

| Indicador | Objetivo |
|---|---|
| Evidencias con cadena de custodia completa | 100% |
| Verificaciones de hash exitosas en transferencias | 100% |
| Tiempo medio entre detección de incidente y recopilación de evidencias críticas | < 4 horas |
| Personal forense con formación específica vigente | 100% |

## 12. ANEXOS

- **Anexo I:** Plantilla de la cadena de custodia
- **Anexo II:** Etiqueta de identificación de evidencias
- **Anexo III:** Plantilla del Informe Forense
- **Anexo IV:** Acta de destrucción de evidencias
- **Anexo V:** Listado de herramientas forenses autorizadas

---

**Documento {{ proyecto.codigo_documento_base }}-204-A — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
