#!/bin/bash
# Dev helper · run tsc with sane PATH (escapes WSL Windows-PATH parens).
# NOTA W9-2: la ruta nvm (node v20.20.2) se mantiene hardcodeada a propósito —
# es el workaround para escapar los paréntesis del PATH de Windows en WSL; no es
# trivialmente parametrizable sin perder ese efecto. Sólo el `cd` se hace
# relativo al script (scripts/ → ../frontend).
PATH=/home/usuario/.nvm/versions/node/v20.20.2/bin:/usr/bin:/bin
export PATH
cd "$(dirname "${BASH_SOURCE[0]}")/../frontend" || exit 1
exec /home/usuario/.nvm/versions/node/v20.20.2/bin/npx tsc --noEmit "$@"
