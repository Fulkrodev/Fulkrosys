# Trazabilidad Motor 2 (MAGERIT) — fuente oficial

## Resumen

Las 57 amenazas del catalogo del Motor 2 (`magerit_threats`) estan trazadas al
**MAGERIT v3.0 Libro II - Catalogo de Elementos** (NIPO 630-12-171-8), publicado por el
Ministerio de Hacienda y Administraciones Publicas en octubre de 2012.

**Fuente oficial**:
- Titulo: MAGERIT v3.0 Libro II - Catalogo de Elementos
- Autores: Miguel Angel Amutio Gomez (MINHAP), Javier Candau (CCN), Jose Antonio Manas (UPM)
- NIPO: 630-12-171-8

## Estructura verificada

| Familia | Descripcion | Cantidad |
|---------|-------------|----------|
| [N] Desastres naturales | N.1, N.2, N.* | 3 |
| [I] De origen industrial | I.1 a I.11 + I.* | 12 |
| [E] Errores no intencionados | E.1-E.28 (18 codigos) | 18 |
| [A] Ataques intencionados | A.3-A.30 (24 codigos) | 24 |
| **Total** | | **57** |

## Politica de descripcion dual

Cada amenaza tiene dos descripciones mantenidas conscientemente:

- **`description`**: version resumida (1-2 lineas), para UI del motor y busquedas.
- **`official_description`**: version literal del Libro II oficial, para auditoria ENAC.

El service del Motor 2 usa `description` por defecto. Los exports para auditoria
incluyen `official_description` cuando el cliente lo requiere.

## Diferencias editoriales en nombres (mantenidas)

15 variantes de redaccion editorial detectadas en cross-check. Se mantienen las
versiones del Motor 2 por mayor claridad moderna (ej: "DoS" incluido, corchetes
eliminados, articulos simplificados).

## Validacion cross-check (2026-04-13)

Script: `scripts/crosscheck_magerit_libro2.py`
- Codigos comunes: 57/57 (100%)
- Grupos N/I/E/A identicos: 57/57 (100%)
- Nombres identicos: 42/57 (74%, 15 variantes editoriales)

## TODOs futuros

- TODO-M2-REF-1 [BAJA]: Tipos de activos raiz del Libro II cap 2
- TODO-M2-REF-2 [BAJA]: Definiciones formales 5 dimensiones DICAT
- TODO-M2-REF-3 [MEDIA]: Grounding LLM con official_description (Motor 11)
