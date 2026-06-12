# SIMULACIONES HIPERREALISTAS ENS — BÁSICA / MEDIA / ALTA (2026-06-12)

> Criterio de aceptación del usuario: probar el sistema **ejecutándolo de verdad**,
> caso a caso, lado admin **y** cliente (+ auditor en MEDIA), end-to-end, encontrando
> y **corrigiendo** cualquier defecto que impida que los resultados sean perfectos,
> y **documentándolo por escrito**. EXCEPTO el pentest externo OSCP (omitido).

## Metodología

- **API-e2e in-process** (httpx ASGITransport contra la app real + servicios reales
  + BD `fulkro_test` con RLS enforced). Esto **esquiva el bucle de login del portal
  cliente** (OPS-052 72ª · desajuste de clave JWT efímera del front) ejercitando el
  backend real sin navegador, tal y como autorizó el usuario.
- Cada simulación siembra un cliente/proyecto realista (Ayuntamiento de Villaverde
  del Río), recorre el ciclo de implantación, **vuelca cada entregable** a
  `out/sim_<cat>/` para revisarlo como auditor, y **asegura invariantes** (un
  defecto en el output rompe la simulación).
- Drivers: `backend/tests/integration/test_sim_{basica,media,alta}.py`.
- **Verificación empírica contra el código/BD reales, nunca contra los tests** (los
  2 bugs de prod de abajo se cazaron así: un test verde los ocultaba).

## Defectos REALES de producción encontrados y corregidos

Hallados ejecutando el ciclo, no contra los tests:

1. **`build_informe_final_context` (E-040) abortaba la transacción** → la generación
   del E-040 (el entregable estrella que el auditor abre primero) fallaba con
   `transaction aborted`. Causa: la query de tratamiento MAGERIT seleccionaba
   `status` sin cualificar y `status` existe **tanto en `magerit_treatment_plan`
   como en `magerit_analysis`** → `column reference "status" is ambiguous`. El
   `except` best-effort lo tragaba con `logger.debug` (silencioso) pero dejaba la
   transacción envenenada. **Fix:** cualificar `tp.treatment` / `tp.status`.
   *(commit `8ee355bc`)*
2. **E-040 no se podía emitir** (`MissingPlaceholderError: cliente.nif,
   cliente.domicilio_social`): el catálogo del E-040 los exige `required` pero el
   builder solo aportaba `razon_social`. **Fix:** leer `clients.cif` → `nif` y
   `clients.domicilio_fiscal` → `domicilio_social`. *(commit `8ee355bc`)*

Ambos afectaban a CUALQUIER proyecto real. 726 tests m06/m03/e040 verdes tras el fix.

## Simulación 1 · BÁSICA (autodeclaración CCN-STIC 809)

**Flujo (admin + cliente):** alta cliente+proyecto (Ayuntamiento, sede electrónica,
5 roles ENS) → categorización DICAT (todo BAJO → **BÁSICA**) → DdA/SoA (49 medidas
aplica estrictas / 52 incl. refuerzos del Anexo II) congelada y aprobada por RSEG →
entregables (E-040 Informe Final, E-160 Manual SGSI, E-170 Plan Director) →
conformidad ruta declaración → **distintivo de Conformidad CCN-STIC 809** → cierre.
(BÁSICA: sin auditor externo.)

**Resultados empíricos:**
- E-040 renderiza con **cumplimiento global real 94,2 %**, fechas reales del
  proyecto, sin fugas Jinja, con la SoA (Anexo II) embebida.
- Distintivo: dice explícitamente *«Distintivo de Conformidad con el ENS (CCN-STIC
  809) · Autoevaluación de categoría BÁSICA»* y que la categoría BÁSICA se acredita
  por autoevaluación, **sin certificación por entidad acreditada** (regla de
  nomenclatura del usuario respetada).
- E-160/E-170: firmantes (RSEG/Dirección) poblados.
- **Defecto de simulación corregido:** se marcaban las medidas con el valor
  `'implementada'` (la BD usa `'implantada'`) → el E-040 salía 0,0 %; corregido →
  94,2 %.

## Simulación 2 · MEDIA (ruta certificación ENAC + AUDITOR)

**Flujo:** alta + DICAT (un MEDIO → **MEDIA**) → DdA **68 medidas aplicables** →
E-040 (**100 %**) → **No Conformidad de auditoría externa** (E-321 AENOR + E-322
hallazgo) **promovida a `AuditFinding` estructurado** (severidad *mayor* · op.exp.8 ·
PAC con fecha de compromiso · 0 violaciones del plazo ≤90 días) → ruta certificación
→ **distintivo CCN-STIC 809** + **slot del certificado de la entidad acreditada**
(PDF adjuntado · FULKRO nunca lo emite) → **PORTAL DEL AUDITOR ENAC**.

**Portal del auditor (magic-link AUDITOR_PORTAL_ENAC · httpx):**
- `GET /summary` → **200** · cliente (Ayuntamiento, CIF P4109500A) + proyecto MEDIA +
  counts (DdA 73 entradas).
- `GET /dda` → **200** · el auditor revisa la Declaración de Aplicabilidad.
- `GET /audit-log` → **200** · cadena de auditoría.
- Aislamiento RLS respetado (el portal queda ligado al proyecto del token).

**Resultados:** DdA 68 (coincide con el canónico MEDIA del BOE), E-040 100 %, NC
estructurada correcta, distintivo MEDIA dice *«no sustituye al certificado de la
entidad de certificación acreditada»*. Sin defectos nuevos.

## Simulación 3 · ALTA (ruta ENAC + continuidad op.cont.*)

**Flujo:** alta + DICAT (D y C en ALTO → **ALTA**) → DdA **73 aplicables + 38 con
refuerzos (+R)** → E-040 (**100 %**) → **CONTINUIDAD** (E-400 BIA / E-401 Estrategias
/ E-403 DRP) con RTO/RPO reales desde `bia_analyses` → distintivo CCN-STIC 809.

**Resultados empíricos:**
- E-400 BIA: inventario de procesos críticos (P-001 Registro de entrada/salida ALTO;
  P-002 Tramitación electrónica **CRÍTICO**), RTO/RPO (4 h / 1 h), análisis temporal
  de impacto — todo poblado (las tablas-loop ya no colapsan tras R20).
- E-401 Estrategias: estrategia por banda de RTO (RTO≤4h → «Redundancia activa»).
- E-403 DRP: sistemas críticos + sitio primario/secundario.
- Distintivo ALTA: igual que MEDIA, acompaña pero **no sustituye** al certificado ENAC.
- Refuerzos (+R): 38 medidas con refuerzos aflorando para ALTA.

## Revisión como AUDITOR ENAC — veredicto

- **E-040** (lo que el auditor abre primero): cumplimiento por familia + global real,
  alcance, categorización, análisis de riesgos, SoA Anexo II, sin huecos ni fugas.
- **Distintivo/Certificado**: separación de nomenclatura impecable (distintivo 809 que
  publica la entidad vs certificado de la entidad acreditada que FULKRO nunca emite).
- **NC**: trazables y estructuradas (severidad + PAC + plazos), promovidas desde el
  registro vivo WORM.
- **Portal del auditor**: read-only, gated por magic-link, aislado por proyecto.
- **Continuidad ALTA**: BIA/Estrategias/DRP con datos reales (no plantillas vacías).

## Estado

- 3 drivers de simulación verdes · 2 bugs reales de prod corregidos · entregables
  volcados en `out/sim_{basica,media,alta}/`.
- Pendiente honesto (no defecto · mejora de realismo): sembrar evidencias (m07) +
  análisis MAGERIT para que los counts del portal y el inventario de activos del
  distintivo dejen de ser 0; lectura IA de documentos subidos por el cliente (no
  existe aún · construir como feature dedicada · ver PROGRESO doc).
