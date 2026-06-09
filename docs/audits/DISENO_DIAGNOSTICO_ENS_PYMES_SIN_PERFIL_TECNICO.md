# Diseño del diagnóstico ENS para PYMEs sin perfil técnico

> **Estado**: DECISIÓN DE DISEÑO CERRADA (Marcos · 2026-06-03). Spec normativa para el punto
> #6 del Plan Maestro de los 45 puntos. Este documento manda sobre la ficha #6 original cuando
> haya contradicción.

## El principio

El diagnóstico organizativo ENS (motor m21) **NO asume que el cliente tenga un CTO o un DPO**.
El target real son PYMEs que licitan a la AAPP y muchas veces **no tienen perfil técnico interno**.
Por tanto:

- **Los roles técnicos (CTO, DPO, RSeg) son un BONUS, no un requisito.**
- **El diagnóstico debe funcionar entero sin ellos.** Si solo hay un sponsor no técnico, el
  diagnóstico tiene que producir un resultado válido igualmente.

## Principio grabado · MADUREZ ≠ CONFORMIDAD

El scoring de madurez (motor m21 · `maturity_service`) mide **MADUREZ**, para **dimensionar el
proyecto/propuesta**. La **CONFORMIDAD** la determina la **SoA** (`dda_entries`) contra las
medidas **obligatorias del nivel ENS** — NO este score. Son dos planos distintos:

- Un cliente puede ser **"maduro" y no "conforme"**. Ej.: `mfa=solo_empleados` puntúa **+2 en
  madurez**, pero en **ENS Alta** el MFA es obligatorio para **todos** (externos incluidos) → no
  basta para **conformidad** Alta aunque sume en madurez.
- **No mezclar los planos** ni en código ni en UI: el diagnóstico de madurez **no debe
  presentarse como conformidad**. (Documentado en el docstring de `maturity_service.py`.)
- Corolario (criterio Marcos): un valor **"no obligatorio"** (p.ej. DPO en una PYME que
  legalmente no lo necesita) es **neutro** — ni puntúa ni cuenta como carencia/rojo. No penaliza
  la madurez ni se pinta como déficit.

## De dónde sale la información técnica del diagnóstico (las dos fuentes canónicas)

La madurez técnica y la cobertura ENS NO se obtienen exigiendo al cliente que rellene
cuestionarios técnicos profundos (`ti_cto`, `legal_dpo`). Se obtienen de:

1. **Discovery del cloud conectado del cliente** (m_cloud_connectors). El cliente conecta su
   M365/Google/AWS por OAuth read-only (ADR-014) durante el onboarding, y el sistema **descubre**
   la realidad técnica (MFA, identidades, retención de logs, buckets, etc.) sin que nadie teclee
   nada técnico. → **Depende de #18** (cloud sync real; hoy trae 0 recursos).

2. **El copiloto preguntando en lenguaje LLANO** (m11), dentro del onboarding. El copiloto
   traduce lo que falta a preguntas que entiende cualquiera ("¿cuando entras a tu correo te pide
   un código del móvil?") y deriva de ahí la señal técnica. → **Depende de #22** (copiloto
   proactivo).

El **cuestionario comercial del lead** (`onb-precliente-sponsor-v1`, 17 preguntas) sigue siendo
**captura de contexto comercial** (CIF, papel frente a la AAPP, plazo, dolor) — NO un input
técnico del diagnóstico. Su rol es alimentar la cadena comercial (lead → proyecto → contrato,
puntos #7/#9/#10), no el scoring de madurez.

## Consecuencia de orden (por qué #6 NO se cierra entero ahora)

El #6 "completo" (diagnóstico nutrido de cloud + copiloto, funcionando para una PYME sin perfil
técnico) **depende de sus cimientos**:

- **#18** — cloud sync real (hoy `m_cloud_connectors` pasa `m16_credentials=None` → descubre 0).
- **#22** — copiloto proactivo (hoy reacciona al abrir, no empuja ni pregunta lo que falta).

Ambos son **olas posteriores**. Por tanto:

> **Estado del punto #6**: **diseño cerrado + drift de keys arreglado** (esta sesión).
> **Cableado cloud+copiloto → diagnóstico: PENDIENTE de #18 + #22.**

## Lo que el repo ya hace HOY (estado verificado, audit-first 2026-06-03)

- `run_diagnosis` ([m21_diagnosis/service.py:24-63](../../backend/app/motors/m21_diagnosis/service.py))
  orquesta 4 dimensiones por `project_id`: stakeholder + process (derivan del grafo PKG) y
  compliance + maturity (**ya leen `OnboardingResponse`** por `project_id` + `estado=COMPLETED`).
- El catálogo de madurez (`SCORING_RULES`) y de compliance (`SECTOR_NORMATIVAS`) es determinista,
  hardcoded, no-LLM.
- **Hueco técnico real** (lo que cubrirán #18+#22): hoy el scoring depende de que alguien rellene
  los cuestionarios técnicos `ti_cto`/`legal_dpo`; cuando el cliente no tiene CTO/DPO, esas
  respuestas no existen y la madurez sale artificialmente baja. La fuente cloud+copiloto sustituye
  esa dependencia.
- **Bug latente independiente** (se arregla esta sesión · ver
  [AUDIT_PUNTO_6_DRIFT_SCORING_RULES.md](AUDIT_PUNTO_6_DRIFT_SCORING_RULES.md)): aunque alguien
  rellene los cuestionarios técnicos, las `SCORING_RULES` esperan keys/valores que solo coinciden
  con 1-2 sectores → casi ninguna regla puntúa. Drift de vocabulario regla↔template.

## Coherencia a respetar (reglas de oro)

- ADR-014: el discovery cloud es **read-only**; nunca escribe al cloud del cliente.
- El diagnóstico se ancla en `project_id` (no en lead/cif); la traza lead→proyecto es el #7.
- Determinismo del scoring (R1): madurez/compliance siguen siendo reglas deterministas; el
  copiloto/LLM aporta señal de entrada en lenguaje llano, no decide la categoría.
- Cliente-mínimo: nunca se exige jerga ni perfil técnico al cliente para diagnosticar.
