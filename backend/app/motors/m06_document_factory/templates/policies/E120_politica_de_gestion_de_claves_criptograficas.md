# DOCUMENTO E-120 — POLÍTICA DE GESTIÓN DE CLAVES CRIPTOGRÁFICAS

**Amplía la sección de ciclo de vida de claves de la Política Criptográfica (E-107) para categoría ALTA. En categoría MEDIA es parcialmente obligatoria.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-120"
titulo: "Política de Gestión de Claves Criptográficas"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE GESTIÓN DE CLAVES CRIPTOGRÁFICAS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-120 — Versión {{ proyecto.version_actual }}**

---

## MARCO NORMATIVO

Esta política se desarrolla en cumplimiento del **Real Decreto 311/2022**, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad (ENS), y en particular de las siguientes medidas recogidas en su Anexo II:

- **mp.info.9** — Cifrado (gestión del ciclo de vida de claves, obligatoria desde categoría MEDIA para datos con valoración C ≥ MEDIO).
- **mp.com.2** — Protección de la confidencialidad en comunicaciones (cifrado TLS/VPN con claves gestionadas bajo esta política).
- **op.exp.5** — Gestión de vulnerabilidades (rotación obligatoria ante compromiso de clave o vulnerabilidad del algoritmo).

Se alinea con las especificaciones de la guía **CCN-STIC 807** (Cifrado y algoritmos criptográficos aprobados para el ENS) y con la norma **NIST SP 800-57** (Recommendation for Key Management). Para entornos cloud, se apoya en las capacidades de HSM/KMS certificadas (Azure Key Vault Premium, AWS KMS con CMK, GCP Cloud KMS con HSM-backed keys) según catálogo de PCE Cloud aplicable.

Complementa la Política Maestra ({{ proyecto.codigo_documento_base }}-100), la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107) y la Política de Protección de la Información ({{ proyecto.codigo_documento_base }}-111).

---

## 1. OBJETO

Desarrollar en detalle el ciclo de vida completo de las claves criptográficas de {{ cliente.razon_social }}, complementando la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107) con los requisitos operativos para la generación, distribución, almacenamiento, rotación, archivo, revocación y destrucción de claves.

## 2. INVENTARIO DE CLAVES

Se mantendrá un **Inventario de Claves Criptográficas** que registre para cada clave: identificador, tipo (simétrica/asimétrica), algoritmo, longitud, propósito, sistema al que sirve, fecha de generación, fecha de expiración, custodio y estado (activa/expirada/revocada/destruida).

## 3. GENERACIÓN

Las claves se generarán exclusivamente mediante generadores criptográficamente seguros (CSPRNG) o hardware criptográfico dedicado (HSM). Queda prohibida la generación manual o con fuentes de aleatoriedad no verificadas.

## 4. CUSTODIA

| Tipo de clave | Mecanismo de custodia |
|---|---|
| Claves maestras (KEK) | HSM o vault corporativo con control de acceso dual |
| Claves operativas simétricas | Vault cifrado con acceso restringido |
| Claves privadas asimétricas | Almacenadas en el dispositivo destino, nunca exportables sin cifrar |
| Certificados digitales de personal | Dispositivo criptográfico personal (tarjeta inteligente, token USB) |

## 5. ROTACIÓN

| Tipo de clave | Plazo máximo de rotación |
|---|---|
| Claves de sesión TLS | Por sesión |
| Claves operativas (cifrado datos en reposo) | 24 meses |
| Claves de servidor (TLS) | 12 meses |
| Certificados de personal | Conforme al periodo del certificado (máx. 36 meses) |
| Claves maestras (KEK) | 36 meses |

## 6. COMPROMISO

En caso de compromiso o sospecha, se procederá a la revocación inmediata, generación de clave de sustitución, reevaluación de la integridad de la información afectada y gestión como incidente conforme a {{ proyecto.codigo_documento_base }}-108.

## 7. DESTRUCCIÓN

Las claves que dejen de ser necesarias se destruirán de forma irreversible, salvo las que deban conservarse para acceder a información cifrada histórica, que se archivarán en repositorio de claves históricas con controles reforzados.

## 8. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-120 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
