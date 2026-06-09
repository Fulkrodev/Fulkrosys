# DOCUMENTO E-126 — POLÍTICA DE BORRADO SEGURO Y DESTRUCCIÓN DE INFORMACIÓN

**Materializa mp.si.5 del Anexo II y desarrolla la sección 9 de la Política de Clasificación (E-104) sobre destrucción y eliminación.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-126"
titulo: "Política de Borrado Seguro y Destrucción de Información"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE BORRADO SEGURO Y DESTRUCCIÓN DE INFORMACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-126 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Garantizar que la información de {{ cliente.razon_social }} se elimina de forma irreversible cuando deja de ser necesaria, evitando que pueda ser recuperada por personas no autorizadas, en cumplimiento de la medida **mp.si.5 (Borrado y destrucción)** del Anexo II del Real Decreto 311/2022, del artículo 5.1.e) del RGPD (limitación del plazo de conservación) y del artículo 32 de la LOPDGDD (bloqueo previo a la supresión).

## 2. MÉTODOS DE BORRADO Y DESTRUCCIÓN POR TIPO DE SOPORTE

### 2.1 Soportes electrónicos

| Nivel de clasificación | Método admitido |
|---|---|
| PÚBLICA / INTERNA | Borrado lógico (formateo) |
| CONFIDENCIAL | Sobreescritura segura (mínimo 1 pasada con verificación), desmagnetización (degaussing) o cifrado previo con destrucción de clave |
| RESTRINGIDA | Destrucción física del soporte (trituración, incineración) o desmagnetización certificada + sobreescritura |

Para los discos SSD y memorias flash, la sobreescritura simple no garantiza el borrado completo. Se utilizará el comando **ATA Secure Erase** del firmware del disco, o bien la destrucción física del soporte, o bien el borrado criptográfico (cifrar el soporte completo y destruir la clave de cifrado).

### 2.2 Soportes en papel

| Nivel | Método admitido | Nivel DIN 66399 / UNE-EN 15713 |
|---|---|---|
| PÚBLICA / INTERNA | Trituración básica | P-2 |
| CONFIDENCIAL | Trituración con corte cruzado | P-3 |
| RESTRINGIDA | Trituración con corte cruzado fino | P-5 o superior |

### 2.3 Soportes ópticos y cintas

Destrucción física (trituración) conforme al nivel DIN 66399 correspondiente al nivel de clasificación de la información que contienen.

## 3. PROVEEDORES DE DESTRUCCIÓN

Cuando la destrucción se confíe a proveedores especializados, estos deberán cumplir los requisitos de la Política de Gestión de Proveedores ({{ proyecto.codigo_documento_base }}-112) y emitir un **certificado de destrucción** firmado que identifique: los soportes destruidos (número de serie), el método utilizado, la fecha y hora, y la persona responsable del proveedor.

## 4. DATOS PERSONALES — BLOQUEO PREVIO

Conforme al artículo 32 de la LOPDGDD, antes de la supresión definitiva de datos personales se procederá a su **bloqueo** durante el plazo de prescripción de las acciones legales que pudieran derivarse del tratamiento, manteniéndolos a disposición exclusiva de jueces, tribunales, Ministerio Fiscal o Administraciones Públicas competentes.

## 5. REGISTRO DE DESTRUCCIÓN

Toda destrucción de soportes que contengan información CONFIDENCIAL o RESTRINGIDA se documentará en el **Registro de Destrucción**, indicando: soporte destruido, contenido, nivel de clasificación, método utilizado, fecha, persona responsable y, en su caso, referencia al certificado del proveedor.

## 6. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-126 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

## RESUMEN DEL BLOQUE 5B

### 12 políticas restantes entregadas

| ID v2.1 | Título | Líneas aprox. | Medidas ENS cubiertas |
|---|---|---|---|
| **E-113** | Adquisición de Tecnología | ~55 | op.pl.3, op.pl.5 (CPSTIC) |
| **E-114** | Desarrollo Seguro (SSDLC) | ~90 | mp.sw.1, mp.sw.2 |
| **E-115** | Gestión de Vulnerabilidades | ~50 | op.exp.4 |
| **E-116** | Gestión de Cambios | ~45 | op.exp.5 |
| **E-117** | Gestión de Privilegios y PAM | ~75 | op.acc.3, op.acc.4 |
| **E-118** | BYOD | ~55 | Condicional |
| **E-120** | Gestión de Claves Criptográficas | ~60 | mp.si.2 (profundizado) |
| **E-121** | Redes y Comunicaciones | ~65 | mp.com.1-4 |
| **E-122** | Gestión de Soportes | ~50 | mp.si.1-5 |
| **E-124** | Seguridad del Personal | ~60 | mp.per.1-4 |
| **E-125** | Mesa Limpia y Pantalla Limpia | ~40 | A.7.7 ISO 27001 |
| **E-126** | Borrado Seguro y Destrucción | ~65 | mp.si.5 + RGPD art. 5.1.e + LOPDGDD art. 32 |

### HITO: 27/27 POLÍTICAS COMPLETADAS ✅

| Bloque | Políticas | Estado |
|---|---|---|
| F1.1+F1.2 originales (renumeradas) | E-100, E-101, E-103, E-104, E-107, E-108, E-109, E-112 | ✅ 8 renumeradas |
| Corrección 5A (nuevas ALTA) | E-102, E-105, E-106, E-110, E-111, E-119, E-123 | ✅ 7 nuevas |
| **Corrección 5B (nuevas MEDIA/BAJA)** | **E-113-E-118, E-120-E-122, E-124-E-126** | **✅ 12 nuevas** |
| **TOTAL** | **27/27** | **100%** |

### Cobertura ENS por familia tras las 27 políticas

| Familia ENS | Cobertura | Políticas que la cubren |
|---|---|---|
| **org** | 100% | E-100, E-116 |
| **op.pl** | 100% | E-100, E-113, E-115 |
| **op.acc** | 100% | E-101, E-102, E-117 |
| **op.exp** | 100% | E-108, E-115, E-116 |
| **op.ext** | 100% | E-112, E-111 |
| **op.cont** | 100% | E-109, E-106 |
| **mp.if** | **100%** | **E-123** (antes 0%) |
| **mp.per** | **100%** | **E-124** (antes 30%) |
| **mp.eq** | 100% | E-103, E-110, E-118 |
| **mp.com** | 100% | E-107, E-121 |
| **mp.si** | 100% | E-107, E-120, E-122 |
| **mp.sw** | **100%** | **E-114** (antes 60%) |
| **mp.info** | 100% | E-104, E-105, E-106, E-107, E-119 |
| **mp.s** | 100% | E-103, E-115 |
| **TOTAL** | **100%** | **Todas las familias del Anexo II cubiertas** |

### Siguiente paso: CORRECCIÓN 6 — los 27 procedimientos nuevos

Con las 27 políticas completas, el siguiente bloque es generar los **27 procedimientos que faltan** para completar 35/35 del catálogo v2.1 §2.7. Esto es el bloque más pesado restante (~4-5 respuestas).

**¿Seguimos con los procedimientos?**
