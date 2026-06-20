# Web pública de Fulkro (`fulkro.es`)

Sitio de marketing **estático** de Fulkro: la landing comercial y sus páginas de
apoyo (producto, ENS, comparativa, FAQ, contacto, legales). Es independiente de
la aplicación (`backend/` + `frontend/`): aquí no hay build ni framework, solo
HTML/CSS/JS plano. Cada página es **autocontenida** (CSS y JS en línea), así que
se puede abrir o desplegar sin pasos previos.

## Estructura

```
landing/
├── index.html            # Home
├── plataforma.html       # La plataforma
├── como-funciona.html    # Cómo funciona (paso a paso)
├── ventajas.html         # Por qué Fulkro
├── seguridad.html        # Pentest y nube
├── ens.html              # Guía: qué es el ENS
├── comparativa.html      # Fulkro vs. la competencia
├── faq.html              # Preguntas frecuentes
├── contacto.html         # Contacto / reservar demo
├── nosotros.html         # Sobre Fulkro
├── soporte.html          # Soporte
├── aviso-legal.html      # Aviso legal
├── privacidad.html       # Política de privacidad
├── cookies.html          # Política de cookies
├── og-image.png          # Imagen para compartir (1200×630)
├── robots.txt            # Permite crawlers tradicionales y de IA (GEO)
├── sitemap.xml           # Mapa del sitio
└── llms.txt              # Resumen para asistentes de IA
```

Todos los ficheros van en UTF-8 y los enlaces internos son **relativos**
(`plataforma.html`, `og-image.png`, …), por lo que la carpeta se sirve tal cual
en la **raíz** del dominio `https://fulkro.es/`.

## Previsualizar en local

Desde esta carpeta, con cualquier servidor estático. Por ejemplo:

```bash
cd landing
python3 -m http.server 8000
# abre http://localhost:8000
```

(Abrir los `.html` con doble clic también funciona; usar un servidor evita
diferencias menores con rutas y cabeceras.)

## Despliegue

Es contenido 100 % estático: vale cualquier hosting de estáticos o el
`file_server` de Caddy (el reverse proxy que ya usa el proyecto). Basta con
publicar el contenido de `landing/` en la raíz de `fulkro.es`. Conviene servir
con cabecera `Content-Type: text/html; charset=utf-8`.

## Notas

- **SEO/GEO**: `robots.txt`, `sitemap.xml`, `llms.txt` y los metadatos
  Open Graph / Twitter + JSON-LD (`schema.org`) ya apuntan a `https://fulkro.es`.
  Si cambia el dominio, hay que actualizar las URLs absolutas (`<link rel="canonical">`,
  `og:url`, `og:image`, sitemap, robots y llms.txt).
- **Fuentes**: se cargan desde Google Fonts (Bricolage Grotesque + Sora) vía CDN;
  requiere conexión a internet al renderizar.
- **`lastmod`** del sitemap está fijado a `2026-06-09`; actualízalo al publicar
  cambios de contenido relevantes.
- **Contacto** referenciado en las páginas: `marcosmata@fulkro.es` /
  `hola@fulkro.es` / `+34 637 165 328` / LinkedIn `company/fulkro`.
```
