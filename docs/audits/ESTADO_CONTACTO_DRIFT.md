# `estado_contacto` — drift frontend ↔ backend (PENDIENTE, no bloqueante)

> Estado: **documentado, no corregido**. Cleanup pendiente. Fecha: 2026-05-29.
> NO es un crash: los schemas Zod del lead usan `z.string()`, no el enum, así que
> ningún valor del backend se rechaza. El impacto es de **etiquetado/filtros**:
> estados reales sin label/chip y valores fantasma que el backend nunca emite.

## Fuente de verdad (backend)

`backend/app/motors/m10_ens_radar/db/models.py` — CHECK constraint
`radar_leads_estado_contacto_check` (máquina de estados canónica Phase C.4, 10 estados):

```
'nuevo', 'contactado', 'respondido', 'discovery_scheduled',
'discovery_realizada', 'propuesta_enviada', 'en_negociacion',
'cerrado_ganado', 'cerrado_perdido', 'descartado'
```

## Estado del frontend (drift)

`frontend/lib/api/ens-radar.ts` — `EstadoContactoEnum` (Zod), desincronizado:

```
'nuevo', 'enviado', 'respondio', 'reunion_agendada',
'propuesta_enviada', 'descartado', 'ganado', 'no_interesa'
```

### Estados reales SIN representación en el enum del frontend
- `contactado`  (frontend tiene `enviado`)
- `respondido`  (frontend tiene `respondio`, sin la 'd')
- `discovery_scheduled`  (frontend tiene `reunion_agendada`)
- `discovery_realizada`  (no existe en frontend)
- `en_negociacion`  (no existe en frontend)
- `cerrado_ganado`  (frontend tiene `ganado`)
- `cerrado_perdido`  (no existe en frontend)

### Valores FANTASMA en el frontend (el backend nunca los emite)
- `enviado`, `respondio`, `reunion_agendada`, `ganado`, `no_interesa`

## Impacto real

- **No hay fallo de validación**: `LeadListItemSchema` / `LeadDossierSchema` /
  action-responses usan `estado_contacto: z.string()`, no `EstadoContactoEnum`.
- **Sí hay degradación de UI**: `ESTADO_CONFIG[lead.estado_contacto]?.label ??
  lead.estado_contacto` cae al valor crudo para los estados sin config; los chips
  de filtro de `LeadsTable` no cubren los estados reales que no estén en el set.
- `EstadoContactoEnum` queda como tipo huérfano (definido, no usado en parsing).

## Remediación propuesta (cuando se aborde)

1. Alinear `EstadoContactoEnum` (y `ESTADO_CONFIG` / `EstadoBadge` / chips de
   filtro de `LeadsTable`) con los 10 estados canónicos del backend.
2. Eliminar los valores fantasma (`enviado`, `respondio`, `reunion_agendada`,
   `ganado`, `no_interesa`) o mapearlos a los canónicos si hubo datos legacy.
3. Opcional: usar `EstadoContactoEnum` en los schemas (en lugar de `z.string()`)
   solo si se quiere validación estricta — con `.catch()`/passthrough para no
   romper ante un estado nuevo del backend.
