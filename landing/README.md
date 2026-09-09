# Web publica de Fulkro (`fulkro.es`)

Sitio **estatico** de Fulkro, conservado como archivo. El proyecto cerro en
septiembre de 2026: la web ya no vende nada ni ofrece ningun servicio, solo
describe lo que hacia la plataforma. El codigo del sistema se esta liberando
como open source en <https://github.com/Fulkrodev/Fulkrosys>.

Es independiente de la aplicacion (`backend/` + `frontend/`): aqui no hay build
ni framework, solo HTML/CSS/JS plano. Cada pagina es **autocontenida** (CSS y JS
en linea), asi que se puede abrir o desplegar sin pasos previos.

## Estructura

```
landing/
├── index.html            # Portada: que era y que hacia la plataforma
├── aviso-legal.html      # Aviso legal
├── privacidad.html       # Politica de privacidad
├── cookies.html          # Politica de cookies
├── assets/               # Capturas del producto usadas en la portada
├── og-image.png          # Imagen para compartir (1200×630)
├── favicon.svg
├── robots.txt            # Sin allowlist de crawlers de IA: no hay nada que promocionar
├── sitemap.xml           # Las cuatro paginas que quedan
└── llms.txt              # Resumen para asistentes de IA: proyecto cerrado
```

Las diez paginas comerciales (`plataforma.html`, `como-funciona.html`,
`ventajas.html`, `seguridad.html`, `ens.html`, `comparativa.html`, `faq.html`,
`soporte.html`, `contacto.html` y el stub `nosotros.html`) se eliminaron al
cerrar el proyecto. El menu y el pie apuntan ahora a anclas dentro de
`index.html` y al repositorio.

Todos los ficheros van en UTF-8 y los enlaces internos son **relativos**, por lo
que la carpeta se sirve tal cual en la **raiz** del dominio.

## Previsualizar en local

```bash
cd landing
python3 -m http.server 8000
# abre http://localhost:8000
```

## Despliegue

Contenido 100 % estatico: vale cualquier hosting de estaticos o el
`file_server` de Caddy. Conviene servir con cabecera
`Content-Type: text/html; charset=utf-8`.

Si se retira el dominio, conviene dejar redirecciones 301 de las diez paginas
borradas hacia `/`, para no dejar 404 en los enlaces que sigan por ahi.

## Notas

- **Datos de contacto**: los unicos que quedan son los del cuerpo de
  `aviso-legal.html` y `privacidad.html`, que son de obligada publicacion
  (identificacion del prestador en la LSSI-CE y ejercicio de derechos del
  RGPD). No deben borrarse mientras el sitio siga publicado.
- **`og-image.png`** conserva el reclamo comercial antiguo; si se sustituye,
  esta referenciada como `og:image`, `twitter:image` y `logo` de JSON-LD en las
  cuatro paginas.
- **Fuentes**: Google Fonts (Bricolage Grotesque + Sora) via CDN; requiere
  conexion a internet al renderizar.
