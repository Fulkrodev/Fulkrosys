# ADR: PKG-lite (SQL) vs Apache AGE (graph database)

## Fecha: 2026-04-16
## Estado: Aprobado
## Contexto

El spec v2.1 sec 3.2 prescribe Apache AGE para el Project Knowledge Graph.
El PKG almacena stakeholders, activos, procesos, informacion, sistemas,
proveedores, identidades, y sus relaciones por proyecto cliente.

## Opciones evaluadas

### Opcion A — Apache AGE
- Pro: Cypher queries nativas para traversals complejos
- Con: requiere extension PG adicional (conflicto con pgvector)
- Con: imagen Docker custom necesaria
- Con: queries reales que necesitamos son simples (1-2 hops)

### Opcion B — PKG-lite con tablas SQL (ELEGIDA)
- Pro: zero dependencias adicionales
- Pro: SQLAlchemy nativo, tests estandar
- Pro: JSONB properties da flexibilidad equivalente a property graph
- Pro: migracion a AGE posible sin cambiar API del PKGService

## Decision

Opcion B — PKG-lite. PKGService abstrae el storage. Si la complejidad
justifica AGE en el futuro, se migra sin cambiar consumidores.

## Consecuencias

- Tablas pkg_nodes + pkg_edges con JSONB properties
- PKGService como unica API de acceso
- Traversals limitados a ~3 hops con SQL (suficiente para ENS)
- TODO-PKG-AGE-MIGRATION si se necesita
