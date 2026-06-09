# Motor 12 — Rotacion de clave Ed25519 para magic links

## Cuando rotar

- Sospecha de compromiso de la clave actual
- Rotacion periodica programada (recomendado: anual)
- Cambio de personal con acceso a produccion

## Procedimiento

1. Generar nueva clave (ver comando en .env.example)
2. Setear nueva clave en FULKRO_ML_PRIVATE_KEY
3. Restart del backend
4. **Tras 8 dias** (TTL mas largo de magic link = 7 dias + margen),
   todos los links firmados con la clave antigua habran expirado

## Limitacion actual

El sistema soporta **una sola clave activa**. Rotar invalida TODOS
los magic links generados antes del restart. Para rotacion sin
downtime, implementar key versioning con `kid` en JWT header (TODO
futuro, ver TODO-M12-G6).

## Impacto de la rotacion

- Links activos pendientes de consumir: **invalidados**
- Links ya consumidos: sin impacto (audit trail conservado en DB)
- Links revocados: sin impacto

## Mitigacion de rotacion forzada

Si hay que rotar la clave urgentemente (compromiso):
1. Rotar la clave inmediatamente
2. Consultar `magic_links` para links activos no consumidos
3. Re-generar manualmente los links criticos pendientes
4. Notificar a destinatarios afectados

## Referencias

- Service: backend/app/motors/m12_magic_link/service.py
- Tests: backend/tests/motors/test_m12_service.py
- Spec: ENS_PLATFORM_MASTER_SPEC_v2.1 seccion 5.1 Motor 12
