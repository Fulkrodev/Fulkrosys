# DOCUMENTO E-125 — POLÍTICA DE MESA LIMPIA Y PANTALLA LIMPIA

**Subpolítica operativa de la Política de Uso Aceptable (E-103). Control A.7.7 de ISO/IEC 27001:2022.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-125"
titulo: "Política de Mesa Limpia y Pantalla Limpia"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE MESA LIMPIA Y PANTALLA LIMPIA DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-125 — Versión {{ proyecto.version_actual }}**

---

## MARCO NORMATIVO

Esta política se desarrolla en cumplimiento del **Real Decreto 311/2022**, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad (ENS), y en particular de las siguientes medidas recogidas en su Anexo II:

- **mp.if.2** — Identificación de las personas (control de acceso físico al puesto de trabajo).
- **mp.eq.1** — Puesto de trabajo despejado (mesa limpia — base normativa directa de esta política).
- **mp.eq.2** — Bloqueo del puesto de trabajo (pantalla limpia tras inactividad).

Está alineada con el control **A.7.7** de la norma **ISO/IEC 27001:2022** (Clear desk and clear screen), que inspira esta subpolítica. Complementa la Política Maestra ({{ proyecto.codigo_documento_base }}-100) y se considera subpolítica operativa de la Política de Uso Aceptable ({{ proyecto.codigo_documento_base }}-103).

---

## 1. OBJETO

Reducir el riesgo de acceso no autorizado, pérdida o daño de la información durante y fuera del horario laboral, mediante la adopción de normas de orden del puesto de trabajo y de protección de la información visible en pantalla.

## 2. NORMAS DE MESA LIMPIA

a) La documentación en papel clasificada como CONFIDENCIAL o RESTRINGIDA se guardará bajo llave al finalizar la jornada o al abandonar el puesto.

b) Los soportes extraíbles (USB, discos) no se dejarán desatendidos sobre la mesa.

c) Las pizarras y notas adhesivas con información sensible se limpiarán al finalizar las reuniones.

d) Las impresoras y fotocopiadoras compartidas se revisarán para retirar documentos olvidados.

e) Los documentos sensibles en espera de destrucción se depositarán en contenedores de destrucción segura, nunca en papeleras ordinarias.

## 3. NORMAS DE PANTALLA LIMPIA

a) La sesión del equipo se bloqueará al abandonar el puesto, aunque sea por un breve periodo. El bloqueo automático se configurará a un máximo de **5 minutos** de inactividad.

b) La información sensible no se dejará visible en pantalla en ausencia del usuario.

c) En reuniones con personas externas, se cerrará cualquier aplicación o documento no relacionado con el objeto de la reunión.

d) Se utilizarán filtros de privacidad en los monitores de los puestos situados en zonas de tránsito o accesibles a visitantes.

## 4. VERIFICACIÓN

El Responsable de la Seguridad podrá realizar verificaciones periódicas no intrusivas del cumplimiento de esta Política, documentando los hallazgos y comunicándolos al personal afectado con carácter educativo.

## 5. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-125 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
