# DOCUMENTO E-123 — POLÍTICA DE SEGURIDAD FÍSICA

**Política nueva. Materializa mp.if.1 a mp.if.7 del Anexo II del ENS y los controles A.7.1 a A.7.14 de ISO/IEC 27001:2022. Es la política que cubría el 0% en la familia mp.if de la auditoría.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-123"
titulo: "Política de Seguridad Física y Ambiental"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE SEGURIDAD FÍSICA Y AMBIENTAL DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-123 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los principios y requisitos aplicables a la protección física de las instalaciones, equipos e infraestructuras que albergan los sistemas de información comprendidos en el alcance del SGSI de {{ cliente.razon_social }}, en cumplimiento de las medidas **mp.if.1 (Áreas separadas y con control de acceso)**, **mp.if.2 (Identificación de las personas)**, **mp.if.3 (Acondicionamiento de los locales)**, **mp.if.4 (Energía eléctrica)**, **mp.if.5 (Protección frente a incendios)**, **mp.if.6 (Protección frente a inundaciones)** y **mp.if.7 (Registro de entrada y salida de equipamiento)** del Anexo II del Real Decreto 311/2022.

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a todas las instalaciones físicas que albergan elementos del sistema comprendidos en el alcance del SGSI:

{% for sede in cliente.sedes %}
- **{{ sede.nombre }}** — {{ sede.direccion }}
{% endfor %}

## 3. ZONAS DE SEGURIDAD

Las instalaciones se organizarán en zonas de seguridad concéntricas, con control de acceso progresivamente más restrictivo:

### 3.1 Zona pública

Áreas accesibles sin restricción: recepción, salas de reuniones externas, zonas comunes del edificio.

### 3.2 Zona controlada

Áreas de oficina restringidas al personal de la Entidad y a visitantes acompañados. Requieren identificación y registro.

### 3.3 Zona restringida

Áreas que albergan equipos de red, servidores, cabinas de comunicaciones o información clasificada como CONFIDENCIAL. Acceso limitado a personal autorizado con necesidad de saber.

### 3.4 Zona crítica

Centro de proceso de datos (CPD) o sala de servidores, si existe en las instalaciones de la Entidad. Acceso limitado al personal técnico expresamente autorizado, con registro individual de entradas y salidas.

## 4. CONTROL DE ACCESO FÍSICO [mp.if.1, mp.if.2]

a) Las zonas restringidas y críticas dispondrán de mecanismos de control de acceso (tarjeta magnética, biométrico u otros) que registren la identidad de cada persona que accede, la fecha y hora.

b) Los visitantes a zonas controladas o superiores serán identificados, registrados y acompañados durante toda su visita.

c) Las llaves, tarjetas y códigos de acceso se gestionarán mediante inventario controlado por el Responsable del Sistema, con procedimiento de entrega, devolución y desactivación al cese.

## 5. ACONDICIONAMIENTO DE LOCALES [mp.if.3]

Las salas que alberguen equipos críticos dispondrán de:

a) Sistema de climatización que mantenga temperatura y humedad dentro de los rangos operativos recomendados por los fabricantes de los equipos.

b) Suelo técnico o canalización adecuada para el tendido ordenado de cableado.

c) Aislamiento acústico y visual suficiente para evitar la observación no autorizada.

## 6. SUMINISTRO ELÉCTRICO [mp.if.4]

{% if proyecto.categoria_ens in ["MEDIA", "ALTA"] %}
Los equipos críticos dispondrán de:

a) Sistemas de alimentación ininterrumpida (SAI/UPS) con autonomía suficiente para un apagado ordenado (mínimo 15 minutos para categoría MEDIA, 30 minutos para categoría ALTA).

b) Protección frente a sobretensiones y transitorios eléctricos.

c) Grupo electrógeno o acuerdo contractual con proveedor de energía alternativo para las zonas críticas, cuando la categoría sea ALTA.
{% else %}
Los equipos que soporten servicios incluidos en el alcance dispondrán de protección frente a sobretensiones y, deseablemente, de sistemas de alimentación ininterrumpida (SAI/UPS) para un apagado ordenado.
{% endif %}

## 7. PROTECCIÓN CONTRA INCENDIOS [mp.if.5]

Las instalaciones cumplirán con la normativa de protección contra incendios aplicable (CTE, RIPCI) y, adicionalmente:

a) Las zonas restringidas y críticas dispondrán de sistemas de detección automática de incendios.

b) Se dispondrá de extintores adecuados (CO₂ o agente limpio en zonas con equipos electrónicos) correctamente señalizados y revisados periódicamente.

c) Se prohíbe fumar y almacenar materiales inflamables en las zonas restringidas y críticas.

## 8. PROTECCIÓN CONTRA INUNDACIONES [mp.if.6]

a) Los equipos críticos se instalarán, siempre que sea posible, en ubicaciones no susceptibles de inundación (evitar sótanos y plantas bajas en zonas de riesgo).

b) Se instalarán sensores de agua en las salas que alberguen equipos críticos.

c) El cableado de red y de alimentación se tenderá por canalizaciones elevadas respecto al suelo.

## 9. REGISTRO DE ENTRADA Y SALIDA DE EQUIPAMIENTO [mp.if.7]

Toda entrada o salida de equipamiento (servidores, dispositivos de almacenamiento, cintas de backup, soportes extraíbles) de las zonas restringidas y críticas se registrará, indicando:

a) Descripción del equipo y número de serie.

b) Persona que lo introduce o retira y motivo.

c) Fecha y hora.

d) Autorización del Responsable del Sistema.

## 10. MANTENIMIENTO DE INSTALACIONES

Las instalaciones y sus sistemas de protección (climatización, SAI, detección de incendios, control de accesos) serán objeto de mantenimiento preventivo periódico conforme a los contratos de mantenimiento suscritos y a la normativa técnica aplicable.

## 11. APROBACIÓN, REVISIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual y siempre que se produzcan cambios en las instalaciones.

---

**Documento {{ proyecto.codigo_documento_base }}-123 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

## RESUMEN DEL BLOQUE 5A

### 7 políticas nuevas PRIORIDAD ALTA entregadas

| ID v2.1 | Título | Líneas aprox. | Medidas ENS cubiertas |
|---|---|---|---|
| **E-102** | Contraseñas y Autenticación | ~130 | op.acc.5, op.acc.6 |
| **E-105** | Tratamiento de Datos Personales (RGPD) | ~120 | mp.info.1 |
| **E-106** | Copias de Seguridad | ~70 | mp.info.9 |
| **E-110** | Teletrabajo y Movilidad | ~110 | mp.eq.3, mp.eq.4 |
| **E-111** | Uso de Servicios Cloud | ~100 | op.ext.1-4, CCN-STIC 887 |
| **E-119** | Respuesta a Brechas de Datos Personales | ~100 | RGPD art. 33-34 |
| **E-123** | Seguridad Física y Ambiental | ~120 | mp.if.1-7 (antes 0% cobertura) |

### Estado de las 27 políticas tras este bloque

| Estado | Cantidad | IDs |
|---|---|---|
| ✅ Existentes (renumeradas de F1) | 8 | E-100, E-101, E-103, E-104, E-107, E-108, E-109, E-112 |
| ✅ **Nuevas en este bloque** | **7** | **E-102, E-105, E-106, E-110, E-111, E-119, E-123** |
| 🔲 Pendientes (bloque 5B) | 12 | E-113, E-114, E-115, E-116, E-117, E-118, E-120, E-121, E-122, E-124, E-125, E-126 |

**Progreso: 15/27 políticas completas (56%).**

### Siguiente: Bloque 5B — las 12 políticas restantes (prioridad MEDIA y BAJA)

Si me dices "seguimos" arranco inmediatamente con las 12 que faltan para cerrar las 27/27 políticas.
