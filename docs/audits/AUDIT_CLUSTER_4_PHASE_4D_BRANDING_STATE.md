# AUDIT CLUSTER 4 Phase 4D · Multi-Tenant Branding Cliente Empirical State

**Sesión**: 3B-2B.8 CLUSTER 4 Phase 4D
**Fecha**: 2026-05-26
**Status**: ✅ **Audit complete · scope refined logo serve + ClientSidebar logo display · NO STOP HARD**

## Empirical findings

- ✅ ClientBrandingProvider exists · fetches `/client-portal/branding` · injects CSS vars primary/secondary
- ✅ ClientFooter consumes `footer_text` empirical
- ✅ BrandingView schema rica: primary_color · secondary_color · footer_text · logo_path · has_logo
- ✅ Admin endpoints branding CRUD complete
- ✅ Cliente endpoint `/client-portal/branding` returns metadata
- ❌ **NO cliente-side endpoint serves logo binary** (only admin DELETE `/admin/.../branding/logo` exists)
- ❌ **ClientSidebar uses hardcoded FULKRO logo** (NO cliente logo display when has_logo=True)
- ❌ **NO logo_url derived in ClientBrandingProvider**

## Refined scope Phase 4D (~1.5-2h)

1. NEW cliente endpoint `GET /client-portal/branding/logo` serves logo binary (mimic admin pattern)
2. ClientBrandingProvider exposes `logoUrl` derived from has_logo
3. ClientSidebar render cliente logo when present (fallback FULKRO mono-white)
4. audit_log emit `cliente.branding.logo.viewed` Sub-atom 5.A
5. Tests TypeScript clean + backend endpoint test

## Pattern formalizable
- Multi-tenant branding logo serve + reactive consume pattern (BrandingProvider expose logoUrl · components derive cliente vs fallback fork)
