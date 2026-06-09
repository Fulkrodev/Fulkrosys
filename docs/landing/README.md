# Landing fulkro.es/garantia · deploy instructions

**Fase 1.E E.3** (2026-05-27) · Marcos approve. Estática HTML5 + CSS3 puros, sin dependencias externas, sin framework.

## Archivos

- `garantia.html` (~12 KB) · landing principal · hero + cómo funciona + FAQ + términos + credenciales + CTA
- `garantia.css` (~6 KB) · estilos · system fonts + mobile responsive + prefers-reduced-motion
- `README.md` · este doc

## Preview local

```bash
# Opción 1 · Python built-in
cd docs/landing && python3 -m http.server 8000
# → abrir http://localhost:8000/garantia.html

# Opción 2 · npx (si tienes Node)
cd docs/landing && npx http-server -p 8000
# → abrir http://localhost:8000/garantia.html
```

## Deploy a fulkro.es

### Opción A · SCP a Hetzner (recomendado · self-hosted)

```bash
# Asume Marcos tiene servidor con nginx/caddy + dominio fulkro.es apuntando al IP
scp docs/landing/garantia.html docs/landing/garantia.css marcos@fulkro.es:/var/www/fulkro.es/

# Nginx config (sample · ajustar paths):
#   server { listen 443 ssl; server_name fulkro.es;
#     root /var/www/fulkro.es;
#     location /garantia { try_files /garantia.html =404; }
#     ... ssl cert paths ...
#   }
```

### Opción B · GitHub Pages (free · público)

```bash
# Crear repo público fulkro-es en GitHub
# Copiar docs/landing/* a la raíz del repo
# Activar GitHub Pages settings (branch=main · folder=/root)
# Configurar dominio custom: settings → Pages → Custom domain "fulkro.es"
# Apuntar CNAME DNS fulkro.es → marcos.github.io
```

### Opción C · Vercel (free · auto-deploy)

```bash
# 1. Crear cuenta Vercel (gratis · login con GitHub)
# 2. New Project → Import desde repo o folder local
# 3. Configurar dominio custom en Vercel settings
# 4. Cada push a main triggers redeploy
```

### Opción D · Netlify (alternativa)

```bash
# Drag-and-drop folder docs/landing/ a https://app.netlify.com/drop
# Asignar dominio custom fulkro.es en site settings
# Update DNS A/CNAME records según instrucciones Netlify
```

## Pre-deploy checklist

- [ ] Reemplazar placeholder `+34 [teléfono]` con número real (línea ~140 garantia.html)
- [ ] Reemplazar `https://fulkro.es/og-garantia.png` con OG image real (1200×630 px recomendado)
- [ ] Configurar Google Analytics:
  - Descomentar `<script>` línea ~20 garantia.html
  - Reemplazar `GA_MEASUREMENT_ID` con measurement ID real
- [ ] Configurar política privacidad + términos servicio (links footer)
- [ ] Verificar contact email `marcosmata@fulkro.es` correcto
- [ ] Lighthouse audit local antes deploy:
  ```bash
  npx lighthouse http://localhost:8000/garantia.html --view
  # Target scores: Performance >90 · Accessibility >90 · Best Practices >90 · SEO >90
  ```

## Post-deploy verify

```bash
# Validate HTML5 W3C
curl -s "https://validator.w3.org/nu/?out=json&doc=https://fulkro.es/garantia" | jq

# Smoke test routes
curl -fsSL https://fulkro.es/garantia -o /dev/null && echo "OK 200"
curl -fsSL https://fulkro.es/garantia.css -o /dev/null && echo "CSS 200"

# Mobile responsive verify Chrome devtools:
# - Mobile S (320px) · iPhone SE (375px) · iPhone 12 Pro (390px) · Tablet (768px) · Desktop (1280px+)
```

## SEO sugerencias post-deploy

1. **Meta description optimize** · 150-160 chars · keyword "ENS implantación garantía"
2. **Schema.org Service markup** añadir JSON-LD en `<head>` cuando estructura comercial concrete
3. **Sitemap.xml + robots.txt** generar y subir al root
4. **Backlinks** desde LinkedIn perfil + portfolio professional + posts blog
5. **Tracking conversiones** CTA "Reservar 30 min" → Google Analytics goal o Calendly tracking

## Notas mantenimiento

- **NO frameworks · NO dependencies** · Marcos puede editar HTML/CSS directo en cualquier editor
- **Tipografía** · system fonts (no Google Fonts) · evita external blocking
- **Color brand** · accent azul `#1E40AF` · ajustable en `:root` `--accent` línea 4 garantia.css
- **Future-X mejoras** post-launch:
  - Animaciones CSS subtle (fade-in scroll) si Marcos demanda
  - Calculadora ROI interactiva (JS vanilla)
  - Form embed Calendly directo (`<iframe>` widget)
  - Casos de éxito post-cierre primer cliente piloto
