# FULKRO Acta E-012 v1 — JSON Schema

## Resumen

Esquema JSON propio de FULKRO para la exportacion estructurada del Acta de
Categorizacion del Sistema (E-012) conforme al RD 311/2022 Anexo I.

**ADVERTENCIA:** Este NO es un formato oficial publicado por el CCN-CERT ni
definido en ningun RD, ITS o guia CCN-STIC. Tras investigacion exhaustiva
(B6.6.1), se confirmo que no existe estandar oficial de intercambio para el
E-012. El RD 311/2022 lo define como documento PDF firmado por el RSEG.
Las herramientas del CCN (AMPARO, EVENS, MARGA) no tienen API documentada.

Este esquema es una convencion FULKRO para uso interno, interoperabilidad
futura, y automatizacion del pipeline ENS.

## Versionado

- `schema_version` sigue versionado semantico: MAJOR.MINOR
- MAJOR: cambio breaking (campos obligatorios anadidos/eliminados, renombrados)
- MINOR: campos opcionales anadidos, mejoras de documentacion
- Version actual: **1.0**

## Campos

| Campo | Tipo | Obligatorio | Descripcion |
|---|---|---|---|
| `schema` | string | Si | Siempre `"fulkro.acta_e012"` |
| `schema_version` | string | Si | Siempre `"1.0"` |
| `document_id` | string | Si | Siempre `"E-012"` |
| `generated_at` | string (ISO 8601) | Si | Timestamp UTC de generacion |
| `act.version` | int | Si | Numero de version de la categorizacion (auto-incremental por sistema) |
| `act.fecha_acta` | string (ISO 8601 date) | Si | Fecha del acta |
| `act.approved_by` | string o null | No | Nombre del aprobador |
| `client.nombre` | string | Si | Nombre del cliente |
| `client.cif` | string | Si | CIF del cliente |
| `project.id` | string (UUID) | Si | ID del proyecto |
| `project.nombre` | string | Si | Nombre del proyecto |
| `system.id` | string (UUID) | Si | ID del sistema categorizado |
| `system.nombre` | string | Si | Nombre del sistema |
| `system.descripcion` | string o null | No | Descripcion del sistema |
| `information_types` | array | Si | Lista de tipos de informacion con valoraciones DICAT |
| `information_types[].nombre` | string | Si | Nombre del tipo de informacion |
| `information_types[].valoraciones` | object | Si | {D, I, C, A, T} con valores BAJO/MEDIO/ALTO |
| `services` | array | Si | Lista de servicios con valoraciones DICAT |
| `services[].nombre` | string | Si | Nombre del servicio |
| `services[].valoraciones` | object | Si | {D, I, C, A, T} con valores BAJO/MEDIO/ALTO |
| `result.dimensiones` | object | Si | Resultado maximo por dimension {D, I, C, A, T} |
| `result.categoria_final` | string | Si | BASICA, MEDIA o ALTA |
| `result.determining_dimension` | string | Si | Dimension que determino la categoria (D/I/C/A/T) |
| `justificacion` | string | Si | Texto justificativo del resultado |
| `normative_basis.primary` | string | Si | Normativa principal aplicada |
| `normative_basis.guides` | array[string] | Si | Guias CCN-STIC aplicadas |

## Compatibilidad oficial

Cuando el CCN publique un formato oficial de intercambio para el E-012
(si lo hace), FULKRO anadira un convertidor adicional manteniendo este
formato propio para uso interno. El convertidor sera un endpoint separado
(e.g. GET /acta-e012.ccn) que transforme el esquema FULKRO al oficial.
