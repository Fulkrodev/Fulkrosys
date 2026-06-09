# ADR: Estrategia de ingesta de datos con LLM+RAG en FULKRO

## Status
Accepted (strategic) — 2026-04-13
Implementation deferred to Motor 11 (Copiloto IA)

## Context

Los consultores ENS reciben datos de clientes en formatos heterogeneos:
exports de CMDB (Excel/CSV), inventarios de Active Directory, catalogos
de sistemas en formatos propietarios. Cada cliente estructura sus datos
de forma distinta con columnas variables, valores inconsistentes, y
categorias propias que no mapean directamente a MAGERIT.

Las herramientas competidoras (GlobalSuite, PILAR, eMAS) exigen
normalizacion manual antes de importar, anadiendo horas de trabajo.

## Decision

**Toda ingesta masiva de datos en FULKRO debe pasar por capa LLM+RAG
inteligente** que:

1. Interprete semanticamente las columnas del fichero del cliente
2. Limpie y normalice valores usando corpus RAG (MAGERIT, CCN-STIC)
3. Infiera valores faltantes cuando el contexto lo permite
4. Importe filas parciales reportando invalidas con explicacion

## Alternativas LLM (decision pendiente Motor 11)

- **Opcion alfa:** LLM remoto (Claude API) — maxima calidad, datos salen
- **Opcion beta:** LLM local (Llama/Qwen via ollama) — soberania datos
- **Opcion gamma:** Hybrid — local por defecto, remoto si cliente acepta

## Implementation roadmap

**Fase 1 — HOY (Motor 2, C3):** Importador determinista CSV+XLSX con
mapping fijo. Base tecnica de parseo, validacion y commit atomico.

**Fase 2 — Motor 11 (Copiloto IA):** Capa LLM+RAG sobre el importador
determinista. El parser determinista se convierte en fallback strict-mode.

**Fase 3 — Extension:** Todos los motores con ingesta masiva heredan
la capa LLM+RAG del Motor 11.

## References

- Motor 11 roadmap: ver master spec
- Corpus RAG: 6438 chunks en knowledge_chunks
- Motor 2 importador: service.py import_assets_from_csv/xlsx
