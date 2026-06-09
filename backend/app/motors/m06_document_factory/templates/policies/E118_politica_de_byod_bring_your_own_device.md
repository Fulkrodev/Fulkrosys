# DOCUMENTO E-118 — POLÍTICA DE BYOD (Bring Your Own Device)

**Política condicional: solo aplica cuando la Entidad permite el uso de dispositivos personales para actividades laborales.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-118"
titulo: "Política de Uso de Dispositivos Personales (BYOD)"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE USO DE DISPOSITIVOS PERSONALES (BYOD) DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-118 — Versión {{ proyecto.version_actual }}**

---

## MARCO NORMATIVO

Esta política se desarrolla en cumplimiento del **Real Decreto 311/2022**, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad (ENS), y en particular de las siguientes medidas recogidas en su Anexo II:

- **mp.eq.3** — Protección de equipos portátiles (MDM obligatorio en BYOD).
- **mp.per.4** — Formación y concienciación (uso seguro del dispositivo personal).
- **op.acc.5** — Mecanismo de autenticación (MFA obligatorio para acceso corporativo desde BYOD).
- **mp.com.2** — Protección de la confidencialidad en comunicaciones (VPN exigida).

Asimismo, se alinea con las obligaciones derivadas del **Reglamento (UE) 2016/679 (RGPD)** y la **LO 3/2018 LOPDGDD** cuando el BYOD pueda implicar el tratamiento de datos personales en dispositivos no propiedad de la Entidad, respetando el principio de responsabilidad proactiva (art. 24 RGPD) y la minimización (art. 5.1.c RGPD).

Complementa la Política Maestra de Seguridad ({{ proyecto.codigo_documento_base }}-100), la Política de Uso Aceptable ({{ proyecto.codigo_documento_base }}-103) y la Política de Teletrabajo y Movilidad ({{ proyecto.codigo_documento_base }}-110).

---

## 1. OBJETO

Establecer las condiciones bajo las cuales el personal de {{ cliente.razon_social }} podrá utilizar dispositivos personales (ordenadores portátiles, teléfonos móviles, tabletas) para acceder a información y sistemas corporativos.

## 2. POSICIÓN DE LA ENTIDAD

{% if cliente.permite_byod %}
{{ cliente.razon_social }} **autoriza** el uso de dispositivos personales para actividades laborales, sujeto al cumplimiento estricto de los requisitos establecidos en la presente Política.
{% else %}
{{ cliente.razon_social }} **no autoriza** con carácter general el uso de dispositivos personales para acceder a los sistemas o información comprendidos en el alcance del SGSI. Las excepciones deberán ser autorizadas individualmente por el Responsable de la Seguridad.
{% endif %}

## 3. REQUISITOS MÍNIMOS DEL DISPOSITIVO PERSONAL

Para ser autorizado, el dispositivo personal deberá cumplir:

a) Sistema operativo con soporte vigente del fabricante y actualizaciones al día.

b) **Cifrado de disco completo** activado.

c) **Código de desbloqueo** o autenticación biométrica activados, con bloqueo automático a 5 minutos de inactividad.

d) Software antimalware instalado y actualizado (o protección nativa del sistema operativo equivalente).

e) No tener root/jailbreak aplicado.

f) Posibilidad de borrado remoto (MDM corporativo o funcionalidad nativa del sistema operativo).

## 4. CONDICIONES DE USO

a) El acceso a sistemas corporativos desde dispositivos personales se realizará **exclusivamente** a través de la VPN corporativa o de soluciones de escritorio virtual (VDI) autorizadas.

b) La información clasificada como CONFIDENCIAL o RESTRINGIDA **no se almacenará localmente** en el dispositivo personal.

c) Se utilizarán contenedores corporativos (MDM) para separar los datos personales de los corporativos cuando la tecnología lo permita.

d) La Entidad se reserva el derecho de **borrar remotamente** los datos corporativos del dispositivo en caso de pérdida, sustracción, cese de la relación laboral o incidente de seguridad.

e) La persona usuaria acepta que el dispositivo personal podrá ser **inspeccionado** por el equipo de seguridad en caso de incidente, limitándose la inspección al contenedor corporativo.

## 5. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-118 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
