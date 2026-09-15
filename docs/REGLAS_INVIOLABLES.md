# Las ocho reglas inviolables

Son las reglas que el código cita por su número (`R1`, `R5`…) en comentarios y
docstrings. Vivían en `CLAUDE.md`, que **se retiró del repositorio** el
2026-09-15 por el motivo que se explica al final. Esto es lo que se ha salvado
de aquel fichero: sólo las reglas, y sólo después de comprobar una a una que lo
que afirman sigue siendo cierto.

**Cada cifra de esta página está medida hoy y lleva el comando que la reproduce.**
Ésa es la diferencia con el fichero del que salen.

---

| | regla | estado comprobado |
|---|---|---|
| **R1** | Motores deterministas por encima del LLM para decisiones normativas. La trazabilidad ante ENAC pesa más que la flexibilidad del modelo | vigente · es criterio de diseño, no una cifra |
| **R2** | Citas obligatorias en toda respuesta del LLM: RD 311/2022, CCN-STIC, Anexo II, ISO | vigente |
| **R3** | Temperatura del LLM ≤ 0,2 | **comprobado: 0,15** |
| **R4** | WebAuthn (Yubikey) como único método en producción · en desarrollo hay sesión de respaldo por `APP_ENV` | vigente · ver [ADR-003](adr/README.md) |
| **R5** | Magic links Ed25519 EC P-256 para clientes, sin cuentas permanentes | **corregido: 37 propósitos, no 23** |
| **R6** | Registro de auditoría inmutable con cadena de hashes (trigger PL/pgSQL) | **comprobado**, migración `d4f8b2a90001` |
| **R7** | La plataforma cumple ENS Medio sobre sí misma (dogfooding) | objetivo declarado, no una medición |
| **R8** | Copia de seguridad probada mensualmente (Motor 26) | procedimiento declarado |

Comandos:

```bash
# R3 · la temperatura por defecto de todos los agentes
grep -n "TEMPERATURE" backend/app/agents/base.py        # TEMPERATURE: float = 0.15

# R5 · cuántos propósitos de magic-link hay de verdad
python3 -c "import sys; sys.path.insert(0,'.'); \
  from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose; \
  print(len(list(MagicLinkPurpose)))"                   # 37

# R6 · la migración que instala el trigger de la cadena de hashes
ls backend/migrations/versions/d4f8b2a90001*
```

> **R5 decía «23 propósitos» y son 37.** La cifra estaba equivocada en el fichero
> original, y estaba en la sección titulada «Reglas inviolables» — la parte que
> uno daría por buena sin comprobar. Es la razón por la que esta página no
> reproduce ninguna otra cifra de aquel fichero.

---

## Por qué se retiró `CLAUDE.md`

Era el fichero al que el README mandaba como especificación canónica, y **ninguna
de sus referencias comprobables resolvía**. Medido el 2026-09-15 sobre el árbol
publicado:

| lo que citaba | cuántas | cuántas resuelven |
|---|---:|---:|
| Etiquetas de git | 13 | **0** |
| Hashes de commit | 16 | **0** |
| Documentos enlazados | 23 | 2 |

Y sus cifras de estado tampoco: decía ~353 ficheros `test_*.py` (son **625**),
160 migraciones (son **273**), 52 modelos ORM (son **63**) y 42 motores (son
**44** bajo `m*/`). Ninguna desviación era menor del 5 %; varias pasaban del 70 %.

```bash
find backend/tests -name 'test_*.py' | wc -l      # 625
ls backend/migrations/versions/*.py | wc -l       # 273
ls backend/app/models/*.py | wc -l                # 63
ls -d backend/app/motors/m*/ | wc -l              # 44
git tag | wc -l                                   # 0
```

El historial de este repositorio se rehízo como snapshot limpio el 2026-06-09, y
la documentación viajó intacta desde otra vida del proyecto: por eso las
etiquetas y los commits que cita no existen aquí. No es que el trabajo que
describe no ocurriera — es que **su cadena de evidencia no es verificable en el
repositorio publicado**, y un lector que comprueba dos punteros y falla en los
dos extiende, con razón, la sospecha al resto.

Un documento así no resta credibilidad por lo que dice, sino por lo que un
lector descubre cuando intenta comprobarlo. Por eso no se ha movido a otra
carpeta: se ha dejado de publicar. Sigue en la máquina, fuera del control de
versiones, en `.claude/`.

**Dónde está ahora lo que aquel fichero intentaba ser:**

- Cómo está construido el sistema y dónde están los límites → [`ARCHITECTURE.md`](../ARCHITECTURE.md)
- Las decisiones, con su fuente comprobada → [`docs/adr/`](adr/) y [`docs/architecture/`](architecture/)
- Qué hace cada motor → el `README.md` de cada uno, bajo `backend/app/motors/`
- Qué se puede afirmar de los tests y qué no → [`README.md`](../README.md)
