# Ejecutable 8 · Pasada 14 · Documents Generation Perfection

## Alcance y método
Verificación empírica de los documentos de los 3 manuales generados por `m06_document_factory` (plantillas E-codes), firma `m05_signing` + Ed25519 propio de m06, motores reportlab/docxtpl. 2 samples generados vía `.venv`. NO se tocó BD/migraciones (drift reservado Pasada 16). grep usado solo para verificación.

## 1. Inventario de plantillas (m06_document_factory/templates)

| Categoría | `.md` (fuente) | `.py` (render helper) | Rango E-codes |
|-----------|---------------|----------------------|---------------|
| **policies** | 40 | 33 | PSI E100 (×4 variantes: base/salud/saas_only/desarrollador_aapp), normativa E101-E126, E150 plan adecuación, E160 manual SGSI, E170 plan director, E180/E041 declaración conformidad 809, actas gobierno E002/E003, + W001/LW001-003 |
| **procedures (POS)** | 37 | 36 | E200-E234 + E204A + W002 |
| **deliverables** | 44 | 37 | E001 ficha ejecutiva, E012 acta categorización+DdA, E040/E041/E042/E043, E050 auditoría interna, E090 diagnóstico, E400-E406 (BIA/BCP/DRP/continuidad), E500-E504 (formación), E600-E615 (proveedores/retainer), E700-E709 (verificación/red team/INES), + L001-L007 legales LCSP |
| **commercial** | 3 | 3 | P001 propuesta maestra, C001 contrato consultoría, C003 contrato mantenimiento |
| **TOTAL** | **124** | **109** | — |
| excel_generators | — | 19 generadores | matrices DdA/RACI/riesgos/RAT-RGPD/BIA/inventario/SLA/CAIQ/PDA/etc |

Evidencia: `out/p14_count.sh` ejecutado · `backend/app/motors/m06_document_factory/templates/{policies,procedures,deliverables,commercial}/`.

## 2. Checklist per documento clave (logo / branding / completo / adaptación / firmable)

| Documento | Logo Fulkro (7.6) | Branding cohesivo | Contenido completo | Adaptación per-proyecto | Firmable m05 |
|-----------|:---:|:---:|:---:|:---:|:---:|
| **Propuesta** (proposal_pdf.py live) | ✅ `fulkro-logo-light.svg` | ✅ tokens violeta + footer fulkro_identity | ✅ 10+ páginas | ✅✅ empresa/CIF/sector/categoría/expediente/pliego_excerpt/dolor/ángulo | n/a (comercial) |
| **PSI E100** (políticas) | ⚠️ `logo_marcos.png` (header_brand NO usado) | ❌ NO importa fulkro_identity | ✅ alineado Art.12 RD311 + CCN-STIC 805 | ✅ Jinja `cliente.razon_social`/`proyecto.*`/`responsables.*` | ✅ `policy_approval` (m05) |
| **Procedimientos POS E200-234** | ⚠️ `logo_marcos.png` | ❌ sin fulkro_identity | ✅ | ✅ Jinja per-proyecto | ⚠️ `document_generic` (no SignableType propio) |
| **DdA E040** | ⚠️ | ❌ | ✅ 73 medidas Anexo II | ✅ | ✅ `dda` (step-up OTP) |
| **Declaración Conformidad E041/E180** | ⚠️ | ❌ | ✅ formato 809 | ✅ | ✅ `conformidad_ens` (step-up OTP) |
| **Acta Comité E003/E012** | ⚠️ | ❌ | ✅ | ✅ | ✅ `acta_comite` |
| **Acta Nombramiento Roles E002** | ⚠️ | ❌ | ✅ | ✅ | ⚠️ `document_generic` (no mapeo) |
| **Plan Adecuación E150** | ⚠️ | ❌ | ✅ | ✅ | ⚠️ `document_generic` (no mapeo) |
| **Sample firma genérico** (m05 embed) | ✅ Fulkro footer | ✅ badge Ed25519+hash chain | ✅ | n/a | ✅ canvas TIER1 |

Leyenda firma: `m05_signing.signable_types` catalog = 11 SignableType (`dda`, `magerit_validation`, `pentest_authorization`, `conformidad_ens`, `acta_comite`, `retainer_offer`, `retainer_quarterly_signoff`, `policy_approval`, `incident_close`, `dpc_anual`, `renewal`, `document_generic`).

## 3. Firma + Ed25519 + audit_log
- **m06 propio**: integridad SHA-256 + Ed25519 (`signing.py` clave dev `var/keys/m6_signing_dev.ed25519.pem`) sobre el DOCX renderizado · sello de integridad, NO flujo de firma cliente.
- **m05_signing**: firma cliente canvas TIER1 + Ed25519 + OTP step-up para alta criticidad · audit_log canónico `signature.*` (Ejecutable 7.7).
- **GAP**: `m06.service.generate_document` NO emite ningún evento canónico `document.generated`/`document.signed` en audit_log. Único match `document.id=` es en `m09_audit_prep/cleanup_service.py:52` (no canónico). Trazabilidad ENAC de generación documental NO registrada en audit_log inmutable (R6/ADR-031 parcialmente incumplido para m06).

## 4. Samples empíricos generados
| Sample | Comando | Tamaño | Contenido verificado |
|--------|---------|--------|----------------------|
| Firma genérico | `.venv/bin/python -m backend.scripts.generate_signed_sample_pdf out/p14_sample_signed.pdf` | **3414 bytes** | 2 páginas + página firma con imagen canvas + badge Ed25519 + hash chain + footer Fulkro |
| Propuesta MEDIA | `out/p14_propuesta_sample.py` (build_proposal_pdf, ctx sintético) | **479670 bytes** | hyperpersonalizado ACME/B12345678/sector/MEDIA/EXP-2026-0042/pliego_excerpt · logo `fulkro-logo-light.svg` · contacto `www.fulkro.es · marcosmata@fulkro.es · +34 637 165 328 · Marcos Mata` |

Evidencia: `out/p14_sample_signed.pdf`, `out/p14_propuesta_sample.pdf`, `out/p14_propuesta_sample.py`.

## 5. Cruce con gaps P10
- **Distintivo SIN color de marca (CONFIRMADO)**: `backend/app/fulkro_identity.py` + `frontend/lib/fulkro-identity.ts` NO contienen Pantone Orange 021C ni ningún hex de color de marca · solo teléfono/web/email/tagline/footer/firma. No hay distintivo cromático canónico.
- **Documento de Alcance dedicado FALTA (CONFIRMADO)**: 0 plantillas `alcance`/`scope`/`ámbito` dedicadas (los matches son contenido dentro de otras políticas). No existe E-code de Documento de Alcance del SGSI.
- **Actas gobierno "solo document_generic firmable" (MATIZADO/PARCIAL)**: el catálogo `m05.signable_types` SÍ tiene `acta_comite` (E003/E012) y `policy_approval` (E100-126) como tipos de 1ª clase con rutas portal dedicadas. PERO `E002` (acta nombramiento roles) y `E150` (plan adecuación) NO tienen SignableType propio → caen en `document_generic`. El gap P10 es preciso solo para E002/E150, no para todas las actas.

## 6. Hallazgos de cohesión adicionales (m06 quedó fuera del Ejecutable 7.6)
- `m06.rendering._inject_brand` usa `assets/brand/logo_marcos.png` (logo de Marcos) mientras la propuesta usa `frontend/public/brand/fulkro-logo-light.svg` (logo Fulkro): **dos identidades visuales distintas** según el generador.
- m06 (124 plantillas) NO importa `fulkro_identity` → footer/teléfono/web Fulkro NO propagados a políticas/procedimientos/entregables/actas. Ejecutable 7.6 cubrió propuesta+emails+copilots pero NO m06.
- `consultor.header_brand` (InlineImage logo) se inyecta en el contexto pero NINGÚN template `.md` usa la variable `header_brand` (0 matches) → embed de logo consultor efectivamente muerto; el bloque de firma cae a texto `_default_firmas` "Marcos Mata García / Consultor independiente en ENS".

## Conclusión
La **propuesta comercial** es el documento perfecto (identity + personalización real). Los **124 documentos m06** son normativamente completos y bien personalizados per-proyecto (Jinja cliente/proyecto/responsables), pero quedaron fuera de la propagación de identidad del Ejecutable 7.6: branding inconsistente (logo Marcos vs logo Fulkro), sin footer/contacto Fulkro, sin evento audit_log de generación, y con embed de logo consultor muerto. Gaps P10 confirmados (distintivo sin color, Alcance ausente) con un matiz: actas comité y políticas SÍ son firmables 1ª clase vía m05; solo E002/E150 caen en document_generic.