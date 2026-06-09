# DOCUMENTO E-110 — POLÍTICA DE TELETRABAJO Y MOVILIDAD

**Política nueva. Materializa mp.eq.3 (Protección de equipos portátiles) y mp.eq.4 (Otros dispositivos conectados a la red) del Anexo II del ENS, y el control A.6.7 (Trabajo a distancia) de ISO/IEC 27001:2022.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-110"
titulo: "Política de Teletrabajo y Movilidad"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE TELETRABAJO Y MOVILIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-110 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las condiciones de seguridad aplicables al trabajo a distancia y al uso de dispositivos móviles fuera de las instalaciones controladas por {{ cliente.razon_social }}, garantizando que la información y los sistemas del alcance del SGSI mantienen un nivel de protección equivalente al de las instalaciones corporativas.

## 2. ÁMBITO DE APLICACIÓN

Se aplica a toda persona, interna o externa, que acceda a los sistemas o información de la Entidad desde ubicaciones no controladas por esta, incluyendo el domicilio particular, espacios de coworking, instalaciones de clientes, desplazamientos y cualquier otro entorno fuera de las sedes corporativas.

## 3. AUTORIZACIÓN

### 3.1 Autorización previa

El trabajo a distancia se realizará exclusivamente en los términos autorizados por la Entidad conforme a la normativa laboral aplicable (Real Decreto-ley 28/2020, de 22 de septiembre, de trabajo a distancia, o norma que lo sustituya) y al acuerdo individual de teletrabajo suscrito con cada persona.

### 3.2 Autorización de seguridad

Con independencia de la autorización laboral, el Responsable de la Seguridad autorizará los perfiles de acceso remoto admisibles, los dispositivos autorizados y los canales de conexión permitidos.

## 4. REQUISITOS TÉCNICOS OBLIGATORIOS

### 4.1 Canal cifrado

Todo acceso remoto a los sistemas corporativos se realizará exclusivamente a través de un **canal cifrado** (VPN corporativa con TLS 1.2 o superior, o equivalente), conforme a la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107).

### 4.2 Autenticación multifactor

El acceso remoto requerirá **autenticación multifactor obligatoria**, conforme a la Política de Contraseñas y Autenticación ({{ proyecto.codigo_documento_base }}-102), sin excepción.

### 4.3 Dispositivos autorizados

Solo se permitirá el acceso remoto desde **dispositivos corporativos gestionados** por la Entidad o desde dispositivos personales que cumplan los requisitos de la Política de BYOD ({{ proyecto.codigo_documento_base }}-118), cuando esta sea aplicable.

### 4.4 Cifrado del dispositivo

Los dispositivos portátiles (laptops, tabletas) utilizados en teletrabajo deberán tener **cifrado de disco completo** activado (BitLocker, FileVault, LUKS) conforme a la Política Criptográfica.

### 4.5 Antimalware y actualización

Los dispositivos remotos deberán tener instalado y actualizado el software antimalware corporativo y las actualizaciones de seguridad del sistema operativo al día, conforme al procedimiento de vulnerabilidades ({{ proyecto.codigo_documento_base }}-205).

### 4.6 Bloqueo automático

Los dispositivos se bloquearán automáticamente tras un periodo máximo de inactividad de **5 minutos** con requerimiento de autenticación para el desbloqueo.

## 5. NORMAS DE COMPORTAMIENTO EN ENTORNO REMOTO

La persona que trabaje a distancia deberá:

a) Adoptar precauciones razonables para que terceros no observen la información mostrada en pantalla, especialmente en espacios públicos. Se recomienda el uso de filtros de privacidad.

b) No conectar los equipos corporativos a redes Wi-Fi públicas abiertas sin canal cifrado adicional (VPN activa obligatoriamente).

c) No dejar desatendidos los equipos corporativos en vehículos, hoteles o espacios compartidos sin custodia adecuada.

d) No almacenar información clasificada como CONFIDENCIAL o RESTRINGIDA en el dispositivo local si es posible trabajar directamente contra los sistemas corporativos vía VPN.

e) No imprimir documentos clasificados en impresoras no controladas por la Entidad.

f) Notificar de inmediato la pérdida o sustracción de cualquier dispositivo corporativo al Responsable de la Seguridad.

## 6. ENTORNO DOMÉSTICO

Cuando el teletrabajo se realice desde el domicilio particular, se recomienda disponer de un espacio de trabajo separado con:

a) Puerta que pueda cerrarse durante las sesiones de trabajo con información sensible.

b) Conexión a Internet propia (no compartida con otros hogares) con cifrado WPA3 o, al menos, WPA2.

c) Router doméstico con contraseña de administración cambiada respecto al valor de fábrica.

## 7. VIAJES Y DESPLAZAMIENTOS

Durante los desplazamientos se aplicarán adicionalmente las siguientes medidas:

a) No facturar equipos con información sensible en el equipaje de bodega.

b) Mantener los dispositivos bajo custodia directa en todo momento.

c) No utilizar puertos USB públicos de carga (riesgo de juice jacking) sin adaptador de solo carga.

d) Deshabilitar las conexiones inalámbricas no necesarias (Bluetooth, NFC).

## 8. REVOCACIÓN DEL ACCESO REMOTO

El Responsable de la Seguridad podrá revocar de forma inmediata y sin previo aviso el acceso remoto de cualquier persona cuando detecte un comportamiento de riesgo, un posible compromiso del dispositivo o un incumplimiento de la presente Política.

## 9. APROBACIÓN, REVISIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-110 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
