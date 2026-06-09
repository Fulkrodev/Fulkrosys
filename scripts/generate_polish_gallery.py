"""Generate static HTML gallery for polish-test-results screenshots.

Emits index.html grouped per page (74 pages) with 6 viewport tiles per page.
Sticky alphabetical quick-jump nav · click thumbnail opens full image.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

SCREENSHOTS_DIR = Path(__file__).resolve().parents[1] / "frontend" / "polish-test-results" / "screenshots"
INDEX_HTML = SCREENSHOTS_DIR / "index.html"

VIEWPORTS_ORDER = ["desktop", "laptop", "tablet-l", "tablet", "mobile-md", "mobile-sm"]
VIEWPORT_LABELS = {
    "desktop": "Desktop 1920",
    "laptop": "Laptop 1440",
    "tablet-l": "Tablet L 1024",
    "tablet": "Tablet 820",
    "mobile-md": "Mobile MD 414",
    "mobile-sm": "Mobile SM 360",
}


def parse_screenshots() -> dict[str, dict[str, str]]:
    """Returns {page_slug: {viewport: filename}}."""
    pattern = re.compile(r"^(.+?)_(desktop|laptop|tablet-l|tablet|mobile-md|mobile-sm)\.png$")
    pages: dict[str, dict[str, str]] = {}
    for png in sorted(SCREENSHOTS_DIR.glob("*.png")):
        match = pattern.match(png.name)
        if not match:
            continue
        slug, viewport = match.group(1), match.group(2)
        pages.setdefault(slug, {})[viewport] = png.name
    return pages


def render_html(pages: dict[str, dict[str, str]]) -> str:
    sorted_slugs = sorted(pages.keys())
    total_pages = len(sorted_slugs)
    total_shots = sum(len(v) for v in pages.values())

    nav_items = "".join(
        f'<a href="#{html.escape(slug)}" class="nav-item">{html.escape(slug)}</a>'
        for slug in sorted_slugs
    )

    sections = []
    for slug in sorted_slugs:
        viewports = pages[slug]
        tiles = []
        for vp in VIEWPORTS_ORDER:
            if vp not in viewports:
                continue
            filename = viewports[vp]
            tiles.append(
                f'<a class="tile" href="{html.escape(filename)}" target="_blank" rel="noopener">'
                f'<div class="tile-viewport">{html.escape(VIEWPORT_LABELS[vp])}</div>'
                f'<img loading="lazy" src="{html.escape(filename)}" alt="{html.escape(slug)} {vp}" />'
                f'</a>'
            )
        sections.append(
            f'<section id="{html.escape(slug)}" class="page-section">'
            f'<header class="page-header">'
            f'<h2>{html.escape(slug)}</h2>'
            f'<span class="page-count">{len(viewports)}/6 viewports</span>'
            f'</header>'
            f'<div class="tiles">{"".join(tiles)}</div>'
            f'</section>'
        )

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<title>FULKRO polish-test-results gallery · {total_pages} pages · {total_shots} screenshots</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root {{
    --purple-700: #6d28d9;
    --purple-600: #7c3aed;
    --purple-100: #f3e8ff;
    --ink-900: #0f172a;
    --ink-700: #334155;
    --ink-500: #64748b;
    --ink-100: #f1f5f9;
    --bg: #fafafa;
    --card: #ffffff;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--ink-900);
    line-height: 1.5;
  }}
  .topbar {{
    position: sticky;
    top: 0;
    z-index: 10;
    background: linear-gradient(90deg, var(--purple-700), var(--purple-600));
    color: white;
    padding: 16px 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }}
  .topbar h1 {{ margin: 0; font-size: 18px; font-weight: 600; }}
  .topbar .meta {{ font-size: 13px; opacity: 0.9; margin-top: 4px; }}
  .layout {{ display: grid; grid-template-columns: 260px 1fr; min-height: calc(100vh - 64px); }}
  .nav {{
    background: var(--card);
    border-right: 1px solid var(--ink-100);
    padding: 16px 12px;
    overflow-y: auto;
    max-height: calc(100vh - 64px);
    position: sticky;
    top: 64px;
  }}
  .nav-search {{
    width: 100%;
    padding: 8px 10px;
    border: 1px solid var(--ink-100);
    border-radius: 6px;
    font-size: 13px;
    margin-bottom: 8px;
  }}
  .nav-item {{
    display: block;
    padding: 6px 8px;
    font-size: 12px;
    color: var(--ink-700);
    text-decoration: none;
    border-radius: 4px;
    transition: background 0.15s;
  }}
  .nav-item:hover {{ background: var(--purple-100); color: var(--purple-700); }}
  .nav-item.hidden {{ display: none; }}
  main {{ padding: 24px 32px; }}
  .page-section {{
    margin-bottom: 48px;
    background: var(--card);
    border: 1px solid var(--ink-100);
    border-radius: 8px;
    padding: 20px;
  }}
  .page-header {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--ink-100);
  }}
  .page-header h2 {{ margin: 0; font-size: 16px; color: var(--purple-700); font-family: ui-monospace, monospace; }}
  .page-count {{ font-size: 12px; color: var(--ink-500); }}
  .tiles {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }}
  @media (max-width: 1200px) {{ .tiles {{ grid-template-columns: repeat(2, 1fr); }} }}
  @media (max-width: 768px) {{
    .layout {{ grid-template-columns: 1fr; }}
    .nav {{ position: static; max-height: 200px; }}
    .tiles {{ grid-template-columns: 1fr; }}
  }}
  .tile {{
    display: block;
    border: 1px solid var(--ink-100);
    border-radius: 6px;
    overflow: hidden;
    background: var(--ink-100);
    text-decoration: none;
    color: inherit;
    transition: transform 0.15s, box-shadow 0.15s;
  }}
  .tile:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
  .tile-viewport {{
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 500;
    color: var(--ink-700);
    background: var(--card);
    border-bottom: 1px solid var(--ink-100);
  }}
  .tile img {{ width: 100%; display: block; max-height: 240px; object-fit: contain; background: white; }}
</style>
</head>
<body>
<div class="topbar">
  <h1>FULKRO polish-test-results gallery</h1>
  <div class="meta">{total_pages} pages · {total_shots} screenshots · 6 viewports (1920/1440/1024/820/414/360)</div>
</div>
<div class="layout">
  <aside class="nav">
    <input type="search" class="nav-search" placeholder="Filtrar pages..." oninput="filterNav(this.value)" />
    {nav_items}
  </aside>
  <main>
    {''.join(sections)}
  </main>
</div>
<script>
  function filterNav(query) {{
    const q = query.toLowerCase();
    document.querySelectorAll('.nav-item').forEach(el => {{
      el.classList.toggle('hidden', q && !el.textContent.toLowerCase().includes(q));
    }});
  }}
</script>
</body>
</html>
"""


def main() -> None:
    pages = parse_screenshots()
    if not pages:
        raise SystemExit(f"No screenshots found in {SCREENSHOTS_DIR}")
    INDEX_HTML.write_text(render_html(pages), encoding="utf-8")
    print(f"Wrote {INDEX_HTML} ({len(pages)} pages · {sum(len(v) for v in pages.values())} screenshots)")


if __name__ == "__main__":
    main()
