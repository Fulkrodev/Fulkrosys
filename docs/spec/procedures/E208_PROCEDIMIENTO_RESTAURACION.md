# DOCUMENTO E-208 — PROCEDIMIENTO DE RESTAURACIÓN

**Es el procedimiento operativo que ejecuta la Política de Copias de Seguridad ({{ proyecto.codigo_documento_base }}-106) y materializa el Plan de Continuidad del Servicio ({{ proyecto.codigo_documento_base }}-109).** Define cómo se restaura información, sistemas o servicios desde una copia de seguridad — desde la decisión de activar la restauración hasta la verificación de que el servicio recuperado opera con normalidad.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-208"
titulo: "Procedimiento de Restauración"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_sistema.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-106, {{ proyecto.codigo_documento_base }}-109"
medidas_ens: ["op.cont.2", "mp.info.6"]
---

# PROCEDIMIENTO DE RESTAURACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-208 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los pasos operativos para la restauración de información, configuraciones, sistemas o servicios desde las copias de seguridad gestionadas conforme al procedimiento {{ proyecto.codigo_documento_base }}-207, garantizando el cumplimiento de los objetivos de tiempo (RTO) y de punto de recuperación (RPO) acordados para cada activo del alcance del SGSI.

Este procedimiento desarrolla la medida **op.cont.2 (continuidad del servicio — plan de continuidad)** del Anexo II del Real Decreto 311/2022 y se aplica de forma coordinada con la guía CCN-STIC 804.

## 2. ALCANCE

Aplica a toda restauración —parcial o total— de:

- Sistemas operativos y servidores virtualizados.
- Bases de datos y volúmenes de almacenamiento.
- Configuraciones de red y de aplicación.
- Buzones, ficheros y carpetas individuales solicitados por usuarios autorizados.
- Imágenes de servicios cloud (snapshots, backups gestionados por el proveedor).

Quedan excluidas las restauraciones de entornos puramente de desarrollo o pruebas que no formen parte del alcance del SGSI.

## 3. CASOS DE USO Y NIVEL DE AUTORIZACIÓN

| Caso | Solicitante autorizado | Aprobador | RTO objetivo |
|---|---|---|---|
| Recuperación de fichero individual borrado | Usuario afectado | Responsable del Sistema | 4 horas hábiles |
| Restauración de buzón completo | Responsable del área | Responsable del Sistema | 1 día hábil |
| Recuperación de base de datos completa | Responsable del Sistema | Responsable de Seguridad | Según RTO del activo (BIA E-400) |
| Restauración tras incidente de seguridad | Coordinador del ERI | Responsable de Seguridad | Inmediata, prioridad máxima |
| Activación de DR-site (fallo total) | Comité de Crisis | Director General o equivalente | Según RTO del Plan de Continuidad |
| Restauración a entorno de pruebas | Responsable del Sistema | Responsable del Sistema | 2 días hábiles |

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** Toda restauración a producción —incluso de un único fichero— requiere aprobación dual: una persona solicita y aprueba inicialmente, otra distinta autoriza la ejecución, dejando registro nominativo de ambas.
{% endif %}

## 4. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Solicitante** | Cumplimentar el formulario F-208 con identificación de los datos a restaurar, fecha objetivo y motivo. |
| **Responsable del Sistema** | Validar la solicitud, identificar la copia adecuada, ejecutar la restauración, verificar integridad y registrar resultados. |
| **Responsable de la Seguridad** | Autorizar restauraciones de criticidad alta o críticas, supervisar pruebas trimestrales, mantener el registro maestro de restauraciones. |
| **DPO** | Cuando la restauración implique datos personales, validar el cumplimiento del RGPD (no recuperar datos cuyo plazo de conservación haya expirado). |
| **Proveedor cloud** (si aplica) | Ejecutar la restauración bajo el modelo de responsabilidad compartida documentado en el contrato. |

## 5. FLUJO OPERATIVO

### Fase 1 — Solicitud y autorización (T+0 a T+1 hora)

**Responsable:** Solicitante.

1. Cumplimentar el formulario **F-208 — Solicitud de Restauración** con los siguientes campos obligatorios:
   - Identificación del activo a restaurar (servidor, ruta, base de datos, identificador del backup).
   - Fecha y hora objetivo de la versión a recuperar (RPO solicitado).
   - Motivo: pérdida accidental, corrupción, incidente de seguridad, prueba programada.
   - Plazo máximo en que se necesita el activo restaurado (RTO solicitado).
   - Datos personales implicados (sí/no) y, en caso afirmativo, base legal del tratamiento.

2. Remitir la solicitud al Responsable del Sistema mediante el sistema de tickets corporativo o, en caso de urgencia operativa, por canal telefónico con confirmación posterior por escrito.

3. El Responsable del Sistema valida la procedencia de la solicitud y, según la matriz del apartado 3, escala al aprobador correspondiente. La aprobación queda registrada con firma electrónica o, como mínimo, traza nominativa en el sistema de tickets.

### Fase 2 — Identificación de la copia y planificación (T+1 hora a T+4 horas)

**Responsable:** Responsable del Sistema.

4. Consultar el **Catálogo de Copias** (mantenido por el procedimiento {{ proyecto.codigo_documento_base }}-207) y localizar la copia que cumpla con el RPO solicitado.

5. Verificar que la copia esté **accesible y verificada** (las copias deben pasar verificación de integridad mensual, conforme al apartado 7 del procedimiento {{ proyecto.codigo_documento_base }}-207).

6. Si la copia más cercana al RPO solicitado no está disponible o ha fallado verificación, escalar al Responsable de Seguridad y seleccionar la siguiente copia válida documentando la desviación.

7. Estimar el tiempo de ejecución de la restauración con base en pruebas anteriores y comparar con el RTO solicitado. Si no es viable, comunicar al solicitante y reevaluar el alcance.

8. **Planificar la ventana de restauración:** entorno destino (producción / preproducción / DR), recursos necesarios (almacenamiento temporal, ancho de banda), impacto previsto en otros servicios.

### Fase 3 — Ejecución de la restauración (según RTO)

**Responsable:** Responsable del Sistema (con apoyo de operadores de sistemas autorizados).

9. **Aislar el entorno destino** si la restauración es por incidente de seguridad: desconectar de la red productiva hasta verificar que la copia no contiene la amenaza original (especialmente en restauraciones por ransomware).

10. Ejecutar la restauración utilizando exclusivamente las herramientas oficiales documentadas en la Instrucción Técnica IT-208-01 correspondiente al sistema de backup en uso ({% if cliente.backup_system %}{{ cliente.backup_system }}{% else %}Veeam, Commvault, Azure Backup, AWS Backup u otra solución corporativa{% endif %}).

11. Documentar en tiempo real las acciones realizadas: comandos ejecutados, parámetros, hora de inicio y fin de cada fase, incidencias.

12. Si la restauración requiere descifrado de datos cifrados con claves gestionadas por el procedimiento {{ proyecto.codigo_documento_base }}-232, registrar el uso de claves en el log correspondiente.

### Fase 4 — Verificación (inmediatamente posterior a la restauración)

**Responsable:** Responsable del Sistema, con validación funcional del solicitante.

13. **Verificación técnica:** comprobación de integridad de la información restaurada mediante:
    - Hash de los ficheros principales contrastado con el hash de origen si está disponible.
    - Conteo de registros si es base de datos.
    - Inicio correcto de servicios si es un sistema completo.
    - Pruebas de conexión y autenticación.

14. **Verificación funcional:** el solicitante (o usuario funcional designado) realiza pruebas representativas del uso real durante un máximo de 4 horas tras la restauración.

15. Solo cuando la verificación funcional sea positiva, el sistema restaurado se conecta a producción (si estaba aislado) o se entrega al solicitante.

### Fase 5 — Cierre y registro (T+24 horas máximo)

**Responsable:** Responsable del Sistema.

16. Cumplimentar el **registro R-208 — Acta de Restauración** con:
    - Identificador único de la restauración (`RST-AAAA-NNNN`).
    - Datos de la copia origen (fecha, identificador, hash de verificación).
    - Tiempos reales (RTO real vs RTO objetivo, RPO real vs RPO objetivo).
    - Personas que intervinieron (solicitante, ejecutor, verificador, aprobador).
    - Incidencias y desviaciones.
    - Resultado: COMPLETADA / COMPLETADA CON OBSERVACIONES / FALLIDA.

17. Si el resultado fue **FALLIDA** o **COMPLETADA CON OBSERVACIONES**, abrir una **No Conformidad** conforme al procedimiento {{ proyecto.codigo_documento_base }}-220 para análisis de causa raíz.

18. Comunicar el cierre al solicitante y, si la restauración fue consecuencia de un incidente, al Coordinador del ERI.

## 6. PRUEBAS PERIÓDICAS DE RESTAURACIÓN

Conforme al procedimiento {{ proyecto.codigo_documento_base }}-209 (Pruebas de Continuidad), se ejecutan las siguientes pruebas planificadas:

| Tipo de prueba | Frecuencia mínima | Categoría BÁSICA | MEDIA | ALTA |
|---|---|---|---|---|
| Restauración de fichero/carpeta individual | Mensual | ✓ | ✓ | ✓ |
| Restauración de base de datos representativa | Trimestral | — | ✓ | ✓ |
| Restauración completa de servidor | Semestral | — | ✓ | ✓ |
| Activación parcial de DR-site | Anual | — | — | ✓ |
| Activación completa de DR-site (BCP test) | Anual o bienal | — | — | ✓ |

Cada prueba genera un acta R-208 marcada como `tipo: prueba_programada` y se incorpora al cuadro de mando de continuidad presentado al Comité de Seguridad.

## 7. REGISTROS GENERADOS

| Código | Registro | Conservación mínima |
|---|---|---|
| F-208 | Solicitud de Restauración | 3 años |
| R-208 | Acta de Restauración | 6 años (12 si afecta a datos personales o evidencias de incidente) |
| L-208 | Log técnico de comandos ejecutados | 12 meses |

Todos los registros se almacenan en el repositorio documental del SGSI con control de versiones y firma electrónica del Responsable del Sistema.

## 8. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| Tasa de éxito de restauraciones | (restauraciones completadas OK / total) × 100 | ≥ 98 % |
| RTO real medio vs RTO objetivo | media(RTO_real / RTO_objetivo) | ≤ 1,0 |
| Cobertura de pruebas programadas | pruebas ejecutadas / pruebas planificadas | 100 % |
| Tiempo medio entre detección y restauración (incidentes) | media(T_restauracion - T_deteccion) | ≤ 8 h |

Los indicadores se reportan trimestralmente al Comité de Seguridad y anualmente en la Revisión por la Dirección ({{ proyecto.codigo_documento_base }}-219).

## 9. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando concurra alguna de las siguientes circunstancias:

- Cambio significativo en la arquitectura de copias de seguridad.
- Cambio de proveedor del sistema de backup.
- Detección de fallos sistemáticos en pruebas o restauraciones reales.
- Modificación del Real Decreto 311/2022 o de la guía CCN-STIC 804 que afecte a la medida op.cont.2.
- Incorporación de nuevos activos al alcance del SGSI con RTO/RPO distintos.

La revisión es responsabilidad del **Responsable del Sistema**, con aprobación del **Responsable de la Seguridad** y notificación al Comité de Seguridad.

## ANEXO I — Plantilla F-208 — Solicitud de Restauración

```
SOLICITUD DE RESTAURACIÓN — Doc {{ proyecto.codigo_documento_base }}-208 / F-208

Identificador (asignado por sistema): RST-_______________
Fecha de solicitud: __________________
Solicitante: ________________________
Cargo: _____________________________

Activo a restaurar (sistema, ruta, base de datos): ____________________
Identificador del backup origen (si conocido): ________________________
Fecha/hora del estado a recuperar (RPO solicitado): ___________________

Motivo:
[ ] Pérdida accidental
[ ] Corrupción de datos
[ ] Incidente de seguridad (referencia INC-_____________)
[ ] Prueba programada
[ ] Otro: _______________________

Datos personales implicados: [ ] Sí  [ ] No
Si Sí, base legal (RGPD art. 6/9): ________________________

Plazo máximo solicitado (RTO): ____ horas
Entorno destino: [ ] Producción  [ ] Preproducción  [ ] Aislado para análisis

Aprobación (firma electrónica): _______________________________
```
