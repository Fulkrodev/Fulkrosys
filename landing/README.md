# Web publica de Fulkro (`fulkro.es`)

Sitio **estatico** de Fulkro. El proyecto se detuvo en septiembre de 2026 por
falta de traccion comercial: la web no vende nada ni ofrece ningun servicio, y
presenta lo que la plataforma hacia y como estaba construida (capacidades,
portales, capa de IA, arquitectura y calidad). El codigo completo se publica
bajo Apache-2.0 en <https://github.com/Fulkrodev/Fulkrosys>.

Es independiente de la aplicacion (`backend/` + `frontend/`): aqui no hay build
ni framework, solo HTML/CSS/JS plano. Cada pagina es **autocontenida** (CSS y JS
en linea), asi que se puede abrir o desplegar sin pasos previos.

## Estructura

```
landing/
├── index.html            # Portada: capacidades, recorrido, ciclo, portales, IA, arquitectura
├── aviso-legal.html      # Aviso legal
├── privacidad.html       # Politica de privacidad
├── cookies.html          # Politica de cookies
├── assets/               # Capturas, recorrido en video (WebM/MP4) y diagramas SVG
├── og-image.png          # Imagen para compartir (1200×630)
├── favicon.svg
├── robots.txt            # Sin allowlist de crawlers de IA: no hay nada que promocionar
├── sitemap.xml           # Las cuatro paginas que quedan
└── llms.txt              # Resumen para asistentes de IA
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
- **`og-image.png`** sale del diagrama de cabecera del README
  (`docs/assets/diagramas/es/hero.svg`); esta referenciada como `og:image`,
  `twitter:image` y `logo` de JSON-LD en las cuatro paginas.
- **Fuentes**: Google Fonts (Bricolage Grotesque + Sora) via CDN; requiere
  conexion a internet al renderizar.
