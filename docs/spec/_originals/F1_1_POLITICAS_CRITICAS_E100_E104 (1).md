# F1.1 — POLÍTICAS CRÍTICAS DEL SGSI ENS — TEXTO LEGAL REAL EN ESPAÑOL (E-100 a E-104)

**Plan 100/100 FULKRO — Bloque 1 de plantillas reales**
**Versión:** 1.0 — 9 de abril de 2026
**Destinatarios:** Claude Code (para conversión a `.docx` con `docxtpl`) + Marcos (para revisión legal por consultor ENS senior antes del primer cliente real)

---

## ADVERTENCIA LEGAL CRÍTICA PARA MARCOS

**Estas políticas son redacción real, no placeholders.** Están escritas con vocabulario jurídico español formal, alineadas con el Real Decreto 311/2022, la LOPDGDD, ISO/IEC 27001:2022 y las guías CCN-STIC 805 y 815. Sin embargo:

1. **No soy abogado.** El texto que sigue es de altísima calidad técnica y formal pero **debe ser revisado por un abogado TIC español o un consultor ENS senior antes de usar con un cliente real**. Presupuesto orientativo: 800-1.500 € por una revisión legal completa de las 27 políticas E-100 a E-126.

2. **Adaptación obligatoria al cliente.** Los placeholders Jinja2 (`{{ cliente.razon_social }}`, etc.) son los valores que el Motor 6 (Document Factory) sustituirá automáticamente desde la información recogida en el onboarding del Motor 16. Pero hay decisiones de redacción que cada cliente puede querer tunear (p.ej. el nombre exacto del órgano que aprueba, niveles de exigencia internos, sanciones disciplinarias específicas). Esas variantes se gestionan con bloques `{% if %}` también incluidos.

3. **Las políticas referencian artículos concretos del RD 311/2022.** Si el RD se modifica en el futuro (cosa que ocurrirá), el Motor 24 (Regulatory Radar) detectará el cambio y FULKRO debe regenerar las políticas con la versión nueva. Esto está previsto en el ciclo del Motor 4.

4. **Estilo: castellano peninsular formal jurídico-administrativo.** Tutea/usted: **usted**. Evita anglicismos. Frases largas con subordinadas. Numeración decimal estilo BOE. Mayúsculas en términos definidos.

---

## CATÁLOGO DE PLACEHOLDERS USADOS

Antes de las políticas, este es el contrato de variables que el Motor 6 debe poder rellenar desde el modelo `OrganizacionCliente` del Motor 16. Si falta alguna variable en runtime, el Motor 6 debe abortar la generación con error explícito (no rellenar con cadenas vacías).

```python
# Modelo de datos requerido por las 5 políticas E-100 a E-104
{
    "cliente": {
        "razon_social": "Empresa Ejemplo, S.L.",
        "nombre_corto": "Empresa Ejemplo",
        "nif": "B12345678",
        "domicilio_social": "Calle Mayor 1, 28013 Madrid",
        "naturaleza_juridica": "sociedad limitada",  # o "ayuntamiento", "fundación", "sociedad anónima", etc.
        "es_sector_publico": False,
        "organo_superior": "Consejo de Administración",  # o "Pleno", "Patronato", "Junta General"
        "organo_aprobador_politicas": "Consejo de Administración",
        "fecha_constitucion": "2015-03-12",
        "sector_actividad": "servicios tecnológicos",
        "actividades_principales": ["desarrollo de software", "consultoría TIC"],
        "ambito_geografico": "España",
        "numero_empleados": 85,
        "sedes": [
            {"nombre": "Sede Madrid", "direccion": "Calle Mayor 1, 28013 Madrid", "es_principal": True},
            {"nombre": "Sede Barcelona", "direccion": "Avda. Diagonal 123, 08008 Barcelona", "es_principal": False}
        ]
    },
    "proyecto": {
        "categoria_ens": "MEDIA",  # BÁSICA | MEDIA | ALTA
        "alcance": {
            "descripcion": "El sistema de información que da soporte al servicio de tramitación electrónica de Empresa Ejemplo, S.L., incluyendo los servicios cloud asociados y la infraestructura corporativa de Madrid y Barcelona.",
            "servicios_incluidos": ["Portal web", "API REST", "Base de datos central", "Servicio de autenticación"],
            "exclusiones": "Quedan expresamente excluidos los entornos de desarrollo y pruebas no productivos."
        },
        "fecha_aprobacion_inicial": "2026-05-15",
        "version_actual": "1.0",
        "codigo_documento_base": "POL",
        "proxima_revision": "2027-05-15"
    },
    "responsables": {
        "responsable_informacion": {"nombre": "Ana García López", "cargo": "Directora de Operaciones", "email": "agarcia@ejemplo.es"},
        "responsable_servicio": {"nombre": "Pedro Sánchez Martínez", "cargo": "Director Comercial", "email": "psanchez@ejemplo.es"},
        "responsable_seguridad": {"nombre": "Marta Fernández Ruiz", "cargo": "CISO", "email": "mfernandez@ejemplo.es"},
        "responsable_sistema": {"nombre": "Luis Torres Vega", "cargo": "Director TI", "email": "ltorres@ejemplo.es"},
        "delegado_proteccion_datos": {"nombre": "Carmen López Díaz", "cargo": "DPO externo", "email": "dpo@ejemplo.es"},
        "comite_seguridad": {
            "presidente": "Marta Fernández Ruiz",
            "miembros": ["Marta Fernández Ruiz", "Luis Torres Vega", "Ana García López", "Pedro Sánchez Martínez", "Carmen López Díaz"],
            "frecuencia_reuniones": "trimestral",
            "secretario": "Luis Torres Vega"
        }
    }
}
```

---

# DOCUMENTO E-100 — POLÍTICA DE SEGURIDAD DE LA INFORMACIÓN

**Es la política madre.** Sin ella aprobada y firmada por el órgano superior, no hay SGSI ENS posible. Es el primer documento que pide cualquier auditor ENAC y el primero que mira la guía CCN-STIC 805. Esta versión está alineada con el artículo 12 del RD 311/2022 (Política de seguridad y requisitos mínimos) y con CCN-STIC 805 v2025.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-100"
titulo: "Política de Seguridad de la Información"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE SEGURIDAD DE LA INFORMACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-100 — Versión {{ proyecto.version_actual }}**

---

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción del cambio | Aprobado por |
|---|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.responsable_seguridad.nombre }} | Versión inicial. Aprobación primera del SGSI conforme al RD 311/2022. | {{ cliente.organo_aprobador_politicas }} |

## REGISTRO DE APROBACIÓN

La presente Política de Seguridad de la Información ha sido elaborada por {{ responsables.responsable_seguridad.nombre }}, en su condición de {{ responsables.responsable_seguridad.cargo }} de {{ cliente.razon_social }}, revisada por el Comité de Seguridad de la Información de la entidad y aprobada formalmente por {{ cliente.organo_aprobador_politicas }} en la sesión celebrada el {{ proyecto.fecha_aprobacion_inicial }}.

| Rol | Nombre | Cargo | Firma | Fecha |
|---|---|---|---|---|
| Elaboración | {{ responsables.responsable_seguridad.nombre }} | {{ responsables.responsable_seguridad.cargo }} | _____________ | {{ proyecto.fecha_aprobacion_inicial }} |
| Revisión | {{ responsables.comite_seguridad.presidente }} | Presidente Comité de Seguridad | _____________ | {{ proyecto.fecha_aprobacion_inicial }} |
| Aprobación | _En representación del_ {{ cliente.organo_aprobador_politicas }} | _____________ | _____________ | {{ proyecto.fecha_aprobacion_inicial }} |

---

## 1. INTRODUCCIÓN Y DECLARACIÓN INSTITUCIONAL

{{ cliente.razon_social }}, con NIF {{ cliente.nif }} y domicilio social en {{ cliente.domicilio_social }} (en adelante, **"la Entidad"**), consciente de su dependencia de los sistemas y servicios de información para el desarrollo de sus actividades, y comprometida con la protección efectiva de los datos personales, la información corporativa y los servicios prestados a sus partes interesadas, mediante la presente Política manifiesta su compromiso firme e inequívoco con la seguridad de la información.

La seguridad de la información, entendida como la preservación de la confidencialidad, la integridad, la disponibilidad, la autenticidad y la trazabilidad de la información tratada y de los servicios prestados por sus sistemas, constituye un objetivo estratégico de la Entidad y forma parte integral de su modelo de gobernanza.

A tal efecto, la Entidad adopta esta Política como norma fundamental de su Sistema de Gestión de la Seguridad de la Información (en adelante, **"SGSI"**), conformado conforme a lo dispuesto en el Real Decreto 311/2022, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad (en adelante, **"ENS"**), y, supletoriamente, conforme a las buenas prácticas reconocidas internacionalmente, en particular las recogidas en la norma UNE-EN ISO/IEC 27001:2022.

## 2. OBJETO Y FINALIDAD

La presente Política tiene por objeto establecer el marco general de gobernanza, principios, objetivos y responsabilidades en materia de seguridad de la información en {{ cliente.razon_social }}, garantizando que:

a) La información y los servicios prestados estén protegidos frente a amenazas internas o externas, deliberadas o accidentales, que puedan comprometer su confidencialidad, integridad, disponibilidad, autenticidad o trazabilidad.

b) El cumplimiento de las obligaciones legales, reglamentarias y contractuales aplicables a la Entidad en materia de protección de la información, en particular las derivadas del Real Decreto 311/2022, del Reglamento (UE) 2016/679 del Parlamento Europeo y del Consejo, de 27 de abril de 2016, relativo a la protección de las personas físicas en lo que respecta al tratamiento de datos personales y a la libre circulación de estos datos (Reglamento General de Protección de Datos, en adelante "RGPD"), y de la Ley Orgánica 3/2018, de 5 de diciembre, de Protección de Datos Personales y garantía de los derechos digitales (en adelante "LOPDGDD"), entre otras normas aplicables.

c) Los riesgos a los que está expuesta la información se identifiquen, valoren, traten y supervisen de forma sistemática y continua.

d) Existan los recursos humanos, organizativos, técnicos y financieros suficientes para implantar y mantener las medidas de seguridad necesarias.

e) Toda persona, interna o externa, que acceda a los sistemas o a la información de la Entidad conozca sus obligaciones y responsabilidades en materia de seguridad y actúe en consecuencia.

## 3. ÁMBITO DE APLICACIÓN

### 3.1 Ámbito subjetivo

La presente Política es de obligado cumplimiento para:

a) Todo el personal de {{ cliente.razon_social }}, con independencia de su régimen jurídico de relación laboral o funcionarial, su categoría profesional, su antigüedad o su modalidad de contratación, incluyendo personal directivo, técnico, administrativo, becarios y personal en prácticas.

b) Las personas físicas o jurídicas que, en virtud de cualquier relación contractual, presten servicios a la Entidad o accedan a sus sistemas de información o a información por ella tratada, incluyendo proveedores, contratistas, subcontratistas y consultores externos.

c) Cualquier tercero que, de forma puntual o continuada, acceda a los recursos de información de la Entidad, debiendo en tal caso suscribir los compromisos de confidencialidad que correspondan.

### 3.2 Ámbito objetivo

Esta Política se aplica a la totalidad de los activos de información titularidad de la Entidad o sobre los que ejerza responsabilidad, incluyendo, con carácter no limitativo:

a) La información en cualquier formato (electrónico, impreso, audiovisual u otros) y en cualquier estado (en tránsito, en uso o almacenada).

b) Los sistemas de información que dan soporte a los servicios y procesos de la Entidad.

c) Las infraestructuras tecnológicas, redes, equipos, dispositivos, software y servicios cloud que componen el entorno tecnológico de la Entidad.

d) Las instalaciones físicas que albergan los activos anteriores.

e) El personal y los procesos vinculados a la operación, mantenimiento, supervisión y mejora de todo lo anterior.

### 3.3 Alcance específico para la conformidad con el ENS

A los efectos de la conformidad con el Real Decreto 311/2022, el alcance del Sistema de Gestión de la Seguridad de la Información comprende:

> **{{ proyecto.alcance.descripcion }}**

Los servicios incluidos en este alcance son: {{ proyecto.alcance.servicios_incluidos | join(", ") }}.

{% if proyecto.alcance.exclusiones %}
**Exclusiones expresas:** {{ proyecto.alcance.exclusiones }}
{% endif %}

La categoría de seguridad asignada al sistema, conforme al procedimiento descrito en el Anexo I del ENS y en la guía CCN-STIC 803, es **{{ proyecto.categoria_ens }}**.

## 4. MARCO NORMATIVO DE REFERENCIA

La presente Política se fundamenta y ha de interpretarse en el marco de las siguientes disposiciones, en su versión vigente en cada momento, así como en cuantas otras le resulten de aplicación:

### 4.1 Normativa nacional

a) Real Decreto 311/2022, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad.

b) Ley Orgánica 3/2018, de 5 de diciembre, de Protección de Datos Personales y garantía de los derechos digitales.

c) Ley 39/2015, de 1 de octubre, del Procedimiento Administrativo Común de las Administraciones Públicas.

d) Ley 40/2015, de 1 de octubre, de Régimen Jurídico del Sector Público.

e) Resolución de 13 de octubre de 2016, de la Secretaría de Estado de Administraciones Públicas, por la que se aprueba la Instrucción Técnica de Seguridad de conformidad con el Esquema Nacional de Seguridad (BOE-A-2016-10109).

f) Resolución de 13 de octubre de 2016, de la Secretaría de Estado de Administraciones Públicas, por la que se aprueba la Instrucción Técnica de Seguridad de Informe del Estado de la Seguridad (BOE-A-2016-10108).

g) Resolución de 27 de marzo de 2018, de la Secretaría de Estado de Función Pública, por la que se aprueba la Instrucción Técnica de Seguridad de Auditoría de la Seguridad de los Sistemas de Información (BOE-A-2018-4573).

h) Resolución de 13 de abril de 2018, de la Secretaría de Estado de Función Pública, por la que se aprueba la Instrucción Técnica de Seguridad de Notificación de Incidentes de Seguridad (BOE-A-2018-5370).

### 4.2 Normativa europea

a) Reglamento (UE) 2016/679 del Parlamento Europeo y del Consejo, de 27 de abril de 2016 (RGPD).

b) Directiva (UE) 2022/2555 del Parlamento Europeo y del Consejo, de 14 de diciembre de 2022, relativa a las medidas destinadas a garantizar un elevado nivel común de ciberseguridad en toda la Unión (NIS2).

c) Reglamento (UE) 910/2014 del Parlamento Europeo y del Consejo, de 23 de julio de 2014, relativo a la identificación electrónica y los servicios de confianza para las transacciones electrónicas en el mercado interior (eIDAS).

{% if cliente.sector_actividad in ["fintech", "servicios financieros", "banca", "seguros"] %}
d) Reglamento (UE) 2022/2554 del Parlamento Europeo y del Consejo, de 14 de diciembre de 2022, sobre la resiliencia operativa digital del sector financiero (DORA).
{% endif %}

### 4.3 Estándares y guías técnicas de referencia

a) Norma UNE-EN ISO/IEC 27001:2022 — Sistemas de Gestión de la Seguridad de la Información — Requisitos.

b) Norma UNE-EN ISO/IEC 27002:2022 — Controles de seguridad de la información.

c) Serie de guías CCN-STIC 800 emitidas por el Centro Criptológico Nacional, y en particular:

- CCN-STIC 800 — Glosario de términos y abreviaturas del ENS.
- CCN-STIC 802 — Guía de auditoría del ENS.
- CCN-STIC 803 — Valoración de los sistemas en el ENS.
- CCN-STIC 805 — Política de Seguridad de la Información.
- CCN-STIC 806 — Plan de Adecuación al ENS.
- CCN-STIC 808 — Verificación del cumplimiento del ENS.

d) Metodología MAGERIT versión 3 — Metodología de Análisis y Gestión de Riesgos de los Sistemas de Información, del Consejo Superior de Administración Electrónica.

## 5. PRINCIPIOS BÁSICOS DE LA SEGURIDAD DE LA INFORMACIÓN

De conformidad con el artículo 5 del ENS, la presente Política y el SGSI de la Entidad se rigen por los siguientes principios básicos:

**5.1. Seguridad como proceso integral.** La seguridad se entiende como un proceso continuo que abarca todos los elementos humanos, materiales, técnicos, jurídicos y organizativos relacionados con el sistema, y no como un estado puntual ni como una mera implementación tecnológica.

**5.2. Gestión de la seguridad basada en los riesgos.** El análisis y la gestión de los riesgos constituyen una parte esencial del proceso de seguridad. La Entidad mantendrá un proceso de análisis y gestión de riesgos continuo y proporcional a la naturaleza y categoría del sistema, conforme a la metodología MAGERIT.

**5.3. Prevención, detección, respuesta y conservación.** La Entidad implantará medidas que eviten razonablemente la materialización de las amenazas, detecten los incidentes con prontitud, permitan responder de forma eficaz y conserven la información necesaria para su análisis posterior.

**5.4. Existencia de líneas de defensa.** El sistema dispondrá de una estrategia de protección constituida por múltiples capas de seguridad, dispuestas de modo que, cuando una de ellas falle, otras permitan ganar tiempo para una reacción adecuada y reducir la probabilidad de que el sistema se vea comprometido en su conjunto.

**5.5. Vigilancia continua y reevaluación periódica.** La Entidad establecerá mecanismos de vigilancia continua que permitan detectar cualquier actividad anómala y reaccionar ante ella, así como mecanismos de reevaluación periódica que permitan adaptar la estrategia de seguridad a las nuevas circunstancias.

**5.6. Diferenciación de responsabilidades.** Las funciones y responsabilidades en materia de seguridad estarán claramente diferenciadas entre el responsable de la información, el responsable del servicio, el responsable de la seguridad y el responsable del sistema, conforme se establece en el documento {{ proyecto.codigo_documento_base }}-101 (Roles, Responsabilidades y Autoridades de Seguridad).

## 6. REQUISITOS MÍNIMOS DE SEGURIDAD

En cumplimiento de los requisitos mínimos establecidos en el artículo 12 y siguientes del ENS, la Entidad garantizará el cumplimiento, al menos, de los siguientes requisitos:

a) **Organización e implantación del proceso de seguridad**, mediante la formalización del Comité de Seguridad y la designación de los roles definidos en el documento {{ proyecto.codigo_documento_base }}-101.

b) **Análisis y gestión de los riesgos**, mediante la aplicación sistemática de la metodología MAGERIT v3 y la elaboración del correspondiente Análisis de Riesgos, que se revisará al menos con carácter anual y siempre que se produzcan cambios significativos en el sistema.

c) **Gestión de personal**, asegurando que todas las personas con acceso al sistema conozcan sus responsabilidades en materia de seguridad y reciban la formación y concienciación adecuadas.

d) **Profesionalidad**, garantizando que los responsables del sistema cuentan con la capacitación técnica y la experiencia necesarias.

e) **Autorización y control de los accesos**, conforme se desarrolla en el documento {{ proyecto.codigo_documento_base }}-102 (Política de Control de Acceso).

f) **Protección de las instalaciones**, mediante medidas físicas y ambientales proporcionales al riesgo identificado.

g) **Adquisición de productos y servicios de seguridad**, atendiendo, cuando proceda, a las disposiciones del Catálogo de Productos y Servicios de Seguridad de las Tecnologías de la Información y la Comunicación (CPSTIC) del Centro Criptológico Nacional.

h) **Mínimo privilegio**, otorgando a cada usuario únicamente los derechos de acceso estrictamente necesarios para el desempeño de sus funciones.

i) **Integridad y actualización del sistema**, manteniendo el inventario de activos actualizado y aplicando un proceso formal de gestión de cambios y de actualizaciones de seguridad.

j) **Protección de la información almacenada y en tránsito**, mediante el uso de mecanismos criptográficos adecuados al nivel de seguridad exigible.

k) **Prevención ante otros sistemas de información interconectados**, mediante el establecimiento de los controles de interconexión necesarios.

l) **Registro de la actividad y detección de código dañino**, garantizando la trazabilidad de las acciones y la protección frente a software malicioso.

m) **Incidentes de seguridad**, mediante la implantación del proceso descrito en el documento {{ proyecto.codigo_documento_base }}-103 (Política de Gestión de Incidentes de Seguridad).

n) **Continuidad de la actividad**, mediante el plan descrito en el documento {{ proyecto.codigo_documento_base }}-104 (Política de Continuidad del Servicio).

o) **Mejora continua del proceso de seguridad**, mediante el ciclo PDCA aplicado al SGSI y la revisión periódica de la presente Política.

## 7. ESTRUCTURA ORGANIZATIVA DE LA SEGURIDAD

### 7.1 Comité de Seguridad de la Información

La Entidad constituye un Comité de Seguridad de la Información, en adelante "el Comité", como órgano colegiado responsable del seguimiento, supervisión y coordinación del SGSI.

El Comité estará presidido por {{ responsables.comite_seguridad.presidente }}, y estará integrado por las siguientes personas o por quienes en cada momento ocupen los cargos indicados:

{% for miembro in responsables.comite_seguridad.miembros %}
- {{ miembro }}
{% endfor %}

Actuará como secretario del Comité {{ responsables.comite_seguridad.secretario }}, quien levantará acta de las sesiones celebradas. El Comité se reunirá con carácter ordinario {{ responsables.comite_seguridad.frecuencia_reuniones }} y, con carácter extraordinario, cuando sea convocado por su presidente o lo soliciten al menos dos de sus miembros.

Son funciones del Comité, entre otras:

a) Aprobar las directrices generales en materia de seguridad de la información y elevar al órgano superior las propuestas de modificación de la presente Política.

b) Coordinar la elaboración, revisión y actualización de la normativa interna de seguridad.

c) Revisar el resultado del análisis de riesgos y aprobar el plan de tratamiento.

d) Supervisar la implantación de las medidas de seguridad.

e) Analizar los incidentes de seguridad relevantes y velar por la adopción de medidas correctivas.

f) Conocer los resultados de las auditorías internas y externas y velar por la subsanación de las no conformidades detectadas.

g) Informar al órgano superior sobre el estado del SGSI con la periodicidad que se determine.

### 7.2 Roles operativos

La estructura operativa de la seguridad descansa sobre los cuatro roles previstos en el artículo 11 del ENS, cuyo nombramiento, funciones y responsabilidades se desarrollan en el documento {{ proyecto.codigo_documento_base }}-101.

| Rol | Persona designada | Cargo |
|---|---|---|
| Responsable de la Información | {{ responsables.responsable_informacion.nombre }} | {{ responsables.responsable_informacion.cargo }} |
| Responsable del Servicio | {{ responsables.responsable_servicio.nombre }} | {{ responsables.responsable_servicio.cargo }} |
| Responsable de la Seguridad | {{ responsables.responsable_seguridad.nombre }} | {{ responsables.responsable_seguridad.cargo }} |
| Responsable del Sistema | {{ responsables.responsable_sistema.nombre }} | {{ responsables.responsable_sistema.cargo }} |

## 8. GESTIÓN DE LOS DATOS PERSONALES

Cuando los sistemas de información de la Entidad traten datos de carácter personal, se aplicarán las medidas de seguridad correspondientes al RGPD y a la LOPDGDD, de modo coordinado con las medidas del presente SGSI, conforme a lo dispuesto en el artículo 3 del ENS y en el documento {{ proyecto.codigo_documento_base }}-115 (Política de Privacidad y Protección de Datos Personales).

La interlocución con la Agencia Española de Protección de Datos, así como las funciones propias del Delegado de Protección de Datos cuando este exista, corresponderán a {{ responsables.delegado_proteccion_datos.nombre }}, en su condición de {{ responsables.delegado_proteccion_datos.cargo }}.

## 9. GESTIÓN DE EXCEPCIONES

Excepcionalmente, y siempre por causa debidamente justificada, podrá autorizarse el incumplimiento temporal o parcial de alguno de los requisitos establecidos en la normativa interna de seguridad. Toda excepción habrá de:

a) Estar formalmente documentada y motivada.

b) Identificar el riesgo asumido y, en su caso, las medidas compensatorias adoptadas.

c) Ser autorizada por escrito por el Responsable de la Seguridad, previo informe favorable, cuando el riesgo asumido sea significativo, del Comité de Seguridad.

d) Tener una vigencia temporal definida, no superior a doce meses, susceptible de prórroga motivada.

e) Quedar registrada en el correspondiente Registro de Excepciones, gestionado por el Responsable de la Seguridad.

## 10. INCUMPLIMIENTO

El incumplimiento de la presente Política o de la normativa interna de seguridad que de ella se deriva podrá dar lugar a la apertura del correspondiente expediente disciplinario, conforme a lo previsto en la legislación laboral o administrativa aplicable y en el régimen disciplinario interno de la Entidad, sin perjuicio de las responsabilidades civiles, administrativas o penales en las que pudiera incurrirse.

En el caso de personal externo, el incumplimiento podrá dar lugar a la resolución del contrato y a la exigencia de las responsabilidades contractuales que correspondan.

## 11. COMUNICACIÓN, FORMACIÓN Y CONCIENCIACIÓN

La Entidad garantizará que la presente Política y la normativa interna de seguridad sean comunicadas, conocidas y comprendidas por todo el personal afectado por su ámbito de aplicación.

A tal efecto:

a) La Política será publicada en la intranet corporativa y, en su caso, en la sede electrónica de la Entidad.

b) Se notificará individualmente al personal de nueva incorporación durante el proceso de acogida, requiriéndose su acuse de recibo.

c) Se desarrollará un plan anual de formación y concienciación en seguridad de la información, dirigido a todo el personal según el rol que desempeñe.

d) Se realizarán acciones específicas de concienciación tras la notificación de incidentes relevantes o la actualización significativa de la normativa interna.

## 12. REVISIÓN Y ACTUALIZACIÓN

La presente Política será revisada con carácter ordinario al menos una vez al año, y con carácter extraordinario cuando concurra alguna de las siguientes circunstancias:

a) Modificaciones significativas en la normativa legal o reglamentaria aplicable.

b) Cambios sustanciales en la estructura organizativa, en los servicios prestados o en los sistemas de información de la Entidad.

c) Resultados del análisis de riesgos que evidencien la insuficiencia de los principios o requisitos establecidos.

d) Incidentes de seguridad de impacto significativo cuyo análisis aconseje su revisión.

e) Conclusiones de auditorías internas o externas que así lo recomienden.

Las modificaciones serán propuestas por el Responsable de la Seguridad, revisadas por el Comité de Seguridad y aprobadas por {{ cliente.organo_aprobador_politicas }}.

La próxima revisión ordinaria está prevista para el {{ proyecto.proxima_revision }}.

## 13. ENTRADA EN VIGOR

La presente Política entrará en vigor el día siguiente al de su aprobación por {{ cliente.organo_aprobador_politicas }}, esto es, el día siguiente al {{ proyecto.fecha_aprobacion_inicial }}, y permanecerá vigente hasta su derogación, modificación o sustitución por una versión posterior debidamente aprobada.

---

**Aprobado por {{ cliente.organo_aprobador_politicas }}** en sesión celebrada el {{ proyecto.fecha_aprobacion_inicial }}.

**Documento {{ proyecto.codigo_documento_base }}-100 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-101 — ROLES, RESPONSABILIDADES Y AUTORIDADES DE SEGURIDAD

**Es el documento que materializa el artículo 11 del ENS** (segregación de funciones de los cuatro roles obligatorios). Sin esto el SGSI ENS está cojo y el auditor lo detecta en los primeros 5 minutos.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-101"
titulo: "Roles, Responsabilidades y Autoridades de Seguridad"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# ROLES, RESPONSABILIDADES Y AUTORIDADES DE SEGURIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-101 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento desarrolla y concreta lo dispuesto en el apartado 7 de la Política de Seguridad de la Información ({{ proyecto.codigo_documento_base }}-100), estableciendo de forma detallada los roles, responsabilidades y autoridades en materia de seguridad de la información de {{ cliente.razon_social }}, así como los procedimientos para su designación, sustitución y rendición de cuentas.

Su objetivo es garantizar la separación de funciones exigida por el artículo 11 del Real Decreto 311/2022, asegurando que ninguna persona acumule responsabilidades incompatibles entre sí, especialmente en lo relativo a la operación del sistema, la decisión sobre los riesgos asumidos y la verificación independiente del cumplimiento.

## 2. ÁMBITO DE APLICACIÓN

El presente documento es de aplicación a todas las personas que desempeñen, con carácter formal o funcional, cualquiera de los roles de seguridad descritos, así como a quienes les apoyen o sustituyan en sus funciones.

## 3. PRINCIPIOS DE LA ESTRUCTURA DE ROLES

### 3.1 Diferenciación de responsabilidades

De conformidad con el artículo 11 del ENS, en los sistemas de información en el ámbito de aplicación del Esquema Nacional de Seguridad se diferenciará al **responsable de la información**, al **responsable del servicio**, al **responsable de la seguridad** y al **responsable del sistema**.

Estos cuatro roles son **incompatibles entre sí**, en el sentido de que ninguna persona podrá acumular simultáneamente más de uno de ellos, salvo en aquellos casos excepcionales en los que la dimensión y complejidad de la Entidad lo justifiquen y se hayan adoptado las medidas compensatorias necesarias para garantizar la objetividad de las decisiones.

{% if cliente.numero_empleados < 50 %}
**Nota sobre dimensión de la Entidad:** dado que {{ cliente.razon_social }} cuenta con {{ cliente.numero_empleados }} empleados, la separación estricta de los cuatro roles podría exigir la asunción excepcional de más de un rol por la misma persona. En tal caso se aplicará el régimen excepcional descrito en el apartado 4.6.
{% endif %}

### 3.2 Independencia del responsable de la seguridad

El Responsable de la Seguridad será **funcionalmente independiente** del Responsable del Sistema, evitando que el responsable de operar y mantener el sistema sea, a su vez, el encargado de verificar su seguridad. Esta independencia funcional es condición necesaria para la objetividad del SGSI.

### 3.3 Cadena de autoridad

La autoridad última en materia de seguridad de la información reside en {{ cliente.organo_aprobador_politicas }}, quien delega su ejercicio operativo en el Comité de Seguridad de la Información y, a través de él, en el Responsable de la Seguridad.

## 4. ROLES DE SEGURIDAD

### 4.1 Responsable de la Información

**4.1.1 Definición.** El Responsable de la Información es la persona que determina los requisitos de la información tratada, atendiendo a su sensibilidad, importancia y necesidades de protección.

**4.1.2 Designación.** A los efectos del SGSI, se designa como Responsable de la Información a {{ responsables.responsable_informacion.nombre }}, en su condición de {{ responsables.responsable_informacion.cargo }}, con dirección de correo electrónico {{ responsables.responsable_informacion.email }}.

**4.1.3 Funciones y responsabilidades.** Son funciones específicas del Responsable de la Información:

a) Establecer los requisitos de seguridad aplicables a la información, teniendo en cuenta su naturaleza, las obligaciones legales, las expectativas de las partes interesadas y los riesgos asociados.

b) Determinar y aprobar la valoración de la información en las dimensiones de confidencialidad, integridad, autenticidad y trazabilidad, conforme a los criterios del Anexo I del ENS y de la guía CCN-STIC 803.

c) Aprobar las normas y procedimientos relativos al ciclo de vida de la información (creación, clasificación, etiquetado, uso, conservación, transferencia, eliminación).

d) Autorizar los flujos de información hacia el exterior de la Entidad o hacia sistemas distintos de los originalmente autorizados.

e) Conocer y aceptar los riesgos residuales relativos a la información.

f) Recibir información periódica sobre los incidentes que afecten a la información de su responsabilidad.

### 4.2 Responsable del Servicio

**4.2.1 Definición.** El Responsable del Servicio es la persona que determina los requisitos de los servicios prestados por el sistema de información, en particular en cuanto a su disponibilidad y calidad de servicio.

**4.2.2 Designación.** Se designa como Responsable del Servicio a {{ responsables.responsable_servicio.nombre }}, en su condición de {{ responsables.responsable_servicio.cargo }}, con dirección de correo electrónico {{ responsables.responsable_servicio.email }}.

**4.2.3 Funciones y responsabilidades.**

a) Establecer los requisitos de seguridad aplicables a los servicios, atendiendo a su criticidad y a las expectativas de las partes interesadas.

b) Determinar y aprobar la valoración del servicio en la dimensión de disponibilidad, conforme a los criterios del Anexo I del ENS.

c) Definir los acuerdos de nivel de servicio (SLA) aplicables y velar por su cumplimiento.

d) Aprobar los planes de continuidad del servicio y los objetivos de tiempo y punto de recuperación (RTO/RPO).

e) Conocer y aceptar los riesgos residuales relativos a la disponibilidad del servicio.

f) Recibir información periódica sobre los incidentes que afecten a los servicios de su responsabilidad.

### 4.3 Responsable de la Seguridad

**4.3.1 Definición.** El Responsable de la Seguridad es la persona encargada de definir, mantener y supervisar la implantación del SGSI de la Entidad, así como de garantizar el cumplimiento de la normativa de seguridad de la información aplicable.

**4.3.2 Designación.** Se designa como Responsable de la Seguridad a {{ responsables.responsable_seguridad.nombre }}, en su condición de {{ responsables.responsable_seguridad.cargo }}, con dirección de correo electrónico {{ responsables.responsable_seguridad.email }}.

El Responsable de la Seguridad reporta directamente a {{ cliente.organo_aprobador_politicas }} y dispone de acceso directo al órgano de gobierno superior de la Entidad para todas aquellas cuestiones relacionadas con la seguridad de la información que requieran su atención.

**4.3.3 Funciones y responsabilidades.**

a) Elaborar y mantener actualizada la normativa interna de seguridad, así como proponer su aprobación al Comité de Seguridad.

b) Coordinar el análisis y la gestión de riesgos del sistema, conforme a la metodología MAGERIT v3.

c) Elaborar y mantener actualizada la Declaración de Aplicabilidad y el Plan de Adecuación al ENS.

d) Definir los requisitos de seguridad aplicables a los productos, servicios y proveedores que intervienen en el sistema.

e) Supervisar la implantación de las medidas de seguridad y verificar su eficacia.

f) Coordinar la respuesta ante los incidentes de seguridad y, en particular, ejercer las funciones de interlocución con el CCN-CERT a través de la herramienta LUCIA, cuando proceda conforme a la Instrucción Técnica de Seguridad de Notificación de Incidentes (BOE-A-2018-5370).

g) Promover y supervisar las actividades de formación y concienciación en seguridad.

h) Coordinar las auditorías internas de seguridad y supervisar la subsanación de las no conformidades detectadas en las auditorías externas.

i) Reportar al Comité de Seguridad y, a través de él, a {{ cliente.organo_aprobador_politicas }}, sobre el estado del SGSI con la periodicidad que se establezca, y en todo caso al menos una vez al año.

j) Mantener una posición funcionalmente independiente del Responsable del Sistema, evitando cualquier conflicto de interés en el ejercicio de sus funciones.

**4.3.4 Capacitación.** El Responsable de la Seguridad deberá acreditar formación específica en seguridad de la información y, deseablemente, certificaciones profesionales reconocidas internacionalmente (CISA, CISM, CISSP, ISO 27001 Lead Implementer, ISO 27001 Lead Auditor, o equivalentes).

### 4.4 Responsable del Sistema

**4.4.1 Definición.** El Responsable del Sistema es la persona encargada de la operación, mantenimiento y disponibilidad técnica del sistema de información, así como de la implantación de las medidas técnicas de seguridad bajo la supervisión del Responsable de la Seguridad.

**4.4.2 Designación.** Se designa como Responsable del Sistema a {{ responsables.responsable_sistema.nombre }}, en su condición de {{ responsables.responsable_sistema.cargo }}, con dirección de correo electrónico {{ responsables.responsable_sistema.email }}.

**4.4.3 Funciones y responsabilidades.**

a) Garantizar el correcto funcionamiento del sistema de información en condiciones de seguridad.

b) Implantar y operar las medidas de seguridad técnicas determinadas en el Plan de Adecuación y en la Declaración de Aplicabilidad.

c) Mantener actualizado el inventario de activos del sistema.

d) Aplicar las normas y procedimientos operativos de seguridad y supervisar su cumplimiento por el personal técnico bajo su responsabilidad.

e) Coordinar la gestión de cambios y de actualizaciones de seguridad del sistema.

f) Detectar y notificar al Responsable de la Seguridad los incidentes de seguridad de los que tenga conocimiento.

g) Facilitar al Responsable de la Seguridad y a los auditores internos y externos la información, evidencia y acceso al sistema necesarios para el ejercicio de sus funciones.

h) Proponer al Comité de Seguridad las mejoras técnicas que estime necesarias para reforzar la seguridad del sistema.

### 4.5 Delegado de Protección de Datos

Cuando la Entidad esté obligada a designar Delegado de Protección de Datos conforme al artículo 37 del RGPD, o cuando voluntariamente decida hacerlo, este rol corresponderá a {{ responsables.delegado_proteccion_datos.nombre }}, en su condición de {{ responsables.delegado_proteccion_datos.cargo }}, y se ejercerá con plena independencia funcional respecto del resto de roles, conforme a lo previsto en los artículos 38 y 39 del RGPD.

El Delegado de Protección de Datos colaborará estrechamente con el Responsable de la Seguridad en todos los asuntos que afecten al tratamiento de datos personales, sin perjuicio del carácter independiente de sus funciones.

### 4.6 Régimen excepcional de acumulación de roles

{% if cliente.numero_empleados < 50 %}
Atendiendo a la dimensión actual de la Entidad ({{ cliente.numero_empleados }} empleados), y siempre con carácter excepcional y temporal, podrá autorizarse que una misma persona acumule simultáneamente más de uno de los roles descritos, con las siguientes limitaciones absolutas:

a) **El Responsable de la Seguridad nunca podrá acumular el rol de Responsable del Sistema**, por exigencia expresa del artículo 11 del ENS y por la imposibilidad de auto-supervisarse.

b) La acumulación deberá ser autorizada formalmente por {{ cliente.organo_aprobador_politicas }}, previa propuesta motivada del Comité de Seguridad.

c) Se documentarán las medidas compensatorias adoptadas para mitigar el riesgo derivado de la acumulación, en particular el recurso a apoyo externo independiente para las funciones de auditoría.

d) La acumulación tendrá vigencia máxima de doce meses, transcurridos los cuales deberá revisarse y, en su caso, prorrogarse mediante nueva autorización expresa.

e) Toda acumulación quedará registrada en el Registro de Excepciones gestionado por el Responsable de la Seguridad.
{% else %}
Atendiendo a la dimensión actual de la Entidad ({{ cliente.numero_empleados }} empleados), no se considera necesaria la acumulación excepcional de roles. Cada uno de los cuatro roles del artículo 11 del ENS recae en una persona distinta, garantizando la separación de funciones exigida por la normativa.
{% endif %}

## 5. SUSTITUCIONES Y SUPLENCIAS

Para garantizar la continuidad operativa del SGSI en ausencia temporal o definitiva de las personas designadas, se establece el siguiente régimen de sustituciones:

a) En caso de **ausencia temporal** (vacaciones, baja por enfermedad, comisión de servicio) de cualquiera de las personas designadas, sus funciones serán asumidas por la persona suplente designada formalmente al efecto, que constará en el correspondiente acta del Comité de Seguridad.

b) En caso de **ausencia definitiva** (cese en el cargo, finalización de la relación laboral o contractual), {{ cliente.organo_aprobador_politicas }} procederá a la designación de la nueva persona titular en un plazo máximo de treinta días naturales. Hasta entonces, las funciones serán asumidas por el suplente designado.

c) Toda sustitución, temporal o definitiva, será comunicada al Comité de Seguridad y, en su caso, a las partes interesadas externas que corresponda.

## 6. RENDICIÓN DE CUENTAS

Cada uno de los roles descritos rendirá cuentas de sus actuaciones, según el siguiente esquema:

| Rol | Rinde cuentas a | Periodicidad |
|---|---|---|
| Responsable de la Seguridad | Comité de Seguridad y {{ cliente.organo_aprobador_politicas }} | Trimestral (Comité) y anual ({{ cliente.organo_aprobador_politicas }}) |
| Responsable del Sistema | Responsable de la Seguridad | Mensual |
| Responsable de la Información | Comité de Seguridad | Semestral |
| Responsable del Servicio | Comité de Seguridad | Semestral |
| Delegado de Protección de Datos | Órgano superior, conforme al art. 38 RGPD | Anual |

Los informes de rendición de cuentas se documentarán y conservarán en el repositorio documental del SGSI conforme al procedimiento {{ proyecto.codigo_documento_base }}-203 (Procedimiento de Gestión de la Información Documentada).

## 7. RESPONSABILIDADES TRAS EL CESE EN EL CARGO

Las personas que cesen en cualquiera de los roles descritos seguirán sujetas a las obligaciones de confidencialidad asumidas durante su ejercicio, conforme a lo previsto en el contrato laboral, en el código ético de la Entidad y en la legislación aplicable.

Asimismo, deberán colaborar de buena fe con su sucesor durante un período razonable de transición, facilitando el traspaso ordenado de las funciones, la documentación y los conocimientos necesarios.

## 8. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo.

---

**Documento {{ proyecto.codigo_documento_base }}-101 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-102 — POLÍTICA DE CONTROL DE ACCESO

**Materializa las medidas op.acc.1 a op.acc.6 del Anexo II del ENS** y los controles A.5.15-A.5.18, A.8.2, A.8.3 y A.8.5 de ISO 27001:2022. Es la política operativa más consultada en el día a día.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-102"
titulo: "Política de Control de Acceso"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE CONTROL DE ACCESO DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-102 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento establece los principios, criterios y reglas aplicables al control de acceso lógico y físico a los sistemas de información, redes, servicios, instalaciones y datos titularidad de {{ cliente.razon_social }}, con la finalidad de garantizar que únicamente las personas autorizadas, en el momento autorizado, mediante los medios autorizados y para los fines autorizados, accedan a los activos de información de la Entidad.

Esta Política desarrolla las medidas **op.acc.1 (Identificación)**, **op.acc.2 (Requisitos de acceso)**, **op.acc.3 (Segregación de funciones y tareas)**, **op.acc.4 (Proceso de gestión de derechos de acceso)**, **op.acc.5 (Mecanismos de autenticación – usuarios externos)** y **op.acc.6 (Mecanismos de autenticación – usuarios de la organización)** del Anexo II del Real Decreto 311/2022.

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a todo acceso, lógico o físico, a los sistemas, redes, servicios, instalaciones y datos comprendidos en el alcance del SGSI, conforme se define en el documento {{ proyecto.codigo_documento_base }}-100, sea dicho acceso solicitado por personal interno, por personal externo, por proveedores, por usuarios finales o por cualquier otra persona o sistema.

## 3. PRINCIPIOS RECTORES

### 3.1 Necesidad de saber y mínimo privilegio

Los accesos se concederán únicamente sobre la base del **principio de necesidad de saber** (*need to know*), conforme al cual cada persona accederá exclusivamente a la información estrictamente necesaria para el desempeño de las funciones que tenga encomendadas.

Adicionalmente, los privilegios concedidos serán los **mínimos imprescindibles** (*least privilege*) para el ejercicio de tales funciones, evitando la concesión de privilegios genéricos, agrupados o por defecto.

### 3.2 Identificación unívoca

Toda persona con acceso al sistema dispondrá de un **identificador único e inequívoco** que permita su identificación individual. Queda expresamente prohibido el uso de identificadores genéricos, compartidos o anónimos, salvo en aquellos casos excepcionales en los que su uso esté funcionalmente justificado, formalmente autorizado por el Responsable de la Seguridad y compensado mediante mecanismos adicionales de trazabilidad.

### 3.3 Autenticación

Toda solicitud de acceso al sistema requerirá la verificación previa de la identidad declarada por el solicitante, mediante mecanismos de autenticación cuya robustez será proporcional al nivel de seguridad exigido y al riesgo asociado.

### 3.4 Autorización

Una vez autenticado, el acceso del usuario al sistema y a los recursos concretos quedará condicionado a que disponga, en el momento del acceso, de la autorización formal correspondiente, gestionada conforme al apartado 6 del presente documento.

### 3.5 Registro y trazabilidad

Toda acción significativa relacionada con el acceso a los sistemas y a la información será objeto de registro, con el fin de permitir la atribución posterior de responsabilidades y el análisis forense en caso de incidente, conforme se desarrolla en el documento {{ proyecto.codigo_documento_base }}-118 (Política de Registro y Auditoría).

### 3.6 Segregación de funciones

Las funciones susceptibles de generar conflictos de interés o de permitir actuaciones fraudulentas no autorizadas estarán **segregadas entre personas distintas**, conforme se desarrolla en el apartado 7 del presente documento.

## 4. IDENTIFICACIÓN DE USUARIOS [op.acc.1]

### 4.1 Asignación del identificador

A cada persona usuaria del sistema se le asignará un identificador único, generado conforme a las reglas técnicas establecidas por el Responsable del Sistema y aprobadas por el Responsable de la Seguridad. El identificador acompañará a la persona durante toda su relación con la Entidad y quedará reservado para ella, no pudiendo ser reasignado a una persona distinta tras su baja.

### 4.2 Vinculación con la identidad real

Cada identificador estará vinculado, en el sistema corporativo de gestión de identidades, con la identidad real, completa y verificada de la persona física a quien se asigna, así como con el rol o roles que desempeña en la Entidad.

### 4.3 Periodo de retención

Los identificadores de personas que hayan cesado en su relación con la Entidad serán bloqueados o suprimidos en los plazos establecidos en el apartado 6.5, y en ningún caso podrán reutilizarse durante el periodo en que pudieran existir registros que los referencien.

## 5. AUTENTICACIÓN [op.acc.5 y op.acc.6]

### 5.1 Mecanismos admitidos

Los mecanismos de autenticación admitidos en los sistemas de la Entidad son los siguientes, en orden creciente de robustez:

a) **Algo que se sabe**: contraseña, código PIN.

b) **Algo que se tiene**: token físico, certificado digital instalado en dispositivo, código TOTP generado por aplicación móvil autorizada.

c) **Algo que se es**: huella dactilar, reconocimiento facial u otros mecanismos biométricos admitidos por la legislación aplicable.

### 5.2 Autenticación multifactor (MFA)

{% if proyecto.categoria_ens in ["MEDIA", "ALTA"] %}
Atendiendo a la categoría {{ proyecto.categoria_ens }} del sistema, será **obligatorio** el uso de autenticación multifactor (MFA), combinando al menos dos de los mecanismos descritos en el apartado 5.1, en los siguientes casos:

a) Acceso de usuarios privilegiados (administradores, operadores con privilegios elevados) a cualquier sistema del alcance.

b) Acceso a los sistemas desde redes externas a la red corporativa o desde ubicaciones no controladas por la Entidad.

c) Acceso a información clasificada de nivel **MEDIO** o **ALTO** en cualquiera de las dimensiones de seguridad.

d) Cualquier otro acceso que el Responsable de la Seguridad determine, atendiendo al riesgo asociado.
{% else %}
Atendiendo a la categoría BÁSICA del sistema, el uso de autenticación multifactor (MFA) será **recomendable** y, en todo caso, **obligatorio** para los accesos de administradores y para los accesos remotos desde redes externas a la red corporativa.
{% endif %}

### 5.3 Política de contraseñas

Cuando se utilicen contraseñas como factor de autenticación, estas deberán cumplir, como mínimo, los siguientes requisitos:

| Requisito | Categoría BÁSICA | Categoría MEDIA | Categoría ALTA |
|---|---|---|---|
| Longitud mínima | 8 caracteres | 12 caracteres | 14 caracteres |
| Composición | Letras + dígitos | Mayúsculas, minúsculas, dígitos y especiales | Mayúsculas, minúsculas, dígitos y especiales |
| Periodo máximo de validez | 12 meses | 6 meses | 3 meses |
| Historial (no reutilización) | Últimas 5 | Últimas 10 | Últimas 15 |
| Bloqueo tras intentos fallidos | 10 intentos | 5 intentos | 3 intentos |
| Almacenamiento | Hash con sal (SHA-256 mínimo) | Hash con sal y stretching (bcrypt/scrypt/argon2) | Hash con sal y stretching robusto (argon2id) |
| Comunicación | Solo cifrada (TLS 1.2 o superior) | Solo cifrada (TLS 1.3) | Solo cifrada (TLS 1.3 con cipher suite restringida) |

Estos requisitos se aplicarán automáticamente desde los sistemas de gestión de identidades y serán objeto de auditoría periódica por parte del Responsable de la Seguridad.

### 5.4 Custodia y protección de las credenciales

Toda persona usuaria es responsable de la custodia y protección de las credenciales de autenticación que le hayan sido asignadas, debiendo:

a) No comunicarlas a ninguna otra persona, ni siquiera al personal técnico de soporte.

b) No anotarlas en soportes que pudieran ser accesibles a terceros.

c) No reutilizar las credenciales corporativas en sistemas o servicios ajenos a la Entidad.

d) Notificar de inmediato al Responsable de la Seguridad cualquier sospecha de compromiso de las mismas.

### 5.5 Acceso de usuarios externos

El acceso de usuarios externos (proveedores, clientes, ciudadanos) a los sistemas de la Entidad se realizará mediante mecanismos de autenticación que ofrezcan garantías equivalentes a las exigidas a los usuarios internos para el mismo tipo de información o servicio, conforme a lo previsto en el Reglamento (UE) 910/2014 (eIDAS) y, cuando proceda, mediante el uso de certificados digitales reconocidos.

## 6. GESTIÓN DEL CICLO DE VIDA DE LOS DERECHOS DE ACCESO [op.acc.4]

### 6.1 Solicitud de acceso

Toda solicitud de acceso al sistema se formulará por escrito, mediante el procedimiento {{ proyecto.codigo_documento_base }}-205 (Procedimiento de Gestión de Cuentas y Accesos), e incluirá, al menos:

a) Identificación del solicitante.

b) Identificación del responsable jerárquico que avala la solicitud.

c) Descripción del rol o funciones a desempeñar.

d) Recursos a los que se solicita acceso y nivel de privilegio requerido.

e) Periodo previsto de vigencia de los accesos solicitados.

### 6.2 Autorización

La autorización corresponderá al **propietario del recurso** (el Responsable de la Información o el Responsable del Servicio, según proceda), quien valorará si los accesos solicitados son proporcionados al rol declarado y si respetan los principios de necesidad de saber y mínimo privilegio.

Toda autorización quedará formalmente documentada y será trazable en el sistema de gestión de identidades.

### 6.3 Provisión

Una vez autorizada, la provisión técnica de los accesos será realizada por el Responsable del Sistema o por el personal técnico bajo su supervisión, en el plazo máximo de cinco días hábiles desde la autorización.

### 6.4 Revisión periódica

Los derechos de acceso vigentes serán objeto de revisión periódica con la siguiente cadencia:

| Tipo de acceso | Frecuencia mínima de revisión |
|---|---|
| Accesos de usuarios privilegiados (administradores) | Trimestral |
| Accesos a información clasificada como nivel ALTO | Trimestral |
| Accesos a información clasificada como nivel MEDIO | Semestral |
| Accesos generales de usuarios | Anual |

La revisión será coordinada por el Responsable de la Seguridad, ejecutada por los propietarios de los recursos y sus resultados quedarán documentados y elevados al Comité de Seguridad.

### 6.5 Modificación y revocación

Todo cambio en las funciones de la persona usuaria (cambio de puesto, cambio de proyecto, asunción temporal de nuevas responsabilidades) dará lugar a la revisión inmediata de sus accesos y a su modificación cuando proceda, conforme al principio de mínimo privilegio.

En caso de **cese definitivo** de la relación laboral o contractual, los accesos serán revocados en los siguientes plazos máximos desde la efectividad del cese:

| Tipo de acceso | Plazo máximo de revocación |
|---|---|
| Accesos privilegiados (administradores) | 1 hora |
| Accesos a información clasificada como nivel ALTO | 4 horas |
| Accesos a información clasificada como nivel MEDIO | 24 horas |
| Accesos generales | 72 horas |

En el supuesto de **despido disciplinario o cese conflictivo**, la revocación será inmediata y previa o simultánea a la comunicación formal del cese a la persona afectada.

## 7. SEGREGACIÓN DE FUNCIONES [op.acc.3]

### 7.1 Funciones incompatibles

Se consideran funciones cuya acumulación por una misma persona genera conflicto de interés y queda, en consecuencia, prohibida sin autorización expresa y compensación documental, las siguientes:

a) Desarrollo de software y autorización de su despliegue en producción.

b) Operación del sistema y auditoría independiente del mismo.

c) Aprobación de gastos y registro contable de los mismos.

d) Solicitud de altas de usuario y autorización de las mismas.

e) Acceso a entornos productivos y modificación de los registros de auditoría sobre dichos entornos.

f) Cualquier otra combinación que el Comité de Seguridad determine en función del análisis de riesgos.

### 7.2 Mecanismos de control

La segregación de funciones se garantizará mediante:

a) Asignación clara y documentada de roles en el organigrama y en el sistema de gestión de identidades.

b) Configuración técnica de los sistemas de modo que las combinaciones prohibidas no sean técnicamente posibles.

c) Auditoría periódica del cumplimiento de la segregación, integrada en el ciclo de revisión de accesos del apartado 6.4.

d) En aquellos casos en que la dimensión de la Entidad impida una segregación estricta, adopción de **medidas compensatorias** documentadas (revisión por una segunda persona, supervisión continua, doble registro, etc.) y autorización expresa del Responsable de la Seguridad.

## 8. CONTROL DE ACCESO FÍSICO

El acceso físico a las instalaciones que albergan elementos del sistema se regulará por el principio de mínimo privilegio, conforme a las medidas mp.if.1 a mp.if.7 del Anexo II del ENS y al desarrollo específico del documento {{ proyecto.codigo_documento_base }}-110 (Política de Seguridad Física y Ambiental).

## 9. ACCESO REMOTO

El acceso remoto a los sistemas desde redes no controladas por la Entidad estará condicionado a:

a) Autorización expresa del Responsable de la Seguridad.

b) Uso obligatorio de canal cifrado (VPN corporativa o equivalente, con TLS 1.2 o superior).

c) Uso obligatorio de autenticación multifactor.

d) Registro completo de la sesión y posibilidad de terminación remota inmediata.

e) Cumplimiento de la política de uso de equipos personales (BYOD), cuando proceda, conforme al documento {{ proyecto.codigo_documento_base }}-117.

## 10. INCUMPLIMIENTO

El incumplimiento de la presente Política, incluyendo el intento de acceso no autorizado, la cesión de credenciales, la elusión de mecanismos de autenticación o la extracción de información a la que no se tiene derecho, podrá dar lugar a la apertura del correspondiente expediente disciplinario y, en su caso, a las responsabilidades civiles, administrativas o penales que correspondan, conforme a lo previsto en el apartado 10 del documento {{ proyecto.codigo_documento_base }}-100.

## 11. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo.

---

**Documento {{ proyecto.codigo_documento_base }}-102 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-103 — POLÍTICA DE GESTIÓN DE INCIDENTES DE SEGURIDAD

**Materializa la medida op.exp.7 del Anexo II del ENS** y cumple las obligaciones de notificación al CCN-CERT vía LUCIA (Resolución BOE-A-2018-5370) + las obligaciones de notificación de brechas a la AEPD del artículo 33 del RGPD (72 horas).

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-103"
titulo: "Política de Gestión de Incidentes de Seguridad de la Información"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE GESTIÓN DE INCIDENTES DE SEGURIDAD DE LA INFORMACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-103 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento establece el marco general para la **detección, notificación, valoración, contención, erradicación, recuperación y aprendizaje** ante los incidentes de seguridad que afecten o puedan afectar a los sistemas de información, redes, servicios, instalaciones e información de {{ cliente.razon_social }}, así como las obligaciones de notificación a las autoridades competentes y a las partes interesadas afectadas.

Esta Política da cumplimiento a la medida **op.exp.7 (Gestión de incidentes)** del Anexo II del Real Decreto 311/2022, a la **Instrucción Técnica de Seguridad de Notificación de Incidentes de Seguridad** (Resolución de 13 de abril de 2018, BOE-A-2018-5370) y, en lo que respecta a las brechas de seguridad de datos personales, a los **artículos 33 y 34 del Reglamento (UE) 2016/679** (RGPD) y a la **Guía para la notificación de brechas de datos personales** publicada por la Agencia Española de Protección de Datos.

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a todo incidente, real o sospechado, que pueda afectar a la confidencialidad, integridad, disponibilidad, autenticidad o trazabilidad de la información o de los servicios prestados por los sistemas comprendidos en el alcance del SGSI, con independencia del origen del incidente (interno o externo, deliberado o accidental, técnico o procedimental).

Es de obligado cumplimiento para todo el personal de la Entidad y para los terceros con acceso a sus sistemas, incluidos proveedores y subcontratistas.

## 3. DEFINICIONES OPERATIVAS

A los efectos del presente documento, se entenderá por:

a) **Evento de seguridad**: cualquier ocurrencia identificada en un sistema, servicio o red que indica una posible violación de la política de seguridad o un fallo en los controles, así como cualquier situación previamente desconocida que pueda ser relevante para la seguridad.

b) **Incidente de seguridad**: uno o varios eventos de seguridad relacionados, no deseados o inesperados, que tienen una probabilidad significativa de comprometer la operación de los sistemas o de la información y de amenazar la seguridad de la información.

c) **Brecha de seguridad de datos personales**: toda violación de la seguridad que ocasione la destrucción, pérdida o alteración accidental o ilícita de datos personales transmitidos, conservados o tratados de otra forma, o la comunicación o acceso no autorizados a dichos datos, conforme al artículo 4.12 del RGPD.

d) **Crisis de seguridad**: incidente de impacto crítico que requiere la activación del comité de crisis y, eventualmente, del Plan de Continuidad del Servicio.

## 4. CLASIFICACIÓN DE INCIDENTES

Los incidentes de seguridad se clasificarán, a efectos de su gestión y notificación, conforme a la siguiente escala, alineada con la guía CCN-CERT IA-04/19 sobre tipología de incidentes:

| Nivel | Categoría | Criterio | Plazo máximo de notificación interna |
|---|---|---|---|
| **5 — CRÍTICO** | Crisis | Compromiso total del sistema, exfiltración masiva, indisponibilidad prolongada de servicios esenciales | Inmediato (15 minutos) |
| **4 — MUY ALTO** | Alto impacto | Compromiso significativo, afectación a servicios esenciales, brecha de datos personales con riesgo alto | 1 hora |
| **3 — ALTO** | Impacto relevante | Compromiso parcial, afectación a servicios no esenciales, brecha de datos personales con riesgo bajo | 4 horas |
| **2 — MEDIO** | Impacto moderado | Detección de actividad anómala con afectación limitada | 24 horas |
| **1 — BAJO** | Impacto menor | Eventos aislados sin afectación significativa | 72 horas |

La clasificación inicial será realizada por la persona que detecte el incidente y revisada inmediatamente por el Responsable de la Seguridad, quien podrá reclasificarlo en función de la información disponible.

## 5. CICLO DE GESTIÓN DEL INCIDENTE

La gestión de cualquier incidente seguirá las siguientes fases, conforme al modelo NIST SP 800-61 adaptado al contexto del ENS:

### 5.1 Detección

Los incidentes pueden ser detectados por:

a) Sistemas automáticos de monitorización (SIEM, IDS/IPS, antimalware, herramientas DLP) operados conforme al documento {{ proyecto.codigo_documento_base }}-118.

b) Personal interno o externo que observe una anomalía o sospeche de un compromiso.

c) Notificaciones recibidas de terceros (CCN-CERT, INCIBE-CERT, partes interesadas, proveedores).

d) Auditorías internas o externas.

Toda persona, sea del personal interno o externo, que detecte un evento o incidente de seguridad **tiene la obligación** de notificarlo de inmediato al Responsable de la Seguridad o, en su defecto, al Responsable del Sistema, mediante los canales establecidos en el procedimiento {{ proyecto.codigo_documento_base }}-204 (Procedimiento de Gestión de Incidentes).

### 5.2 Notificación interna y registro

Recibida la notificación, el Responsable de la Seguridad procederá inmediatamente a:

a) Registrar el incidente en el **Registro de Incidentes** del SGSI, asignándole un identificador único, fecha y hora exactas, persona notificadora y descripción inicial.

b) Realizar la clasificación preliminar conforme al apartado 4.

c) Activar el equipo de respuesta correspondiente al nivel del incidente.

### 5.3 Análisis y valoración

El equipo de respuesta procederá a:

a) Recopilar toda la información disponible sobre el incidente, preservando la cadena de custodia de las evidencias conforme al procedimiento {{ proyecto.codigo_documento_base }}-228 (Recopilación y Custodia de Evidencias).

b) Determinar el alcance, naturaleza y causa probable del incidente.

c) Valorar el impacto real o potencial sobre la confidencialidad, integridad, disponibilidad, autenticidad y trazabilidad de la información y los servicios.

d) Determinar si el incidente afecta a datos personales y, en su caso, valorar el riesgo conforme a los criterios de la guía AEPD para la notificación de brechas de datos personales.

e) Confirmar o reclasificar el nivel del incidente.

### 5.4 Contención

El equipo de respuesta adoptará las medidas necesarias para contener el incidente, evitando su propagación y limitando su impacto. Estas medidas podrán incluir, entre otras, el aislamiento de sistemas afectados, la suspensión de cuentas de usuario, el bloqueo de comunicaciones o la activación de copias de respaldo.

Las medidas de contención serán aprobadas por el Responsable de la Seguridad y ejecutadas por el Responsable del Sistema o por el personal técnico bajo su supervisión.

### 5.5 Erradicación

Una vez contenido el incidente, se procederá a eliminar la causa raíz del mismo, lo que podrá incluir la limpieza de sistemas comprometidos, la aplicación de parches, la eliminación de cuentas no autorizadas, la reconfiguración de controles de seguridad o cualquier otra medida correctiva necesaria.

### 5.6 Recuperación

Eliminada la causa raíz, se procederá a la restauración del servicio en condiciones de seguridad, mediante el procedimiento adecuado a cada caso y, cuando proceda, mediante la activación de los planes de continuidad descritos en el documento {{ proyecto.codigo_documento_base }}-104.

La recuperación se considerará completada cuando los sistemas afectados operen con normalidad y se haya verificado la ausencia de actividad anómala residual.

### 5.7 Aprendizaje (lecciones aprendidas)

Tras el cierre del incidente, y en un plazo máximo de quince días naturales para incidentes de niveles 3 a 5, el Responsable de la Seguridad elaborará un **informe post-incidente** que incluirá, al menos:

a) Cronología detallada del incidente.

b) Causa raíz identificada.

c) Impacto real producido.

d) Eficacia de las medidas de contención, erradicación y recuperación adoptadas.

e) Lecciones aprendidas y recomendaciones de mejora para los controles, los procedimientos o la formación.

f) Acciones correctivas a implantar, con responsables y plazos.

El informe post-incidente será elevado al Comité de Seguridad y, en función de su gravedad, a {{ cliente.organo_aprobador_politicas }}.

## 6. NOTIFICACIÓN A AUTORIDADES Y PARTES INTERESADAS

### 6.1 Notificación al CCN-CERT vía LUCIA

{% if cliente.es_sector_publico or proyecto.categoria_ens in ["MEDIA", "ALTA"] %}
Conforme a la Instrucción Técnica de Seguridad de Notificación de Incidentes de Seguridad (BOE-A-2018-5370), los incidentes de niveles **CRÍTICO** y **MUY ALTO**, y en general aquellos que afecten significativamente a los servicios esenciales o a la información clasificada, serán notificados al CCN-CERT mediante la herramienta **LUCIA**, en los siguientes plazos máximos:

| Nivel del incidente | Plazo de notificación inicial al CCN-CERT |
|---|---|
| CRÍTICO | 1 hora desde la detección |
| MUY ALTO | 6 horas desde la detección |
| ALTO | 24 horas desde la detección |

La notificación inicial se complementará con notificaciones de seguimiento durante la gestión del incidente y con el informe final de cierre.

La interlocución con el CCN-CERT corresponde al Responsable de la Seguridad o a la persona en quien delegue formalmente.
{% else %}
Atendiendo a la naturaleza privada de la Entidad y a la categoría {{ proyecto.categoria_ens }} del sistema, la notificación al CCN-CERT vía LUCIA tendrá carácter **voluntario** salvo en aquellos casos en que el incidente afecte a un servicio prestado a la Administración Pública, en cuyo caso se notificará en los plazos establecidos en el apartado anterior.
{% endif %}

### 6.2 Notificación de brechas a la AEPD

Cuando el incidente constituya una brecha de seguridad de datos personales, conforme a la definición del artículo 4.12 del RGPD, y exista probabilidad de riesgo para los derechos y libertades de las personas físicas, la Entidad procederá a su notificación a la Agencia Española de Protección de Datos en el plazo máximo de **72 horas desde su conocimiento**, conforme al artículo 33 del RGPD.

La notificación se realizará a través del **formulario electrónico de la sede electrónica de la AEPD** disponible en https://sedeaepd.gob.es y contendrá, al menos:

a) Naturaleza de la brecha y, cuando sea posible, las categorías y el número aproximado de personas afectadas y de registros de datos personales afectados.

b) Datos de contacto del Delegado de Protección de Datos o del punto de contacto donde pueda obtenerse más información.

c) Posibles consecuencias de la brecha.

d) Medidas adoptadas o propuestas para poner remedio a la brecha y, en su caso, mitigar sus posibles efectos.

Cuando la brecha entrañe **riesgo alto** para los derechos y libertades de las personas físicas, se procederá adicionalmente a la **comunicación a las personas afectadas** sin dilación indebida, conforme al artículo 34 del RGPD.

La interlocución con la AEPD corresponde al Delegado de Protección de Datos en coordinación con el Responsable de la Seguridad.

{% if cliente.sector_actividad in ["fintech", "servicios financieros", "banca", "seguros"] %}
### 6.3 Notificación bajo DORA

Adicionalmente, conforme al Reglamento (UE) 2022/2554 (DORA), los incidentes graves relacionados con las TIC serán notificados a la autoridad competente en los plazos y con el contenido establecidos en dicho Reglamento y en sus actos delegados.
{% endif %}

### 6.4 Notificación a partes interesadas afectadas

Cuando el incidente afecte a clientes, proveedores o terceros que mantengan relaciones contractuales con la Entidad, se les notificará conforme a las obligaciones contractuales o legales aplicables, en los plazos y por los canales establecidos.

## 7. EQUIPO DE RESPUESTA A INCIDENTES

La Entidad constituye un **Equipo de Respuesta a Incidentes** (en adelante, "ERI"), cuya composición y funciones serán las siguientes:

| Rol en el ERI | Persona designada | Responsabilidades |
|---|---|---|
| Coordinador del ERI | {{ responsables.responsable_seguridad.nombre }} | Coordinación general, interlocución con autoridades |
| Analista técnico líder | {{ responsables.responsable_sistema.nombre }} | Análisis técnico, contención y erradicación |
| Asesor legal | _A designar_ | Asesoramiento jurídico, valoración de obligaciones de notificación |
| Comunicación | _A designar_ | Comunicación interna y externa, gestión reputacional |
| Delegado de Protección de Datos | {{ responsables.delegado_proteccion_datos.nombre }} | Asesoramiento sobre brechas de datos personales y notificación a la AEPD |

Para incidentes de nivel **CRÍTICO**, el ERI activará el **Comité de Crisis**, presidido por {{ responsables.comite_seguridad.presidente }} y, en su defecto, por la persona en quien delegue {{ cliente.organo_aprobador_politicas }}.

## 8. EJERCICIOS Y SIMULACROS

Con periodicidad al menos **anual**, la Entidad realizará ejercicios y simulacros de gestión de incidentes que permitan evaluar la eficacia del proceso descrito en el presente documento, identificar áreas de mejora y mantener entrenado al ERI.

Los resultados de los ejercicios serán documentados y elevados al Comité de Seguridad.

## 9. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo, y en todo caso tras cualquier incidente de nivel CRÍTICO o MUY ALTO.

---

**Documento {{ proyecto.codigo_documento_base }}-103 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-104 — POLÍTICA DE CONTINUIDAD DEL SERVICIO

**Materializa las medidas op.cont.1 a op.cont.4 del Anexo II del ENS** y los controles A.5.29, A.5.30 y A.8.14 de ISO 27001:2022. Es la política que el auditor ENAC pide siempre demostrada con un test real de restore.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-104"
titulo: "Política de Continuidad del Servicio"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE CONTINUIDAD DEL SERVICIO DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-104 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento establece los principios, criterios y compromisos de {{ cliente.razon_social }} en materia de continuidad de los servicios y recuperación ante desastres, con la finalidad de garantizar que, ante una disrupción significativa, los servicios esenciales puedan mantenerse o restaurarse en niveles aceptables y dentro de los plazos comprometidos con las partes interesadas.

Esta Política da cumplimiento a las medidas **op.cont.1 (Análisis de impacto)**, **op.cont.2 (Plan de continuidad)**, **op.cont.3 (Pruebas periódicas)** y **op.cont.4 (Medios alternativos)** del Anexo II del Real Decreto 311/2022, así como, supletoriamente, a las directrices de la norma UNE-EN ISO 22301:2019 sobre Sistemas de Gestión de la Continuidad del Negocio.

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a la totalidad de los servicios y sistemas comprendidos en el alcance del SGSI, conforme se define en el documento {{ proyecto.codigo_documento_base }}-100, y a todos los procesos, recursos humanos, infraestructuras, terceros y elementos de cualquier naturaleza que sean necesarios para la prestación de dichos servicios.

## 3. PRINCIPIOS DE CONTINUIDAD

### 3.1 Proporcionalidad

Las medidas de continuidad serán proporcionales a la criticidad de los servicios, valorada conforme a los criterios del Anexo I del ENS y al análisis de impacto en el negocio.

### 3.2 Anticipación

La Entidad actuará anticipándose a los escenarios de disrupción razonablemente previsibles, mediante la identificación temprana de amenazas, la evaluación de su impacto potencial y la planificación de las respuestas.

### 3.3 Recuperación priorizada

En caso de disrupción, la recuperación de los servicios se realizará atendiendo a su criticidad, comenzando por los servicios esenciales y continuando por los menos críticos hasta restablecer la operación normal.

### 3.4 Mejora continua

Los planes de continuidad serán objeto de revisión, prueba y mejora continua, integrándose en el ciclo PDCA del SGSI.

## 4. ANÁLISIS DE IMPACTO EN EL NEGOCIO [op.cont.1]

### 4.1 Realización del análisis

La Entidad realizará y mantendrá actualizado un **Análisis de Impacto en el Negocio** (en adelante, "BIA", del inglés *Business Impact Analysis*) que identifique:

a) Los procesos y servicios críticos para el cumplimiento de la misión de la Entidad.

b) Los recursos humanos, tecnológicos, físicos y de información necesarios para su prestación.

c) El impacto que produciría su interrupción a lo largo del tiempo, expresado en términos operativos, económicos, reputacionales, legales y sobre las partes interesadas.

d) Los **objetivos de tiempo de recuperación** (RTO – *Recovery Time Objective*) máximos admisibles para cada servicio crítico.

e) Los **objetivos de punto de recuperación** (RPO – *Recovery Point Objective*) máximos admisibles para los datos asociados a cada servicio crítico.

f) Las dependencias internas y externas (proveedores, terceros, infraestructuras compartidas).

### 4.2 Periodicidad

El BIA será revisado al menos con carácter **anual** y, con carácter extraordinario, cuando se produzcan cambios significativos en los servicios prestados, en la organización, en la infraestructura o en el contexto operativo de la Entidad.

### 4.3 Aprobación

El BIA será elaborado por el Responsable de la Seguridad en coordinación con los Responsables del Servicio y de la Información, y aprobado por el Comité de Seguridad.

## 5. PLAN DE CONTINUIDAD DEL SERVICIO [op.cont.2]

### 5.1 Elaboración

A partir de los resultados del BIA, la Entidad elaborará y mantendrá actualizado un **Plan de Continuidad del Servicio** (en adelante, "PCS"), que documentará:

a) La estrategia general de continuidad adoptada para cada servicio crítico.

b) Los procedimientos operativos para la activación, gestión y desactivación del Plan.

c) Los roles y responsabilidades del Equipo de Continuidad.

d) Los recursos alternativos previstos (instalaciones, equipos, conectividad, personal, proveedores).

e) Las comunicaciones internas y externas durante una situación de disrupción.

f) Los criterios y procedimientos para la vuelta a la normalidad.

### 5.2 Plan de Recuperación ante Desastres

El PCS se complementará con un **Plan de Recuperación ante Desastres** (DRP, *Disaster Recovery Plan*), que detallará los procedimientos técnicos específicos para la restauración de los sistemas e infraestructuras tecnológicas tras una disrupción.

### 5.3 Aprobación

El PCS y el DRP serán aprobados por el Comité de Seguridad y elevados a {{ cliente.organo_aprobador_politicas }} para su conocimiento.

## 6. MEDIOS ALTERNATIVOS [op.cont.4]

### 6.1 Redundancia

Para los servicios cuya criticidad lo justifique, la Entidad mantendrá medios alternativos que permitan su prestación en caso de fallo del entorno principal. Estos medios podrán incluir:

a) **Redundancia de hardware**: servidores, sistemas de almacenamiento y elementos de red duplicados o en alta disponibilidad.

b) **Redundancia de comunicaciones**: enlaces de red alternativos con proveedores diferentes.

c) **Redundancia de instalaciones**: centros de proceso de datos alternativos, ubicados a distancia geográfica suficiente del principal.

d) **Redundancia de proveedores**: existencia de proveedores alternativos para servicios externalizados críticos.

e) **Copias de seguridad** (backups) almacenadas en ubicaciones independientes y protegidas, con políticas de retención y rotación adecuadas.

### 6.2 Política de copias de seguridad

Las copias de seguridad de la información y los sistemas se realizarán conforme a los siguientes criterios mínimos:

| Categoría ENS del sistema | Frecuencia mínima de respaldo | Retención mínima | Pruebas de restauración |
|---|---|---|---|
| BÁSICA | Semanal | 1 mes | Anual |
| MEDIA | Diaria | 3 meses | Semestral |
| ALTA | Diaria + incrementos | 6 meses | Trimestral |

Las copias se almacenarán cifradas, en ubicación física separada de los sistemas de origen, y serán objeto de pruebas periódicas de restauración para verificar su integridad y operatividad.

## 7. PRUEBAS PERIÓDICAS [op.cont.3]

### 7.1 Programa de pruebas

La Entidad mantendrá un programa anual de pruebas del PCS y del DRP que incluya, al menos, los siguientes tipos de ejercicio:

a) **Revisión documental**: revisión periódica de los planes y procedimientos para verificar su vigencia y consistencia.

b) **Walkthrough**: ejercicio teórico en mesa con los miembros del Equipo de Continuidad para revisar paso a paso la respuesta a un escenario simulado.

c) **Prueba parcial técnica**: ejercicio práctico de restauración de un componente o servicio concreto, sin afectar a la operación.

d) **Prueba completa**: ejercicio práctico de activación de los medios alternativos y restauración íntegra del servicio en el entorno alternativo.

### 7.2 Periodicidad mínima

| Tipo de prueba | Categoría BÁSICA | Categoría MEDIA | Categoría ALTA |
|---|---|---|---|
| Revisión documental | Anual | Semestral | Semestral |
| Walkthrough | Anual | Anual | Semestral |
| Prueba parcial técnica | Bienal | Anual | Semestral |
| Prueba completa | Bienal | Bienal | Anual |

### 7.3 Documentación de las pruebas

De cada prueba se elaborará un informe que recoja los objetivos, el escenario, los participantes, las acciones realizadas, los tiempos medidos, los problemas detectados y las acciones correctivas a emprender. Los informes serán elevados al Comité de Seguridad.

## 8. EQUIPO DE CONTINUIDAD

La Entidad constituye un **Equipo de Continuidad** cuya composición incluirá, al menos, al Responsable de la Seguridad, al Responsable del Sistema, al Responsable del Servicio y a una persona con capacidad de decisión sobre los recursos económicos necesarios.

En situaciones de **crisis** (incidentes de nivel CRÍTICO conforme al documento {{ proyecto.codigo_documento_base }}-103), el Equipo de Continuidad se integrará en el Comité de Crisis, asumiendo la coordinación operativa de la respuesta.

## 9. CONTINUIDAD DE PROVEEDORES CRÍTICOS

La Entidad identificará a los proveedores cuyos servicios resulten críticos para la prestación de sus propios servicios e incluirá en los contratos con estos proveedores:

a) Compromisos sobre continuidad del servicio y recuperación ante desastres.

b) Obligación de notificación inmediata de cualquier disrupción que pueda afectar a la Entidad.

c) Derecho de auditoría sobre las medidas de continuidad del proveedor.

d) Acuerdos de nivel de servicio (SLA) consistentes con los RTO y RPO de la Entidad.

## 10. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo, y en todo caso tras cualquier prueba completa del Plan que evidencie deficiencias significativas.

---

**Documento {{ proyecto.codigo_documento_base }}-104 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

## INSTRUCCIONES PARA CLAUDE CODE

### Conversión a `.docx` con `docxtpl`

Cada uno de los 5 bloques anteriores delimitado por triple backtick `jinja` debe convertirse a un fichero `.docx` separado mediante el siguiente flujo:

1. **Crear plantilla base** `templates/policy_base.docx` en LibreOffice/Word con:
   - Cabecera con logo FULKRO + datos del cliente
   - Pie con número de página, código documento y clasificación
   - Tipografía Inter (cuerpo) + Fraunces (titulares H1)
   - Estilos de párrafo predefinidos: H1, H2, H3, Body, Tabla
   - Marcado de campos editables con `{{ }}` Jinja2

2. **Por cada política** (E-100 a E-104):
   - Copiar la plantilla base
   - Insertar el contenido del bloque jinja correspondiente
   - Guardar como `templates/{codigo}.docx` (ej: `templates/POL-100.docx`)

3. **Generar el documento final** del cliente con:
```python
from docxtpl import DocxTemplate

doc = DocxTemplate("templates/POL-100.docx")
context = {
    "cliente": cliente_data,
    "proyecto": proyecto_data,
    "responsables": responsables_data,
}
doc.render(context)
doc.save(f"output/{cliente.nombre_corto}_POL-100_v{version}.docx")
```

### Validación post-generación

Cada documento generado debe pasar la siguiente validación automática del Motor 6:

1. **Sin placeholders sin sustituir**: ningún `{{ ... }}` debe quedar en el output final.
2. **Sin bloques `{% if %}` mal cerrados**: si quedan, fallar el render.
3. **Hash SHA-256** del documento generado registrado en la BD junto al `cliente_id` y la versión.
4. **Firma Ed25519** del Motor 6 sobre el hash, para garantizar autenticidad de la generación.
5. **Watermark FULKRO** discreto en pie de página: `Generado por FULKRO · fulkro.es · {fecha} · Hash: {hash[:8]}`

### Próximas plantillas (F1.2)

En la siguiente respuesta de F1.2 cierro las 4 políticas restantes del bloque crítico:
- **E-105** Política de Cifrado y Gestión de Claves Criptográficas
- **E-106** Política de Uso Aceptable de los Recursos
- **E-107** Política de Seguridad en las Relaciones con Proveedores
- **E-108** Política de Clasificación y Tratamiento de la Información

Tras F1.1 y F1.2 quedarán listas las **9 políticas críticas** del SGSI ENS. Las 18 políticas restantes (E-109 a E-126) son secundarias y pueden generarse a partir de plantillas más ligeras o redactarse específicamente con un consultor ENS senior antes del primer cliente real.

---

**Fin del Entregable F1.1.**

5 políticas críticas con texto legal real español, ~12.500 palabras totales, listas para ingestar al Motor 6 (Document Factory) durante la Semana 5 del plan de construcción FULKRO.
