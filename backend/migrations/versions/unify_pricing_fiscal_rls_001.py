"""Unificación pricing + identidad fiscal (NIF) + RLS defense-in-depth (2026-06-11).

Migración de DATOS + RLS (no de esquema) que cierra tres frentes detectados en
la auditoría de coherencia:

1. PRICING — alinea la tabla de catálogo ``pricing_catalog`` (consumida por
   M23 retainer/billing) a la FUENTE ÚNICA (BÁSICA 3.200 · MEDIA 10.700 · ALTA
   22.800) eliminando los precios "sombra" divergentes (5.500/9.500/17.500), e
   inserta el tier ``R_CRITICAL`` (era seleccionable vía VALID_RETAINER_TIERS
   pero faltaba en el catálogo → lookup fallido latente). ``pricing_config`` (BD)
   sigue siendo la fuente editable y NO se toca aquí (respeta ediciones admin).

2. IDENTIDAD FISCAL — fija el NIF del consultor (77171140E · Marcos Mata García ·
   autónomo persona física) en ``admin_settings.fiscal`` de forma IDEMPOTENTE
   (solo si está vacío · no pisa ediciones posteriores vía /admin/settings/fiscal).
   El domicilio fiscal y los datos bancarios los completa Marcos por la UI.

3. RLS — activa Row-Level Security en las 2 únicas tablas tenant-scoped que
   quedaban sin política (``llm_interaction_log`` · project_id ·
   ``marcos_timesheet_entries`` · client_id), cumpliendo la convención del
   proyecto ("RLS en todas las tablas con client_id/project_id"). La política usa
   el escape ``OR current_x_id() IS NULL`` para NO romper las vistas admin
   cross-cliente (sin contexto → ve todo) y aislar cualquier conexión con
   contexto de tenant fijado (cliente → solo lo suyo).

Revision ID: unify_pricing_fiscal_rls_001
Revises: client_mfa_email_code_001
Create Date: 2026-06-11
"""
from typing import Sequence, Union

from alembic import op


revision: str = "unify_pricing_fiscal_rls_001"
down_revision: Union[str, None] = "client_mfa_email_code_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Precios canónicos (fuente única · idénticos a rules.BASE_PRICES + pricing_config)
_CANONICAL_IMPLANTACION = {
    "BASICA": 3200.00,
    "MEDIA": 10700.00,
    "ALTA": 22800.00,
}


def upgrade() -> None:
    # ── 1. PRICING · alinear pricing_catalog implantación a la fuente única ──
    for tier, price in _CANONICAL_IMPLANTACION.items():
        op.execute(
            f"""
            UPDATE pricing_catalog SET base_price = {price}
            WHERE category = 'implantacion' AND tier_code = '{tier}'
              AND deleted_at IS NULL
            """
        )

    # R_CRITICAL: tier seleccionable que faltaba en el catálogo (lookup latente)
    op.execute(
        """
        INSERT INTO pricing_catalog
            (id, category, tier_code, name, base_price, currency, billing_unit,
             extras_jsonb, description, effective_from, version, is_active, created_at)
        SELECT gen_random_uuid(), 'retainer', 'R_CRITICAL',
               'Retainer Critical (Alta · SOC + DR 24/7)', 3000.00, 'EUR', 'mensual',
               '{"sector_regulado": 500.00, "multi_ubicacion": 400.00,
                 "redteam_anual": 3500.00, "formacion_extra_sesion": 250.00,
                 "incident_support_hour": 130.00}'::jsonb,
               'Categoria ALTA / infraestructura critica. SOC + DR drills + '
               'comite mensual + pentest + auditoria anual. SLA 8h 24/7.',
               '2026-04-21', '2026-04-21', true, now()
        WHERE NOT EXISTS (
            SELECT 1 FROM pricing_catalog
            WHERE category = 'retainer' AND tier_code = 'R_CRITICAL'
              AND deleted_at IS NULL
        )
        """
    )

    # ── 2. IDENTIDAD FISCAL · fijar NIF del consultor (idempotente) ──
    # Solo si fiscal.nif está vacío/ausente · NO pisa ediciones vía UI.
    op.execute(
        """
        UPDATE admin_settings
        SET fiscal = fiscal || jsonb_build_object(
                'nif', '77171140E',
                'nombre_fiscal', 'Marcos Mata García',
                'nombre_comercial', 'Fulkro',
                'tipo_persona', 'F'
            ),
            updated_at = now()
        WHERE id = '00000000-0000-0000-0000-000000000001'::uuid
          AND COALESCE(NULLIF(fiscal->>'nif', ''), '') = ''
        """
    )

    # ── 3. RLS defense-in-depth en las 2 tablas tenant-scoped sin política ──
    _enable_rls("llm_interaction_log", "project_id", "current_project_id")
    _enable_rls("marcos_timesheet_entries", "client_id", "current_client_id")


def _enable_rls(table: str, col: str, fn: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {table}_isolation ON {table}
          USING ({col} = {fn}() OR {fn}() IS NULL)
        """
    )
    op.execute(
        f"""
        CREATE POLICY {table}_insert_permissive ON {table}
          FOR INSERT WITH CHECK (true)
        """
    )


def downgrade() -> None:
    for table in ("llm_interaction_log", "marcos_timesheet_entries"):
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_permissive ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute(
        """
        DELETE FROM pricing_catalog
        WHERE category = 'retainer' AND tier_code = 'R_CRITICAL'
        """
    )
    # Los precios de implantación NO se revierten (no hay valor previo canónico
    # al que volver · la fuente única es pricing_config).
    # La identidad fiscal NO se revierte (dato operativo · idempotente).
