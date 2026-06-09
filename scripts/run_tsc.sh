#!/bin/bash
# Dev helper · run tsc with sane PATH (escapes WSL Windows-PATH parens).
PATH=/home/usuario/.nvm/versions/node/v20.20.2/bin:/usr/bin:/bin
export PATH
cd /home/usuario/fulkro/frontend || exit 1
exec /home/usuario/.nvm/versions/node/v20.20.2/bin/npx tsc --noEmit "$@"
