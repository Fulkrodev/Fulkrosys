# DOCUMENTO E-122 — POLÍTICA DE GESTIÓN DE SOPORTES

**Materializa mp.si.1 a mp.si.5 del Anexo II (etiquetado, criptografía, custodia, transporte, borrado de soportes de información).**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-122"
titulo: "Política de Gestión de Soportes de Información"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE GESTIÓN DE SOPORTES DE INFORMACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-122 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las normas aplicables al etiquetado, cifrado, custodia, transporte, reutilización y destrucción de los soportes de información (discos duros, memorias USB, cintas, discos ópticos, documentos en papel) de {{ cliente.razon_social }}, en cumplimiento de las medidas **mp.si.1 a mp.si.5** del Anexo II del Real Decreto 311/2022.

## 2. INVENTARIO

Todo soporte que contenga información del alcance del SGSI se registrará en el inventario de soportes, indicando: tipo, identificador, contenido (nivel de clasificación), custodio, ubicación y fecha de creación.

## 3. ETIQUETADO [mp.si.1]

Los soportes que contengan información CONFIDENCIAL o RESTRINGIDA llevarán etiqueta visible indicando su nivel de clasificación conforme a la Política de Clasificación ({{ proyecto.codigo_documento_base }}-104).

## 4. CIFRADO [mp.si.2]

Los soportes extraíbles que contengan información CONFIDENCIAL o RESTRINGIDA se cifrarán conforme a la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107).

## 5. CUSTODIA [mp.si.3]

Los soportes se custodiarán en condiciones que garanticen su integridad, disponibilidad y confidencialidad, proporcionales a su clasificación. Los soportes con información RESTRINGIDA se guardarán bajo llave con acceso limitado a los custodios autorizados.

## 6. TRANSPORTE [mp.si.4]

El transporte de soportes fuera de las instalaciones de la Entidad requerirá cifrado, embalaje protector, registro de salida conforme al apartado 9 de la Política de Seguridad Física ({{ proyecto.codigo_documento_base }}-123) y, para información RESTRINGIDA, acompañamiento presencial.

## 7. BORRADO Y DESTRUCCIÓN [mp.si.5]

La reutilización o eliminación de soportes se realizará conforme a la Política de Borrado Seguro ({{ proyecto.codigo_documento_base }}-126), garantizando la imposibilidad de recuperación de la información.

## 8. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-122 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
