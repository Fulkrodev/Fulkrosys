"""projects_19dims_1c_d_a0_001 · sub-atom 1.C.D.A.0.1 (19 dimensiones adaptación).

ALTER projects table añadiendo 16 columnas para capturar dimensiones que
drive workflow adapation (Anexo L plan v3.8).

Storage actual pre-migration (3 dims existing empíricamente):
  - categoria_objetivo VARCHAR(10)            · dim 1 (BASICA/MEDIA/ALTA)
  - archetype VARCHAR(50)                     · dim 2 (fintech/saas_tech/...)
  - fase VARCHAR(50)                          · dim 5 (10 fases lifecycle)

Storage post-migration (19 dims total · 3 existing + 16 nuevas):
  - tamano_empleados                · dim 3
  - madurez_ens_actual              · dim 4
  - geografia_operacion             · dim 6
  - procesa_datos_sensibles_rgpd9   · dim 7
  - aplica_nis2                     · dim 8
  - aplica_dora                     · dim 9
  - aplica_ai_act                   · dim 10
  - dpo_designado                   · dim 11
  - arquitectura_sistemas           · dim 12
  - multi_tenancy                   · dim 13
  - equipo_ti_tamano                · dim 14
  - certificaciones_previas (JSONB) · dim 15
  - urgencia_certificacion          · dim 16
  - presupuesto_disponible          · dim 17
  - compromiso_interno              · dim 18
  - horas_cliente_semana            · dim 19

OPS-029 caso 9 formalizada: spec plan v3.7 decía "4 dims existing + 15 nuevas"
pero audit empírico Claude Code reveló "3 existing + 16 nuevas" (tamano_empleados
no estaba en projects table · realidad gana).

OPS-045 caso 4 sostenido: NO crear tabla nueva · extender projects existing
(audit-first reveals infrastructure · ADR-025 NO new tables sostenido).

Revision ID: projects_19dims_1c_d_a0_001
Revises: live_records_1c_b_001
Create Date: 2026-05-19
"""
from typing import Sequence, Union

from alembic import op


revision: str = "projects_19dims_1c_d_a0_001"
down_revision: Union[str, None] = "live_records_1c_b_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Añadir 16 columnas + CHECK constraints (defensivos · valores Anexo L v3.8)
    op.execute(
        """
        ALTER TABLE projects
          ADD COLUMN IF NOT EXISTS tamano_empleados VARCHAR(20) NOT NULL DEFAULT 'pequeno',
          ADD COLUMN IF NOT EXISTS madurez_ens_actual VARCHAR(2) NOT NULL DEFAULT 'L0',
          ADD COLUMN IF NOT EXISTS geografia_operacion VARCHAR(20) NOT NULL DEFAULT 'spain',
          ADD COLUMN IF NOT EXISTS procesa_datos_sensibles_rgpd9 BOOLEAN NOT NULL DEFAULT false,
          ADD COLUMN IF NOT EXISTS aplica_nis2 VARCHAR(20) NOT NULL DEFAULT 'no',
          ADD COLUMN IF NOT EXISTS aplica_dora VARCHAR(30) NOT NULL DEFAULT 'no',
          ADD COLUMN IF NOT EXISTS aplica_ai_act VARCHAR(20) NOT NULL DEFAULT 'no',
          ADD COLUMN IF NOT EXISTS dpo_designado VARCHAR(20) NOT NULL DEFAULT 'no_designado',
          ADD COLUMN IF NOT EXISTS arquitectura_sistemas VARCHAR(30) NOT NULL DEFAULT 'cloud_native',
          ADD COLUMN IF NOT EXISTS multi_tenancy VARCHAR(20) NOT NULL DEFAULT 'single',
          ADD COLUMN IF NOT EXISTS equipo_ti_tamano VARCHAR(20) NOT NULL DEFAULT '1_3',
          ADD COLUMN IF NOT EXISTS certificaciones_previas JSONB NOT NULL DEFAULT '[]'::jsonb,
          ADD COLUMN IF NOT EXISTS urgencia_certificacion VARCHAR(20) NOT NULL DEFAULT '6m',
          ADD COLUMN IF NOT EXISTS presupuesto_disponible VARCHAR(20) NOT NULL DEFAULT 'estandar',
          ADD COLUMN IF NOT EXISTS compromiso_interno VARCHAR(20) NOT NULL DEFAULT 'reactivo',
          ADD COLUMN IF NOT EXISTS horas_cliente_semana VARCHAR(20) NOT NULL DEFAULT '5_15h'
        """
    )

    # CHECK constraints per enum (defensivos · valores Anexo L v3.8)
    op.execute(
        """
        ALTER TABLE projects
          ADD CONSTRAINT ck_projects_tamano_empleados
            CHECK (tamano_empleados IN ('micro','pequeno','mediano','grande','enterprise')),
          ADD CONSTRAINT ck_projects_madurez_ens_actual
            CHECK (madurez_ens_actual IN ('L0','L1','L2','L3','L4','L5')),
          ADD CONSTRAINT ck_projects_geografia_operacion
            CHECK (geografia_operacion IN ('spain','ue','global','apac','latam')),
          ADD CONSTRAINT ck_projects_aplica_nis2
            CHECK (aplica_nis2 IN ('no','esencial','importante')),
          ADD CONSTRAINT ck_projects_aplica_dora
            CHECK (aplica_dora IN ('no','entidad_financiera','proveedor_ict_critico')),
          ADD CONSTRAINT ck_projects_aplica_ai_act
            CHECK (aplica_ai_act IN ('no','alto_riesgo','gpai','limitado')),
          ADD CONSTRAINT ck_projects_dpo_designado
            CHECK (dpo_designado IN ('interno','externo','no_designado')),
          ADD CONSTRAINT ck_projects_arquitectura_sistemas
            CHECK (arquitectura_sistemas IN ('on_premise','hibrido','cloud_native','multi_cloud','hyperscaler')),
          ADD CONSTRAINT ck_projects_multi_tenancy
            CHECK (multi_tenancy IN ('single','multi_tenant','marketplace')),
          ADD CONSTRAINT ck_projects_equipo_ti_tamano
            CHECK (equipo_ti_tamano IN ('sin_equipo','1_3','4_10','11_30','gt30')),
          ADD CONSTRAINT ck_projects_urgencia_certificacion
            CHECK (urgencia_certificacion IN ('no_urge','6m','3m','1m','urgent_30d')),
          ADD CONSTRAINT ck_projects_presupuesto_disponible
            CHECK (presupuesto_disponible IN ('minimo','estandar','generoso','premium')),
          ADD CONSTRAINT ck_projects_compromiso_interno
            CHECK (compromiso_interno IN ('proactivo','reactivo','reluctante')),
          ADD CONSTRAINT ck_projects_horas_cliente_semana
            CHECK (horas_cliente_semana IN ('lt5h','5_15h','15_40h','full_time'))
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE projects
          DROP CONSTRAINT IF EXISTS ck_projects_tamano_empleados,
          DROP CONSTRAINT IF EXISTS ck_projects_madurez_ens_actual,
          DROP CONSTRAINT IF EXISTS ck_projects_geografia_operacion,
          DROP CONSTRAINT IF EXISTS ck_projects_aplica_nis2,
          DROP CONSTRAINT IF EXISTS ck_projects_aplica_dora,
          DROP CONSTRAINT IF EXISTS ck_projects_aplica_ai_act,
          DROP CONSTRAINT IF EXISTS ck_projects_dpo_designado,
          DROP CONSTRAINT IF EXISTS ck_projects_arquitectura_sistemas,
          DROP CONSTRAINT IF EXISTS ck_projects_multi_tenancy,
          DROP CONSTRAINT IF EXISTS ck_projects_equipo_ti_tamano,
          DROP CONSTRAINT IF EXISTS ck_projects_urgencia_certificacion,
          DROP CONSTRAINT IF EXISTS ck_projects_presupuesto_disponible,
          DROP CONSTRAINT IF EXISTS ck_projects_compromiso_interno,
          DROP CONSTRAINT IF EXISTS ck_projects_horas_cliente_semana
        """
    )

    op.execute(
        """
        ALTER TABLE projects
          DROP COLUMN IF EXISTS tamano_empleados,
          DROP COLUMN IF EXISTS madurez_ens_actual,
          DROP COLUMN IF EXISTS geografia_operacion,
          DROP COLUMN IF EXISTS procesa_datos_sensibles_rgpd9,
          DROP COLUMN IF EXISTS aplica_nis2,
          DROP COLUMN IF EXISTS aplica_dora,
          DROP COLUMN IF EXISTS aplica_ai_act,
          DROP COLUMN IF EXISTS dpo_designado,
          DROP COLUMN IF EXISTS arquitectura_sistemas,
          DROP COLUMN IF EXISTS multi_tenancy,
          DROP COLUMN IF EXISTS equipo_ti_tamano,
          DROP COLUMN IF EXISTS certificaciones_previas,
          DROP COLUMN IF EXISTS urgencia_certificacion,
          DROP COLUMN IF EXISTS presupuesto_disponible,
          DROP COLUMN IF EXISTS compromiso_interno,
          DROP COLUMN IF EXISTS horas_cliente_semana
        """
    )
