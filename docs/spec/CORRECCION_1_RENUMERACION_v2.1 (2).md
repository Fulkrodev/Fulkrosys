# CORRECCIÓN 1 — RENUMERACIÓN COMPLETA A v2.1

**Plan 100/100 FULKRO — Parche de auditoría**
**Fecha:** 10 de abril de 2026
**Motivo:** La numeración de políticas (E-1XX) y procedimientos (E-2XX) usada en los entregables F1 y F2 NO coincide con la tabla maestra de la spec v2.1 (§2.6 y §2.7). Esto rompe la trazabilidad. Se adopta la numeración de v2.1 como canónica.

---

## 1. TABLA DE MAPEO: POLÍTICAS (F1.1 + F1.2)

### 1.1 Las 9 políticas que YA TENEMOS — renumeración

| ID ANTIGUO (nuestro) | Tema del documento | ID NUEVO (v2.1) | Tema en v2.1 para ese ID | ¿Coincide? |
|---|---|---|---|---|
| E-100 | Política de Seguridad de la Información | **E-100** | Política de Seguridad de la Información | ✅ Coincide |
| E-101 | Roles, Responsabilidades y Autoridades | **Sin ID propio en v2.1** | v2.1 E-101 = Control de Accesos | ❌ Nuestro E-101 no existe como política separada en v2.1. **DECISIÓN:** el contenido de "Roles y Responsabilidades" se integra como sección ampliada dentro de E-100 (la Política de Seguridad madre) y como el documento de nombramiento que v2.1 describe en §2.1. No se mantiene como política independiente. |
| E-102 | Política de Control de Acceso | **E-101** | Política de Control de Accesos | ✅ Tema coincide (renumerar) |
| E-103 | Política de Gestión de Incidentes | **E-108** | Política de Gestión de Incidentes | ✅ Tema coincide (renumerar) |
| E-104 | Política de Continuidad del Servicio | **E-109** | Política de Continuidad de Negocio | ✅ Tema coincide (renumerar) |
| E-105 | Política de Cifrado y Gestión de Claves | **E-107** | Política Criptográfica | ✅ Tema coincide (renumerar + absorber E-120 "Gestión de Claves" como subsección) |
| E-106 | Política de Uso Aceptable de los Recursos | **E-103** | Política de Uso Aceptable de los recursos TI | ✅ Tema coincide (renumerar) |
| E-107 | Política de Seguridad en Relaciones con Proveedores | **E-112** | Política de Gestión de Proveedores | ✅ Tema coincide (renumerar) |
| E-108 | Política de Clasificación y Tratamiento de la Información | **E-104** | Política de Clasificación de la Información | ✅ Tema coincide (renumerar) |

### 1.2 Tabla de conversión directa para sed/regex

```
E-100 → E-100  (sin cambio)
E-101 → ABSORBER en E-100 (sección 7 "Estructura organizativa")
E-102 → E-101
E-103 → E-108
E-104 → E-109
E-105 → E-107
E-106 → E-103
E-107 → E-112
E-108 → E-104
```

### 1.3 Las 18 políticas que FALTAN por crear (v2.1 §2.6)

| ID v2.1 | Título v2.1 | Prioridad | Notas |
|---|---|---|---|
| **E-102** | Política de Contraseñas y Autenticación | ALTA | Extraer de nuestro E-101→E-101 la sección de contraseñas y MFA, ampliar como política independiente |
| **E-105** | Política de Tratamiento de Datos Personales (RGPD) | ALTA | Totalmente nueva. RGPD art. 5, 6, 9, 32. LOPDGDD. DPO. |
| **E-106** | Política de Copias de Seguridad | ALTA | Extraer de nuestro E-104→E-109 la sección de backup, ampliar |
| **E-110** | Política de Teletrabajo y Movilidad | ALTA | Referenciada en nuestro E-103→E-103 apartado 8 pero no desarrollada |
| **E-111** | Política de Uso de Servicios Cloud | ALTA | Referenciada en nuestro E-107→E-112 sección 7 pero no desarrollada |
| **E-113** | Política de Adquisición de Tecnología | MEDIA | op.pl.3, op.pl.5 CPSTIC |
| **E-114** | Política de Desarrollo Seguro (SSDLC) | MEDIA | Obligatoria desde categoría Media. mp.sw.1, mp.sw.2 |
| **E-115** | Política de Gestión de Vulnerabilidades | MEDIA | Ya tenemos procedimiento E-218→nuevo ID, falta política madre |
| **E-116** | Política de Gestión de Cambios | MEDIA | Ya tenemos procedimiento E-206→nuevo ID, falta política madre |
| **E-117** | Política de Gestión de Privilegios y PAM | MEDIA | Obligatoria desde categoría Media. op.acc.3, op.acc.4 |
| **E-118** | Política de BYOD | BAJA | Condicional: solo si aplica |
| **E-119** | Política de Respuesta a Brechas de Datos Personales | ALTA | RGPD art. 33-34, LOPDGDD |
| **E-120** | Política de Gestión de Claves Criptográficas | BAJA | Parcialmente cubierta en nuestro E-105→E-107. Ampliar si categoría Alta |
| **E-121** | Política de Redes y Comunicaciones | MEDIA | mp.com.1 a mp.com.4 |
| **E-122** | Política de Gestión de Soportes | BAJA | mp.si.1 a mp.si.5 |
| **E-123** | Política de Seguridad Física | ALTA | mp.if.1 a mp.if.7 — es el 0% de cobertura que teníamos en mp.if |
| **E-124** | Política de Seguridad del Personal | MEDIA | mp.per.1 a mp.per.4 |
| **E-125** | Política de Mesa Limpia y Pantalla Limpia | BAJA | Subpolítica operativa de E-103 |
| **E-126** | Política de Borrado Seguro y Destrucción | BAJA | Ya cubierto parcialmente en nuestro E-108→E-104 sección 9 |

---

## 2. TABLA DE MAPEO: PROCEDIMIENTOS (F2.1 + F2.2)

### 2.1 Los 12 procedimientos que YA TENEMOS — renumeración

| ID ANTIGUO | Tema del documento | ID NUEVO (v2.1) | Tema en v2.1 para ese ID |
|---|---|---|---|
| E-200 | Análisis y Gestión de Riesgos | **Sin ID directo en v2.1** | v2.1 E-200 = Alta de personal. **DECISIÓN:** El análisis de riesgos no tiene procedimiento en la tabla v2.1 §2.7 porque v2.1 lo trata como output del Motor 2 (MAGERIT Risk Engine), no como procedimiento documental. **Se mantiene como documento técnico E-AR-001** (Análisis de Riesgos) fuera de la serie E-2XX de procedimientos. |
| E-203 | Gestión de la Información Documentada | **E-221** | Procedimiento de gestión documental | ✅ Renumerar |
| E-204 | Gestión de Incidentes de Seguridad | **E-204** | Procedimiento de gestión de incidentes | ✅ Coincide |
| E-205 | Gestión de Cuentas y Accesos | **E-231** | Procedimiento de gestión de identidades | ✅ Tema cercano (renumerar, ampliar título) |
| E-206 | Gestión de Cambios | **E-203** | Procedimiento de gestión de cambios (con CAB) | ✅ Renumerar |
| E-207 | Concienciación y Formación | **Sin ID en v2.1** | No tiene procedimiento específico en la tabla v2.1 §2.7. **DECISIÓN:** Se mantiene como parte del Plan de Formación (§2.10 de v2.1), no como procedimiento E-2XX. Se codifica como **E-PF-001** (Plan de Formación). |
| E-210 | Copias de Seguridad y Restauración | **E-207 + E-208** | v2.1 separa backup (E-207) y restauración (E-208). **DECISIÓN:** Dividir nuestro documento en dos o mantener unificado con doble código E-207/E-208. |
| E-217 | Evaluación y Seguimiento de Proveedores | **E-217** | Evaluación de riesgos de proveedores | ✅ Coincide |
| E-218 | Gestión de Vulnerabilidades y Parches | **E-205 + E-206** | v2.1 separa vulnerabilidades (E-205) y parches (E-206). **DECISIÓN:** Dividir o mantener con doble código. |
| E-219 | Hardening y Configuración Segura | **Sin ID directo** | No tiene procedimiento específico en v2.1 §2.7. **DECISIÓN:** Se codifica como **E-IT-001** (Instrucción Técnica de Hardening) conforme al esquema de nomenclatura de la spec. |
| E-228 | Recopilación y Custodia de Evidencias | **Sin ID directo** | v2.1 E-228 = Respuesta ante pérdida/robo de dispositivos (tema distinto). **DECISIÓN:** Nuestro contenido sobre custodia de evidencias es parte del procedimiento de incidentes E-204 (anexo forense). Se codifica como **E-204-A** (Anexo forense del procedimiento de incidentes). |
| E-234 | Auditoría Interna del SGSI | **E-218** | Procedimiento de auditoría interna | ✅ Renumerar |

### 2.2 Tabla de conversión directa

```
E-200 (Análisis Riesgos) → E-AR-001 (sale de la serie E-2XX)
E-203 (Info Documentada) → E-221
E-204 (Incidentes) → E-204 (sin cambio)
E-205 (Cuentas y Accesos) → E-231
E-206 (Cambios) → E-203
E-207 (Concienciación) → E-PF-001 (sale de la serie E-2XX)
E-210 (Backup+Restore) → E-207 + E-208 (split o doble código)
E-217 (Proveedores) → E-217 (sin cambio)
E-218 (Vulns+Parches) → E-205 + E-206 (split o doble código)
E-219 (Hardening) → E-IT-001 (sale de la serie E-2XX, pasa a Instrucciones Técnicas)
E-228 (Evidencias) → E-204-A (anexo del procedimiento de incidentes)
E-234 (Auditoría Interna) → E-218
```

### 2.3 Los 23 procedimientos que FALTAN por crear (v2.1 §2.7)

| ID v2.1 | Título v2.1 | Prioridad | Notas |
|---|---|---|---|
| **E-200** | Alta de personal (técnico y lógico) | ALTA | Accesos, formación, firma NDA, alta en sistemas |
| **E-201** | Baja de personal | ALTA | Revocación accesos, devolución equipos, exit interview |
| **E-202** | Cambio de rol | ALTA | Revisión de accesos al cambiar de puesto |
| **E-208** | Restauración (con pruebas periódicas) | MEDIA | Si decidimos split de nuestro E-210 |
| **E-209** | Pruebas de continuidad | ALTA | Actualmente cubierto parcialmente en nuestra E-104→E-109 |
| **E-210** | Revisión periódica de accesos | ALTA | Cubierto parcialmente en nuestro E-205→E-231 sección 6 |
| **E-211** | Gestión de cuentas privilegiadas | ALTA | PAM, break-glass, rotación — parcial en nuestro E-205→E-231 secciones 8-9 |
| **E-212** | Respuesta a brechas RGPD | ALTA | RGPD art. 33-34, coordinación con DPO |
| **E-213** | Notificación de brechas a la AEPD | ALTA | Formulario sede electrónica AEPD, plazo 72h |
| **E-214** | Destrucción segura de información | MEDIA | UNE-EN 15713, niveles P-3/P-5, certificados |
| **E-215** | Gestión de soportes extraíbles | BAJA | USB, discos externos, cintas |
| **E-216** | Gestión de proveedores | MEDIA | Operativo de nuestro E-107→E-112, complementa E-217 |
| **E-219** | Revisión por la dirección | ALTA | Input/output annual management review del SGSI |
| **E-220** | Gestión de no conformidades | ALTA | NC mayores/menores, PAC, verificación cierre |
| **E-222** | Gestión de excepciones | MEDIA | Registro, autorización, vigencia, compensatorias |
| **E-223** | Revisión de logs | ALTA | Qué logs, quién revisa, frecuencia, qué buscar |
| **E-224** | Despliegue de software (SSDLC operativo) | MEDIA | CI/CD seguro, validación pre-producción |
| **E-225** | Pruebas pre-producción | MEDIA | Entornos staging, criterios de paso a producción |
| **E-226** | Teletrabajo | MEDIA | VPN, MFA, equipos, política pantalla limpia remota |
| **E-227** | Uso de cloud | MEDIA | Operativo de la política E-111 |
| **E-229** | Visitas externas | BAJA | Control de visitantes a CPD/oficinas |
| **E-230** | Categorización de sistemas | ALTA | Operativo del Motor 1, Anexo I del ENS |
| **E-232** | Gestión criptográfica | MEDIA | Operativo de E-107, inventario de claves |
| **E-233** | Notificación a LUCIA | MEDIA | Operativo para sector público, aplazable para ICP actual |

---

## 3. REFERENCIAS CRUZADAS QUE DEBEN ACTUALIZARSE

Cuando se renumeren las políticas y procedimientos, hay que actualizar TODAS las referencias cruzadas en todos los documentos. Estas son las referencias más frecuentes:

### 3.1 Referencias dentro de las políticas

Cada política referencia a otras políticas y a procedimientos. Con la renumeración:

```
{{ proyecto.codigo_documento_base }}-101  →  sección ampliada de E-100 (no doc separado)
{{ proyecto.codigo_documento_base }}-102  →  {{ proyecto.codigo_documento_base }}-101
{{ proyecto.codigo_documento_base }}-103  →  {{ proyecto.codigo_documento_base }}-108
{{ proyecto.codigo_documento_base }}-104  →  {{ proyecto.codigo_documento_base }}-109
{{ proyecto.codigo_documento_base }}-105  →  {{ proyecto.codigo_documento_base }}-107
{{ proyecto.codigo_documento_base }}-106  →  {{ proyecto.codigo_documento_base }}-103
{{ proyecto.codigo_documento_base }}-107  →  {{ proyecto.codigo_documento_base }}-112
{{ proyecto.codigo_documento_base }}-108  →  {{ proyecto.codigo_documento_base }}-104
```

### 3.2 Referencias dentro de los procedimientos

```
{{ proyecto.codigo_documento_base }}-200  →  E-AR-001 (documento de Análisis de Riesgos)
{{ proyecto.codigo_documento_base }}-203  →  {{ proyecto.codigo_documento_base }}-221
{{ proyecto.codigo_documento_base }}-204  →  {{ proyecto.codigo_documento_base }}-204 (sin cambio)
{{ proyecto.codigo_documento_base }}-205  →  {{ proyecto.codigo_documento_base }}-231
{{ proyecto.codigo_documento_base }}-206  →  {{ proyecto.codigo_documento_base }}-203
{{ proyecto.codigo_documento_base }}-207  →  E-PF-001
{{ proyecto.codigo_documento_base }}-210  →  {{ proyecto.codigo_documento_base }}-207 / -208
{{ proyecto.codigo_documento_base }}-217  →  {{ proyecto.codigo_documento_base }}-217 (sin cambio)
{{ proyecto.codigo_documento_base }}-218  →  {{ proyecto.codigo_documento_base }}-205 / -206
{{ proyecto.codigo_documento_base }}-219  →  E-IT-001
{{ proyecto.codigo_documento_base }}-228  →  {{ proyecto.codigo_documento_base }}-204-A
{{ proyecto.codigo_documento_base }}-234  →  {{ proyecto.codigo_documento_base }}-218
```

### 3.3 Referencias en las plantillas comerciales (F3)

Los documentos P-001, C-001, C-003, E-001, E-040, E-050, E-400 referencian políticas y procedimientos por código. Todas las menciones deben actualizarse.

### 3.4 Referencias en el Motor 8 (G) y PLACSP Scraper (H)

Las referencias a `ens_measures_affected` en los findings del Motor 8 usan códigos del Anexo II del ENS (op.acc.4, mp.com.2, etc.) — estos NO cambian, son del RD 311/2022, no de nuestra numeración interna. Solo cambian las referencias a los documentos del SGSI interno.

---

## 4. INSTRUCCIONES PARA CLAUDE CODE — SCRIPT DE RENUMERACIÓN

```python
#!/usr/bin/env python3
"""
rename_sgsi_ids.py — Script de renumeración masiva de IDs de documentos SGSI.

Ejecutar ANTES de iniciar la construcción de FULKRO.
Lee todos los ficheros .md del plan 100/100 y aplica las sustituciones
de IDs conforme a la tabla de mapeo v2.1.

IMPORTANTE: ejecutar con --dry-run primero para verificar los cambios.
"""
import re
import sys
from pathlib import Path

# Tabla de mapeo: ID antiguo → ID nuevo
# Para políticas
POLICY_MAP = {
    # E-100 no cambia
    "E-101": "ABSORB_INTO_E100",  # Caso especial: absorber en E-100
    "E-102": "E-101",
    "E-103": "E-108",
    "E-104": "E-109",
    "E-105": "E-107",
    "E-106": "E-103",
    "E-107": "E-112",
    "E-108": "E-104",
}

# Para procedimientos
PROCEDURE_MAP = {
    "E-200": "E-AR-001",   # Sale de la serie E-2XX
    "E-203": "E-221",
    # E-204 no cambia
    "E-205": "E-231",
    "E-206": "E-203",
    "E-207": "E-PF-001",   # Sale de la serie E-2XX
    "E-210": "E-207",       # Primera parte (backup). E-208 para restore si se split.
    # E-217 no cambia
    "E-218": "E-205",       # Primera parte (vulns). E-206 para parches si se split.
    "E-219": "E-IT-001",   # Sale de la serie E-2XX
    "E-228": "E-204-A",    # Pasa a anexo forense del E-204
    "E-234": "E-218",
}

# Combinar ambos mapas
FULL_MAP = {**POLICY_MAP, **PROCEDURE_MAP}

# Patrones de referencia en los documentos Jinja2
# Los IDs aparecen como:
#   - {{ proyecto.codigo_documento_base }}-XXX
#   - POL-XXX
#   - E-XXX
#   - Documento E-XXX
#   - procedimiento E-XXX
PATTERNS = [
    # Jinja2 template references
    (r'\{\{ proyecto\.codigo_documento_base \}\}-(\d{3})', 
     lambda m: f'{{{{ proyecto.codigo_documento_base }}}}-{remap(m.group(1))}'),
    # Direct E-XXX references
    (r'\bE-(\d{3})\b', 
     lambda m: f'E-{remap(m.group(1))}'),
    # POL-XXX references
    (r'\bPOL-(\d{3})\b', 
     lambda m: f'POL-{remap(m.group(1))}'),
]


def remap(old_num: str) -> str:
    """Convierte un número de 3 dígitos al nuevo ID."""
    old_id = f"E-{old_num}"
    new_id = FULL_MAP.get(old_id)
    if new_id is None:
        return old_num  # No cambiar si no está en el mapa
    # Extraer solo la parte numérica del nuevo ID
    if new_id.startswith("E-") and new_id[2:].isdigit():
        return new_id[2:]
    # Para IDs especiales (E-AR-001, E-PF-001, etc.) mantener como está
    return new_id.replace("E-", "")


def process_file(filepath: Path, dry_run: bool = True) -> list[tuple[int, str, str]]:
    """
    Procesa un fichero y devuelve la lista de cambios.
    
    Returns:
        Lista de (línea, texto_original, texto_nuevo)
    """
    changes = []
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")
    
    for i, line in enumerate(lines):
        new_line = line
        for pattern, replacer in PATTERNS:
            new_line = re.sub(pattern, replacer, new_line)
        
        if new_line != line:
            changes.append((i + 1, line.strip(), new_line.strip()))
    
    if not dry_run and changes:
        new_content = "\n".join(
            re.sub(pattern, replacer, line) 
            for line in lines 
            for pattern, replacer in PATTERNS
        )
        # Simplified: apply all patterns sequentially
        new_content = content
        for pattern, replacer in PATTERNS:
            new_content = re.sub(pattern, replacer, new_content)
        filepath.write_text(new_content, encoding="utf-8")
    
    return changes


def main():
    dry_run = "--dry-run" in sys.argv
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else Path(".")
    
    md_files = sorted(target_dir.glob("**/*.md"))
    
    total_changes = 0
    for filepath in md_files:
        changes = process_file(filepath, dry_run=dry_run)
        if changes:
            print(f"\n{'[DRY RUN] ' if dry_run else ''}Fichero: {filepath}")
            for lineno, old, new in changes:
                print(f"  L{lineno}: {old}")
                print(f"      → {new}")
            total_changes += len(changes)
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Total: {total_changes} cambios en {len(md_files)} ficheros.")
    
    if dry_run:
        print("\nEjecuta sin --dry-run para aplicar los cambios.")


if __name__ == "__main__":
    main()
```

---

## 5. TABLA MAESTRA DEFINITIVA — DOCUMENTOS DEL SGSI FULKRO ALINEADOS CON v2.1

### 5.1 Políticas (27 documentos, v2.1 §2.6)

| ID v2.1 | Título | B | M | A | Estado |
|---|---|---|---|---|---|
| **E-100** | Política de Seguridad de la Información | ✓ | ✓ | ✓ | ✅ EXISTE (ampliar con sección Roles de E-101 antiguo) |
| **E-101** | Política de Control de Accesos | ✓ | ✓ | ✓ | ✅ EXISTE (renumerar desde E-102 antiguo) |
| **E-102** | Política de Contraseñas y Autenticación | ✓ | ✓ | ✓ | 🔲 CREAR (extraer de E-101 nuevo, sección contraseñas + MFA) |
| **E-103** | Política de Uso Aceptable de los recursos TI | ✓ | ✓ | ✓ | ✅ EXISTE (renumerar desde E-106 antiguo) |
| **E-104** | Política de Clasificación de la Información | ✓ | ✓ | ✓ | ✅ EXISTE (renumerar desde E-108 antiguo) |
| **E-105** | Política de Tratamiento de Datos Personales (RGPD) | ✓ | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-106** | Política de Copias de Seguridad | ✓ | ✓ | ✓ | 🔲 CREAR (extraer de E-109 nuevo) |
| **E-107** | Política Criptográfica | ✓ | ✓ | ✓ | ✅ EXISTE (renumerar desde E-105 antiguo) |
| **E-108** | Política de Gestión de Incidentes | ✓ | ✓ | ✓ | ✅ EXISTE (renumerar desde E-103 antiguo) |
| **E-109** | Política de Continuidad de Negocio | p | ✓ | ✓ | ✅ EXISTE (renumerar desde E-104 antiguo) |
| **E-110** | Política de Teletrabajo y Movilidad | ✓ | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-111** | Política de Uso de Servicios Cloud | ✓ | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-112** | Política de Gestión de Proveedores | ✓ | ✓ | ✓ | ✅ EXISTE (renumerar desde E-107 antiguo) |
| **E-113** | Política de Adquisición de Tecnología | ✓ | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-114** | Política de Desarrollo Seguro (SSDLC) | – | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-115** | Política de Gestión de Vulnerabilidades | – | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-116** | Política de Gestión de Cambios | ✓ | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-117** | Política de Gestión de Privilegios y PAM | – | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-118** | Política de BYOD | si | si | si | 🔲 CREAR NUEVA (condicional) |
| **E-119** | Política de Respuesta a Brechas de Datos Personales | ✓ | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-120** | Política de Gestión de Claves Criptográficas | – | p | ✓ | 🔲 CREAR (ampliar de E-107 nuevo) |
| **E-121** | Política de Redes y Comunicaciones | ✓ | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-122** | Política de Gestión de Soportes | ✓ | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-123** | Política de Seguridad Física | ✓ | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-124** | Política de Seguridad del Personal | ✓ | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-125** | Política de Mesa Limpia y Pantalla Limpia | ✓ | ✓ | ✓ | 🔲 CREAR NUEVA |
| **E-126** | Política de Borrado Seguro y Destrucción | ✓ | ✓ | ✓ | 🔲 CREAR NUEVA |

**Resumen: 8 EXISTEN (renumerar) + 19 POR CREAR**

*(Nota: son 19 en lugar de 18 porque el antiguo E-101 "Roles" se absorbe en E-100 y libera un slot, pero E-102 "Contraseñas" es nueva.)*

### 5.2 Procedimientos (35 documentos, v2.1 §2.7)

| ID v2.1 | Título | Estado |
|---|---|---|
| **E-200** | Alta de personal (técnico y lógico) | 🔲 CREAR NUEVA |
| **E-201** | Baja de personal | 🔲 CREAR NUEVA |
| **E-202** | Cambio de rol | 🔲 CREAR NUEVA |
| **E-203** | Gestión de cambios técnicos (con CAB) | ✅ EXISTE (renumerar desde E-206 antiguo) |
| **E-204** | Gestión de incidentes | ✅ EXISTE (sin cambio de ID) |
| **E-205** | Gestión de vulnerabilidades | ✅ PARCIAL (renumerar desde E-218 antiguo, separar parches) |
| **E-206** | Aplicación de parches | 🔲 CREAR (split de E-218 antiguo) |
| **E-207** | Copias de seguridad | ✅ PARCIAL (renumerar desde E-210 antiguo, separar restore) |
| **E-208** | Restauración (con pruebas periódicas) | 🔲 CREAR (split de E-210 antiguo) |
| **E-209** | Pruebas de continuidad | 🔲 CREAR NUEVA |
| **E-210** | Revisión periódica de accesos | 🔲 CREAR (extraer de E-231 sección 6) |
| **E-211** | Gestión de cuentas privilegiadas | 🔲 CREAR (extraer de E-231 secciones 8-9) |
| **E-212** | Respuesta a brechas RGPD | 🔲 CREAR NUEVA |
| **E-213** | Notificación de brechas a la AEPD | 🔲 CREAR NUEVA |
| **E-214** | Destrucción segura de información | 🔲 CREAR NUEVA |
| **E-215** | Gestión de soportes extraíbles | 🔲 CREAR NUEVA |
| **E-216** | Gestión de proveedores | 🔲 CREAR (operativo de E-112) |
| **E-217** | Evaluación de riesgos de proveedores | ✅ EXISTE (sin cambio de ID) |
| **E-218** | Auditoría interna | ✅ EXISTE (renumerar desde E-234 antiguo) |
| **E-219** | Revisión por la dirección | 🔲 CREAR NUEVA |
| **E-220** | Gestión de no conformidades | 🔲 CREAR NUEVA |
| **E-221** | Gestión documental | ✅ EXISTE (renumerar desde E-203 antiguo) |
| **E-222** | Gestión de excepciones | 🔲 CREAR NUEVA |
| **E-223** | Revisión de logs | 🔲 CREAR NUEVA |
| **E-224** | Despliegue de software (SSDLC operativo) | 🔲 CREAR NUEVA |
| **E-225** | Pruebas pre-producción | 🔲 CREAR NUEVA |
| **E-226** | Teletrabajo | 🔲 CREAR NUEVA |
| **E-227** | Uso de cloud | 🔲 CREAR NUEVA |
| **E-228** | Respuesta ante pérdida o robo de dispositivos | 🔲 CREAR NUEVA |
| **E-229** | Visitas externas | 🔲 CREAR NUEVA |
| **E-230** | Categorización de sistemas | 🔲 CREAR NUEVA |
| **E-231** | Gestión de identidades | ✅ EXISTE (renumerar desde E-205 antiguo) |
| **E-232** | Gestión criptográfica | 🔲 CREAR NUEVA |
| **E-233** | Notificación a LUCIA | 🔲 CREAR NUEVA |
| **E-234** | Proceso de autorización (org.4) | 🔲 CREAR NUEVA |

**Resumen: 8 EXISTEN (renumerar, 2 requieren split) + 27 POR CREAR**

### 5.3 Documentos adicionales que salen de la serie E-2XX

| ID nuevo | Título | Origen |
|---|---|---|
| E-AR-001 | Análisis y Gestión de Riesgos (MAGERIT v3) | Renumerado desde E-200 antiguo |
| E-PF-001 | Plan de Formación y Concienciación | Renumerado desde E-207 antiguo |
| E-IT-001 | Instrucción Técnica de Hardening | Renumerado desde E-219 antiguo |
| E-204-A | Anexo Forense del Procedimiento de Incidentes | Renumerado desde E-228 antiguo |

---

## 6. TRABAJO PENDIENTE TOTAL TRAS LA CORRECCIÓN 1

| Corrección | Documentos afectados | Tipo de trabajo |
|---|---|---|
| **C-1 Renumeración** | 8 políticas + 8 procedimientos + 4 docs adicionales + todas las refs cruzadas | Renumerar IDs, actualizar refs en F3/G/H/I |
| **C-2 Motor 8** | Entregable G completo | Rediseñar pipeline 11 fases, añadir ~12 adaptadores críticos |
| **C-3 Cláusula Recursos** | C-001 en F3.1 | Añadir cláusula 5bis con texto legal |
| **C-4 Effort Estimator** | D+E | Actualizar horas base a 60/150/230 |
| **C-5 Políticas nuevas** | 19 políticas nuevas | Redacción legal real en español |
| **C-6 Procedimientos nuevos** | 27 procedimientos nuevos | Redacción operativa real |
| **C-7 Plantillas comerciales** | 8 plantillas del Apéndice F | Reunión exploratoria, negociación, kick-off, etc. |
| **C-8 Agentes 17-20** | 4 system prompts | Prompts para cualificación, reunión, propuesta, negociación |

**DECISIÓN REQUERIDA DE MARCOS:**

¿Procedo en el siguiente orden?

1. **Ahora mismo:** Generar las 19 políticas nuevas (el bloque más pesado) con numeración v2.1 correcta.
2. **Después:** Generar los 27 procedimientos nuevos.
3. **Después:** Motor 8 ampliado + C-001 cláusula + Effort Estimator + plantillas + agentes.

O prefieres otro orden. Lo que tengo claro es que las políticas y procedimientos son el cuello de botella — son ~46 documentos con texto legal real en español que hay que redactar. Los otros (Motor 8, cláusula, estimator, plantillas, agentes) son más cortos individualmente.
