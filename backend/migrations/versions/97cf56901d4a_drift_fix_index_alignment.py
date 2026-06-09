"""drift_fix_index_alignment

MIG-A · Mini-Sesión 11.5 · Sub-bloque 11.5.B · CAT-B Index drift fix.

Closes TODO-DB-DRIFT-001 categoría B (Index drift) — 94 ops upgrade.

Scope (94 ops):
  B.1 RENAME PAIRS (18 pairs · 36 ops):
    - audit_simulation_findings (3) + audit_simulation_runs (1) prefix expand sim → simulation
    - change_topologies project → project_id
    - conformity_state_snapshots project_type → project_id (composite → single, intencional)
    - dda_project_signatures magic_link_id → signature_magic_link_id
    - document_tags value → tag_value
    - documents expires_at_notnull (partial) → expires_at (no partial)
    - idms_document_permissions (2) prefix expand idms_perm → idms_document_permissions
    - retainer_drift_events (2) prefix expand drift_events → retainer_drift_events
    - workspace_chat_messages (2) prefix expand chat_messages → workspace_chat_messages
    - workspace_feed_items (3) prefix expand feed_items → workspace_feed_items
  B.2a SIMPLE DROPS (44 ops): legacy índices BD sin equivalente modelo.
  B.2c PARTIAL DROPS (2 ops): exploratory_meetings.project_id partial + verification_runs.vr_cancel_pending partial.
  B.3 PURE CREATES (12 ops): índices modelo declarados que BD missing.

Excluidos MIG-A (movidos otras MIGs):
  - 5 ops drop acoplados drop_column → MIG-D (CAT-D)
  - 1 op uq_pricing_catalog → MIG-B (CAT-C constraint)

Modelos editados fuera migration (alineación realidad sin migration, BD ya tiene los índices):
  - 3 FTS GIN restored (M30 contacts notes + M29 messages body + meetings exploratory notes)
  - 6 custom indexes restored m08_verification (idx_vf_finding_hash + idx_vf_ens_primary + idx_vf_run_severity + idx_vf_run_status + idx_fpp_tool + idx_rr_finding)

Revision ID: 97cf56901d4a
Revises: e8b3c5d70a91
Create Date: 2026-04-30 10:34:21.668958
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '97cf56901d4a'
down_revision: Union[str, None] = 'e8b3c5d70a91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================================================================
    # B.1 RENAME PAIRS (18 pairs · 36 ops)
    # ==================================================================

    # 1-3. audit_simulation_findings: prefix expand sim → simulation
    op.drop_index('ix_audit_sim_findings_measure_code', table_name='audit_simulation_findings')
    op.drop_index('ix_audit_sim_findings_project_id', table_name='audit_simulation_findings')
    op.drop_index('ix_audit_sim_findings_run_id', table_name='audit_simulation_findings')
    op.create_index('ix_audit_simulation_findings_measure_code', 'audit_simulation_findings', ['measure_code'])
    op.create_index('ix_audit_simulation_findings_project_id', 'audit_simulation_findings', ['project_id'])
    op.create_index('ix_audit_simulation_findings_run_id', 'audit_simulation_findings', ['run_id'])

    # 4. audit_simulation_runs: prefix expand
    op.drop_index('ix_audit_sim_runs_project_id', table_name='audit_simulation_runs')
    op.create_index('ix_audit_simulation_runs_project_id', 'audit_simulation_runs', ['project_id'])

    # 5. change_topologies: column suffix _id standard
    op.drop_index('ix_change_topologies_project', table_name='change_topologies')
    op.create_index('ix_change_topologies_project_id', 'change_topologies', ['project_id'])

    # 6. conformity_state_snapshots: composite → single project_id (intencional, modelo declara single)
    op.drop_index('ix_conformity_state_snapshots_project_type', table_name='conformity_state_snapshots')
    op.create_index('ix_conformity_state_snapshots_project_id', 'conformity_state_snapshots', ['project_id'])

    # 7. dda_project_signatures: column rename magic_link_id → signature_magic_link_id
    op.drop_index('ix_dda_project_signatures_magic_link_id', table_name='dda_project_signatures')
    op.create_index('ix_dda_project_signatures_signature_magic_link_id', 'dda_project_signatures', ['signature_magic_link_id'])

    # 8. document_tags: column rename value → tag_value
    op.drop_index('ix_document_tags_value', table_name='document_tags')
    op.create_index('ix_document_tags_tag_value', 'document_tags', ['tag_value'])

    # 9. documents: drop partial WHERE → no partial
    op.drop_index('ix_documents_expires_at_notnull', table_name='documents', postgresql_where='(expires_at IS NOT NULL)')
    op.create_index('ix_documents_expires_at', 'documents', ['expires_at'])

    # 10-11. idms_document_permissions: prefix expand idms_perm → idms_document_permissions
    op.drop_index('ix_idms_perm_document_id', table_name='idms_document_permissions')
    op.drop_index('ix_idms_perm_user_id', table_name='idms_document_permissions')
    op.create_index('ix_idms_document_permissions_document_id', 'idms_document_permissions', ['document_id'])
    op.create_index('ix_idms_document_permissions_user_id', 'idms_document_permissions', ['user_id'])

    # 12-13. retainer_drift_events: prefix expand drift_events → retainer_drift_events
    op.drop_index('ix_drift_events_project_id', table_name='retainer_drift_events')
    op.drop_index('ix_drift_events_retainer_id', table_name='retainer_drift_events')
    op.create_index('ix_retainer_drift_events_project_id', 'retainer_drift_events', ['project_id'])
    op.create_index('ix_retainer_drift_events_retainer_contract_id', 'retainer_drift_events', ['retainer_contract_id'])

    # 14-15. workspace_chat_messages: prefix expand chat_messages → workspace_chat_messages
    op.drop_index('ix_chat_messages_project_id', table_name='workspace_chat_messages')
    op.drop_index('ix_chat_messages_workspace_id', table_name='workspace_chat_messages')
    op.create_index('ix_workspace_chat_messages_project_id', 'workspace_chat_messages', ['project_id'])
    op.create_index('ix_workspace_chat_messages_workspace_id', 'workspace_chat_messages', ['workspace_id'])

    # 16-18. workspace_feed_items: prefix expand feed_items → workspace_feed_items
    op.drop_index('ix_feed_items_project_id', table_name='workspace_feed_items')
    op.drop_index('ix_feed_items_tipo', table_name='workspace_feed_items')
    op.drop_index('ix_feed_items_workspace_id', table_name='workspace_feed_items')
    op.create_index('ix_workspace_feed_items_project_id', 'workspace_feed_items', ['project_id'])
    op.create_index('ix_workspace_feed_items_tipo', 'workspace_feed_items', ['tipo'])
    op.create_index('ix_workspace_feed_items_workspace_id', 'workspace_feed_items', ['workspace_id'])

    # ==================================================================
    # B.2a SIMPLE DROPS (44 ops · BD legacy sin equivalente modelo)
    # ==================================================================

    # auth_login_attempts (2 composite)
    op.drop_index('ix_auth_login_attempts_email_created', table_name='auth_login_attempts')
    op.drop_index('ix_auth_login_attempts_ip_created', table_name='auth_login_attempts')
    # auth_sessions (2)
    op.drop_index('ix_auth_sessions_expires_at', table_name='auth_sessions')
    op.drop_index('ix_auth_sessions_user_id', table_name='auth_sessions')
    # auth_webauthn_credentials (1)
    op.drop_index('ix_auth_webauthn_credentials_user_id', table_name='auth_webauthn_credentials')
    # basic_declarations (2)
    op.drop_index('ix_basic_declarations_self_assessment_report_id', table_name='basic_declarations')
    op.drop_index('ix_basic_declarations_submission_id', table_name='basic_declarations')
    # client_commitments (1)
    op.drop_index('ix_client_commitments_contract_id', table_name='client_commitments')
    # companies (2)
    op.drop_index('ix_companies_cnae', table_name='companies')
    op.drop_index('ix_companies_provincia', table_name='companies')
    # conformity_routes (1 composite)
    op.drop_index('ix_conformity_routes_project_status', table_name='conformity_routes')
    # documents (1 composite)
    op.drop_index('ix_documents_project_estado', table_name='documents')
    # exploratory_meetings (2 non-partial)
    op.drop_index('ix_exploratory_meetings_contact_id', table_name='exploratory_meetings')
    op.drop_index('ix_exploratory_meetings_status', table_name='exploratory_meetings')
    # extraordinary_audits (2)
    op.drop_index('ix_extraordinary_audits_audit_report_id', table_name='extraordinary_audits')
    op.drop_index('ix_extraordinary_audits_trigger_material_change_id', table_name='extraordinary_audits')
    # invoice_lines (1)
    op.drop_index('ix_invoice_lines_invoice_id', table_name='invoice_lines')
    # lms_assignments (1 NON-client_id; client_id va a MIG-D)
    op.drop_index('ix_lms_assignments_project_id', table_name='lms_assignments')
    # magic_links (1)
    op.drop_index('ix_magic_links_contact_id', table_name='magic_links')
    # material_changes (1 composite)
    op.drop_index('ix_material_changes_project_is_material', table_name='material_changes')
    # onboarding_sessions (2 composite)
    op.drop_index('ix_onboarding_sessions_project_role', table_name='onboarding_sessions')
    op.drop_index('ix_onboarding_sessions_project_state', table_name='onboarding_sessions')
    # participations (1)
    op.drop_index('ix_participations_company_id', table_name='participations')
    # payment_reminders (1)
    op.drop_index('ix_payment_reminders_invoice_id', table_name='payment_reminders')
    # pce_overlays (1)
    op.drop_index('ix_pce_overlays_assessment_report_id', table_name='pce_overlays')
    # project_archived_backups (1)
    op.drop_index('ix_project_archived_backups_expires_at', table_name='project_archived_backups')
    # project_lifecycle_events (1)
    op.drop_index('ix_project_lifecycle_events_event_date', table_name='project_lifecycle_events')
    # project_plans (1 composite)
    op.drop_index('ix_project_plans_project_estado', table_name='project_plans')
    # radar_leads (3)
    op.drop_index('ix_radar_leads_ccn_checked', table_name='radar_leads')
    op.drop_index('ix_radar_leads_score', table_name='radar_leads')
    op.drop_index('ix_radar_leads_temperatura', table_name='radar_leads')
    # recategorizations (2)
    op.drop_index('ix_recategorizations_analysis_report_id', table_name='recategorizations')
    op.drop_index('ix_recategorizations_trigger_material_change_id', table_name='recategorizations')
    # renewal_campaigns (1 composite)
    op.drop_index('ix_renewal_campaigns_project_scheduled', table_name='renewal_campaigns')
    # retainer_billing_events (1 composite)
    op.drop_index('ix_retainer_billing_events_contract_period', table_name='retainer_billing_events')
    # retainer_quarterly_reports (1 composite)
    op.drop_index('ix_retainer_quarterly_reports_contract_period', table_name='retainer_quarterly_reports')
    # role_exception_memos (2)
    op.drop_index('ix_role_exception_memos_document_id', table_name='role_exception_memos')
    op.drop_index('ix_role_exception_memos_role_topology_id', table_name='role_exception_memos')
    # sources_runs (2)
    op.drop_index('ix_sources_runs_source_id', table_name='sources_runs')
    op.drop_index('ix_sources_runs_started_at', table_name='sources_runs')
    # tenders (3)
    op.drop_index('ix_tenders_estado', table_name='tenders')
    op.drop_index('ix_tenders_fecha_publicacion', table_name='tenders')
    op.drop_index('ix_tenders_source', table_name='tenders')
    # wbs_tasks (1)
    op.drop_index('ix_wbs_tasks_status', table_name='wbs_tasks')

    # ==================================================================
    # B.2c PARTIAL DROPS (2 ops · partial indexes nicho)
    # ==================================================================

    op.drop_index(
        'ix_exploratory_meetings_project_id',
        table_name='exploratory_meetings',
        postgresql_where='(project_id IS NOT NULL)',
    )
    op.drop_index(
        'ix_vr_cancel_pending',
        table_name='verification_runs',
        postgresql_where='((cancel_requested_at IS NOT NULL) AND (cancel_completed_at IS NULL))',
    )

    # ==================================================================
    # B.3 PURE CREATES (12 ops · modelo declarado, BD missing)
    # ==================================================================

    op.create_index('ix_collaborative_workspaces_project_id', 'collaborative_workspaces', ['project_id'])
    op.create_index('ix_diagnosis_runs_project_id', 'diagnosis_runs', ['project_id'])
    op.create_index('ix_retainer_activities_fecha_programada', 'retainer_activities', ['fecha_programada'])
    op.create_index('ix_retainer_activities_project_id', 'retainer_activities', ['project_id'])
    op.create_index('ix_retainer_activities_retainer_contract_id', 'retainer_activities', ['retainer_contract_id'])
    op.create_index('ix_retainer_activities_tipo_actividad', 'retainer_activities', ['tipo_actividad'])
    op.create_index('ix_retainer_contracts_client_id', 'retainer_contracts', ['client_id'])
    op.create_index('ix_retainer_contracts_project_id', 'retainer_contracts', ['project_id'])
    op.create_index('ix_videocall_sessions_project_id', 'videocall_sessions', ['project_id'])
    op.create_index('ix_videocall_sessions_workspace_id', 'videocall_sessions', ['workspace_id'])
    op.create_index('ix_workspace_files_project_id', 'workspace_files', ['project_id'])
    op.create_index('ix_workspace_files_workspace_id', 'workspace_files', ['workspace_id'])


def downgrade() -> None:
    # ==================================================================
    # B.3 → drop (12 ops inverso)
    # ==================================================================

    op.drop_index('ix_workspace_files_workspace_id', table_name='workspace_files')
    op.drop_index('ix_workspace_files_project_id', table_name='workspace_files')
    op.drop_index('ix_videocall_sessions_workspace_id', table_name='videocall_sessions')
    op.drop_index('ix_videocall_sessions_project_id', table_name='videocall_sessions')
    op.drop_index('ix_retainer_contracts_project_id', table_name='retainer_contracts')
    op.drop_index('ix_retainer_contracts_client_id', table_name='retainer_contracts')
    op.drop_index('ix_retainer_activities_tipo_actividad', table_name='retainer_activities')
    op.drop_index('ix_retainer_activities_retainer_contract_id', table_name='retainer_activities')
    op.drop_index('ix_retainer_activities_project_id', table_name='retainer_activities')
    op.drop_index('ix_retainer_activities_fecha_programada', table_name='retainer_activities')
    op.drop_index('ix_diagnosis_runs_project_id', table_name='diagnosis_runs')
    op.drop_index('ix_collaborative_workspaces_project_id', table_name='collaborative_workspaces')

    # ==================================================================
    # B.2c → recreate partial (2 ops)
    # ==================================================================

    op.create_index(
        'ix_vr_cancel_pending',
        'verification_runs',
        ['cancel_requested_at'],
        postgresql_where=sa.text('cancel_requested_at IS NOT NULL AND cancel_completed_at IS NULL'),
    )
    op.create_index(
        'ix_exploratory_meetings_project_id',
        'exploratory_meetings',
        ['project_id'],
        postgresql_where=sa.text('project_id IS NOT NULL'),
    )

    # ==================================================================
    # B.2a → recreate (44 ops legacy restore con columnas exactas)
    # ==================================================================

    op.create_index('ix_wbs_tasks_status', 'wbs_tasks', ['status'])
    op.create_index('ix_tenders_source', 'tenders', ['source'])
    op.create_index('ix_tenders_fecha_publicacion', 'tenders', ['fecha_publicacion'])
    op.create_index('ix_tenders_estado', 'tenders', ['estado'])
    op.create_index('ix_sources_runs_started_at', 'sources_runs', ['started_at'])
    op.create_index('ix_sources_runs_source_id', 'sources_runs', ['source_id'])
    op.create_index('ix_role_exception_memos_role_topology_id', 'role_exception_memos', ['role_topology_id'])
    op.create_index('ix_role_exception_memos_document_id', 'role_exception_memos', ['document_id'])
    op.create_index('ix_retainer_quarterly_reports_contract_period', 'retainer_quarterly_reports', ['retainer_contract_id', 'period_start'])
    op.create_index('ix_retainer_billing_events_contract_period', 'retainer_billing_events', ['retainer_contract_id', 'billing_period_start'])
    op.create_index('ix_renewal_campaigns_project_scheduled', 'renewal_campaigns', ['project_id', 'scheduled_for'])
    op.create_index('ix_recategorizations_trigger_material_change_id', 'recategorizations', ['trigger_material_change_id'])
    op.create_index('ix_recategorizations_analysis_report_id', 'recategorizations', ['analysis_report_id'])
    op.create_index('ix_radar_leads_temperatura', 'radar_leads', ['temperatura'])
    op.create_index('ix_radar_leads_score', 'radar_leads', ['score'])
    op.create_index('ix_radar_leads_ccn_checked', 'radar_leads', ['ccn_checked'])
    op.create_index('ix_project_plans_project_estado', 'project_plans', ['project_id', 'estado'])
    op.create_index('ix_project_lifecycle_events_event_date', 'project_lifecycle_events', ['event_date'])
    op.create_index('ix_project_archived_backups_expires_at', 'project_archived_backups', ['expires_at'])
    op.create_index('ix_pce_overlays_assessment_report_id', 'pce_overlays', ['assessment_report_id'])
    op.create_index('ix_payment_reminders_invoice_id', 'payment_reminders', ['invoice_id'])
    op.create_index('ix_participations_company_id', 'participations', ['company_id'])
    op.create_index('ix_onboarding_sessions_project_state', 'onboarding_sessions', ['project_id', 'estado'])
    op.create_index('ix_onboarding_sessions_project_role', 'onboarding_sessions', ['project_id', 'rol_receptor'])
    op.create_index('ix_material_changes_project_is_material', 'material_changes', ['project_id', 'is_material'])
    op.create_index('ix_magic_links_contact_id', 'magic_links', ['sent_to_contact_id'])
    op.create_index('ix_lms_assignments_project_id', 'lms_assignments', ['project_id'])
    op.create_index('ix_invoice_lines_invoice_id', 'invoice_lines', ['invoice_id'])
    op.create_index('ix_extraordinary_audits_trigger_material_change_id', 'extraordinary_audits', ['trigger_material_change_id'])
    op.create_index('ix_extraordinary_audits_audit_report_id', 'extraordinary_audits', ['audit_report_id'])
    op.create_index('ix_exploratory_meetings_status', 'exploratory_meetings', ['status'])
    op.create_index('ix_exploratory_meetings_contact_id', 'exploratory_meetings', ['interlocutor_contact_id'])
    op.create_index('ix_documents_project_estado', 'documents', ['project_id', 'estado'])
    op.create_index('ix_conformity_routes_project_status', 'conformity_routes', ['project_id', 'status'])
    op.create_index('ix_companies_provincia', 'companies', ['provincia'])
    op.create_index('ix_companies_cnae', 'companies', ['cnae'])
    op.create_index('ix_client_commitments_contract_id', 'client_commitments', ['contract_id'])
    op.create_index('ix_basic_declarations_submission_id', 'basic_declarations', ['submission_id'])
    op.create_index('ix_basic_declarations_self_assessment_report_id', 'basic_declarations', ['self_assessment_report_id'])
    op.create_index('ix_auth_webauthn_credentials_user_id', 'auth_webauthn_credentials', ['user_id'])
    op.create_index('ix_auth_sessions_user_id', 'auth_sessions', ['user_id'])
    op.create_index('ix_auth_sessions_expires_at', 'auth_sessions', ['expires_at'])
    op.create_index('ix_auth_login_attempts_ip_created', 'auth_login_attempts', ['ip_address', 'created_at'])
    op.create_index('ix_auth_login_attempts_email_created', 'auth_login_attempts', ['email', 'created_at'])

    # ==================================================================
    # B.1 → revertir rename (drop new + create old, 36 ops inverso)
    # ==================================================================

    # 16-18. workspace_feed_items
    op.drop_index('ix_workspace_feed_items_workspace_id', table_name='workspace_feed_items')
    op.drop_index('ix_workspace_feed_items_tipo', table_name='workspace_feed_items')
    op.drop_index('ix_workspace_feed_items_project_id', table_name='workspace_feed_items')
    op.create_index('ix_feed_items_workspace_id', 'workspace_feed_items', ['workspace_id'])
    op.create_index('ix_feed_items_tipo', 'workspace_feed_items', ['tipo'])
    op.create_index('ix_feed_items_project_id', 'workspace_feed_items', ['project_id'])

    # 14-15. workspace_chat_messages
    op.drop_index('ix_workspace_chat_messages_workspace_id', table_name='workspace_chat_messages')
    op.drop_index('ix_workspace_chat_messages_project_id', table_name='workspace_chat_messages')
    op.create_index('ix_chat_messages_workspace_id', 'workspace_chat_messages', ['workspace_id'])
    op.create_index('ix_chat_messages_project_id', 'workspace_chat_messages', ['project_id'])

    # 12-13. retainer_drift_events
    op.drop_index('ix_retainer_drift_events_retainer_contract_id', table_name='retainer_drift_events')
    op.drop_index('ix_retainer_drift_events_project_id', table_name='retainer_drift_events')
    op.create_index('ix_drift_events_retainer_id', 'retainer_drift_events', ['retainer_contract_id'])
    op.create_index('ix_drift_events_project_id', 'retainer_drift_events', ['project_id'])

    # 10-11. idms_document_permissions
    op.drop_index('ix_idms_document_permissions_user_id', table_name='idms_document_permissions')
    op.drop_index('ix_idms_document_permissions_document_id', table_name='idms_document_permissions')
    op.create_index('ix_idms_perm_user_id', 'idms_document_permissions', ['user_id'])
    op.create_index('ix_idms_perm_document_id', 'idms_document_permissions', ['document_id'])

    # 9. documents (recreate partial)
    op.drop_index('ix_documents_expires_at', table_name='documents')
    op.create_index(
        'ix_documents_expires_at_notnull',
        'documents',
        ['expires_at'],
        postgresql_where=sa.text('expires_at IS NOT NULL'),
    )

    # 8. document_tags
    op.drop_index('ix_document_tags_tag_value', table_name='document_tags')
    op.create_index('ix_document_tags_value', 'document_tags', ['tag_value'])

    # 7. dda_project_signatures
    op.drop_index('ix_dda_project_signatures_signature_magic_link_id', table_name='dda_project_signatures')
    op.create_index('ix_dda_project_signatures_magic_link_id', 'dda_project_signatures', ['signature_magic_link_id'])

    # 6. conformity_state_snapshots (recreate composite original)
    op.drop_index('ix_conformity_state_snapshots_project_id', table_name='conformity_state_snapshots')
    op.create_index('ix_conformity_state_snapshots_project_type', 'conformity_state_snapshots', ['project_id', 'snapshot_type', 'created_at'])

    # 5. change_topologies
    op.drop_index('ix_change_topologies_project_id', table_name='change_topologies')
    op.create_index('ix_change_topologies_project', 'change_topologies', ['project_id'])

    # 4. audit_simulation_runs
    op.drop_index('ix_audit_simulation_runs_project_id', table_name='audit_simulation_runs')
    op.create_index('ix_audit_sim_runs_project_id', 'audit_simulation_runs', ['project_id'])

    # 1-3. audit_simulation_findings
    op.drop_index('ix_audit_simulation_findings_run_id', table_name='audit_simulation_findings')
    op.drop_index('ix_audit_simulation_findings_project_id', table_name='audit_simulation_findings')
    op.drop_index('ix_audit_simulation_findings_measure_code', table_name='audit_simulation_findings')
    op.create_index('ix_audit_sim_findings_run_id', 'audit_simulation_findings', ['run_id'])
    op.create_index('ix_audit_sim_findings_project_id', 'audit_simulation_findings', ['project_id'])
    op.create_index('ix_audit_sim_findings_measure_code', 'audit_simulation_findings', ['measure_code'])
