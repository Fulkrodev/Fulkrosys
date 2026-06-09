"""SAN-E MB-9.bis atom 9.bis.3 · RoPA Art. 30 GDPR + DPA Art. 28 sign tracking.

Creates ``fulkro_ropa_treatments`` (10 pre-seeded factual rows declaring
every processing activity FULKRO performs) and extends ``clients`` with
DPA sign tracking columns (``dpa_signed_at`` · ``dpa_version`` ·
``dpa_signed_minio_path``).

Revision ID: sane_mb9bis_ropa_001
Revises: sane_mb9bis_subs_001
Create Date: 2026-05-12
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "sane_mb9bis_ropa_001"
down_revision = "sane_mb9bis_subs_001"
branch_labels = None
depends_on = None


_TREATMENTS = [
    {
        "treatment_code": "T001",
        "treatment_name": "Almacenamiento de datos de cliente",
        "role": "controller",
        "purpose": (
            "Persistir información identificativa y profesional de los empleados "
            "del cliente necesaria para gestionar proyectos de consultoría ENS "
            "(RD 311/2022): contactos, designaciones de responsable de seguridad, "
            "histórico de obligaciones, evidencias documentales."
        ),
        "legal_basis": "Art. 6.1.b GDPR (ejecución contrato)",
        "data_categories": [
            "Identificativos (nombre, apellidos)",
            "Contacto profesional (email corporativo, teléfono)",
            "Datos laborales (cargo, organización)",
        ],
        "data_subjects_categories": [
            "Empleados del cliente",
            "Personas de contacto designadas",
        ],
        "recipients": [
            "Personal autorizado FULKRO (Marcos Mata García)",
            "Hetzner Online GmbH (sub-encargado · hosting)",
        ],
        "transfers_outside_eu": False,
        "transfer_safeguards": None,
        "retention_period": (
            "Duración del contrato + 7 años de retención de evidencias ENS "
            "(art. 24.1 RD 311/2022 · trazabilidad auditoría)"
        ),
        "security_measures": (
            "Cifrado en tránsito TLS 1.3 · Postgres RLS por proyecto · "
            "backups diarios cifrados · Ed25519 audit log signing · 2FA TOTP admin."
        ),
        "processor_name": "Hetzner Online GmbH",
        "is_sub_processor": True,
        "dpa_signed": True,
    },
    {
        "treatment_code": "T002",
        "treatment_name": "Envío de emails transaccionales y notificaciones",
        "role": "processor",
        "purpose": (
            "Entrega de magic links de acceso al portal cliente, notificaciones "
            "de hitos del proyecto, recordatorios y digests operacionales."
        ),
        "legal_basis": "Art. 6.1.b GDPR (ejecución contrato)",
        "data_categories": [
            "Identificativos (nombre, email)",
            "Metadatos de entrega (timestamps, message-id)",
        ],
        "data_subjects_categories": [
            "Empleados del cliente",
            "Contactos comerciales suscritos",
        ],
        "recipients": [
            "Postmark (ActiveCampaign LLC · EU Data Region)",
        ],
        "transfers_outside_eu": False,
        "transfer_safeguards": (
            "Postmark EU Data Region: datos retenidos exclusivamente en la UE; "
            "DPA Art. 28 GDPR firmado."
        ),
        "retention_period": (
            "Email body: 30 días · Metadatos de entrega: 1 año · "
            "Audit log de envío: 7 años (ENS)"
        ),
        "security_measures": (
            "TLS 1.3 al gateway · DKIM + SPF + DMARC · headers de tracking "
            "minimizados · email_log persistido en Postgres bajo RLS."
        ),
        "processor_name": "Postmark (ActiveCampaign LLC)",
        "is_sub_processor": True,
        "dpa_signed": True,
    },
    {
        "treatment_code": "T003",
        "treatment_name": "Mensajería WhatsApp Business",
        "role": "processor",
        "purpose": (
            "Canal opt-in para comunicaciones operacionales con clientes que "
            "han elegido WhatsApp como vía preferida (recordatorios, "
            "notificaciones de cambios, escalado de incidencias)."
        ),
        "legal_basis": "Art. 6.1.a GDPR (consentimiento explícito)",
        "data_categories": [
            "Identificativos (nombre)",
            "Contacto (teléfono móvil)",
            "Contenido de mensajes operacionales",
        ],
        "data_subjects_categories": ["Empleados del cliente que opt-in al canal"],
        "recipients": ["360dialog GmbH (Alemania · WhatsApp Business API)"],
        "transfers_outside_eu": False,
        "transfer_safeguards": (
            "360dialog opera desde Alemania; los datos no salen de la UE. "
            "DPA Art. 28 GDPR firmado."
        ),
        "retention_period": (
            "Conversaciones: 90 días post última interacción · "
            "Audit log de envío: 7 años (ENS)"
        ),
        "security_measures": (
            "Cifrado extremo a extremo (WhatsApp) · TLS 1.3 al gateway · "
            "opt-in/opt-out trazable en consent_audit_log."
        ),
        "processor_name": "360dialog GmbH",
        "is_sub_processor": True,
        "dpa_signed": True,
    },
    {
        "treatment_code": "T004",
        "treatment_name": "Análisis con modelo de lenguaje (Claude LLM)",
        "role": "processor",
        "purpose": (
            "Procesamiento automatizado de documentos del cliente (políticas, "
            "informes, evidencias) para extracción estructurada, resúmenes y "
            "razonamiento del copiloto FULKRO."
        ),
        "legal_basis": "Art. 6.1.b GDPR (ejecución contrato)",
        "data_categories": [
            "Contenido de documentos provistos por el cliente",
            "Identificativos (cuando aparecen en los propios documentos)",
        ],
        "data_subjects_categories": [
            "Empleados del cliente",
            "Terceros mencionados en documentación del cliente",
        ],
        "recipients": ["Anthropic PBC (Estados Unidos · API Claude)"],
        "transfers_outside_eu": True,
        "transfer_safeguards": (
            "Transferencia internacional a EE.UU. amparada por: "
            "(i) Cláusulas Contractuales Tipo 2021/914 firmadas con Anthropic; "
            "(ii) DPA Art. 28 GDPR firmado; "
            "(iii) Anthropic adheridos al EU-US Data Privacy Framework. "
            "Las solicitudes se enrutan preferentemente al endpoint Frankfurt."
        ),
        "retention_period": (
            "Anthropic no retiene contenido de prompts/respuestas para "
            "entrenamiento; logs operacionales de Anthropic: 30 días."
        ),
        "security_measures": (
            "TLS 1.3 al endpoint · sin contenido en logs FULKRO · "
            "llm_interaction_log con prompt/respuesta truncados para audit · "
            "RLS por proyecto en llm_interaction_log."
        ),
        "processor_name": "Anthropic PBC",
        "is_sub_processor": True,
        "dpa_signed": True,
    },
    {
        "treatment_code": "T005",
        "treatment_name": "Firma electrónica de documentos (signing_intents)",
        "role": "controller",
        "purpose": (
            "Generación, firma y archivo de documentos firmables (políticas, "
            "actas, DPA) mediante el motor de firma Ed25519 propio de FULKRO."
        ),
        "legal_basis": "Art. 6.1.b GDPR (ejecución contrato)",
        "data_categories": [
            "Identificativos del firmante",
            "Hash SHA-256 del documento firmado",
            "Firma Ed25519 + timestamp",
        ],
        "data_subjects_categories": [
            "Marcos Mata García (FULKRO)",
            "Representantes legales del cliente",
        ],
        "recipients": ["Personal autorizado FULKRO", "MinIO self-hosted (archivo)"],
        "transfers_outside_eu": False,
        "transfer_safeguards": None,
        "retention_period": (
            "Documentos firmados + claves públicas: 7 años (ENS audit) · "
            "Claves privadas: rotación anual con archivo cifrado."
        ),
        "security_measures": (
            "Ed25519 con clave privada en HSM/keyring local · MinIO con "
            "Object Lock WORM · audit log firmado para cada firma."
        ),
        "processor_name": None,
        "is_sub_processor": False,
        "dpa_signed": False,
    },
    {
        "treatment_code": "T006",
        "treatment_name": "Almacenamiento de evidencias documentales",
        "role": "processor",
        "purpose": (
            "Archivo a largo plazo de evidencias documentales del cliente que "
            "soportan el cumplimiento ENS (procedimientos, registros de "
            "operaciones, capturas, certificados)."
        ),
        "legal_basis": "Art. 6.1.b GDPR (ejecución contrato)",
        "data_categories": [
            "Contenido documental del cliente",
            "Metadatos (sha256, tipo MIME, autoría)",
        ],
        "data_subjects_categories": ["Empleados del cliente (incidental)"],
        "recipients": ["MinIO self-hosted (Falkenstein co-localizado)"],
        "transfers_outside_eu": False,
        "transfer_safeguards": None,
        "retention_period": "7 años (art. 24.1 RD 311/2022)",
        "security_measures": (
            "MinIO con bucket Object Lock WORM (evidence-worm) · "
            "TLS 1.3 al objeto · sha256 verificación integridad."
        ),
        "processor_name": None,
        "is_sub_processor": False,
        "dpa_signed": False,
    },
    {
        "treatment_code": "T007",
        "treatment_name": "Registros continuos de auditoría",
        "role": "controller",
        "purpose": (
            "Trazabilidad de todas las operaciones sobre datos del cliente para "
            "cumplir el principio de responsabilidad proactiva (Art. 5.2 GDPR + "
            "Art. 30 GDPR + ENS [op.exp.8])."
        ),
        "legal_basis": "Art. 6.1.c GDPR (obligación legal)",
        "data_categories": [
            "Usuario autor de la operación",
            "Acción realizada + recurso afectado",
            "Timestamp + IP de origen",
        ],
        "data_subjects_categories": [
            "Personal autorizado FULKRO",
            "Empleados del cliente con acceso al portal",
        ],
        "recipients": ["Personal autorizado FULKRO"],
        "transfers_outside_eu": False,
        "transfer_safeguards": None,
        "retention_period": "7 años (art. 24.1 RD 311/2022 + Art. 30.4 GDPR)",
        "security_measures": (
            "audit_log append-only con seq hash chained · Ed25519 signing del "
            "head cada noche · RLS multi-tenant + restricción acceso admin."
        ),
        "processor_name": None,
        "is_sub_processor": False,
        "dpa_signed": False,
    },
    {
        "treatment_code": "T008",
        "treatment_name": "Backups de la plataforma",
        "role": "controller",
        "purpose": (
            "Copias de seguridad cifradas de la base de datos y MinIO para "
            "garantizar continuidad de servicio y recuperación ante incidentes."
        ),
        "legal_basis": "Art. 6.1.c GDPR (obligación legal seguridad Art. 32)",
        "data_categories": [
            "Imagen completa de la base de datos cifrada",
            "Snapshots de buckets MinIO cifrados",
        ],
        "data_subjects_categories": [
            "Todos los interesados presentes en la plataforma (incidental)",
        ],
        "recipients": [
            "Personal autorizado FULKRO",
            "Hetzner Storage Box (S3-compatible · cifrado en reposo)",
        ],
        "transfers_outside_eu": False,
        "transfer_safeguards": None,
        "retention_period": (
            "Backups diarios: 30 días rolling · "
            "Backups full semanales: 7 años (cold storage)"
        ),
        "security_measures": (
            "Cifrado AES-256-GCM en reposo · clave de cifrado en HSM "
            "separado · restore test mensual automatizado."
        ),
        "processor_name": "Hetzner Online GmbH (Storage Box)",
        "is_sub_processor": True,
        "dpa_signed": True,
    },
    {
        "treatment_code": "T009",
        "treatment_name": "Timesheet del consultor (Marcos)",
        "role": "controller",
        "purpose": (
            "Registro de horas dedicadas a cada cliente para facturación, "
            "cumplimiento del retainer y obligaciones fiscales."
        ),
        "legal_basis": "Art. 6.1.b GDPR + Art. 6.1.c (obligaciones fiscales AEAT)",
        "data_categories": [
            "Cliente atendido (cif)",
            "Horas, fecha, descripción de la actividad",
        ],
        "data_subjects_categories": ["Marcos Mata García (autónomo)"],
        "recipients": ["Personal autorizado FULKRO", "Asesoría fiscal de Marcos"],
        "transfers_outside_eu": False,
        "transfer_safeguards": None,
        "retention_period": (
            "5 años (art. 30 Ley General Tributaria · plazo prescripción AEAT)"
        ),
        "security_measures": "Postgres RLS · audit_log de operaciones.",
        "processor_name": None,
        "is_sub_processor": False,
        "dpa_signed": False,
    },
    {
        "treatment_code": "T010",
        "treatment_name": "Analítica de uso (PostHog auto-hospedado)",
        "role": "controller",
        "purpose": (
            "Métricas agregadas de uso de la plataforma (páginas vistas, "
            "tiempos de respuesta) para mejora del producto. Solo se activa "
            "previo consentimiento explícito del cliente."
        ),
        "legal_basis": "Art. 6.1.a GDPR (consentimiento)",
        "data_categories": [
            "Eventos pseudonimizados",
            "Identificador anónimo de sesión",
        ],
        "data_subjects_categories": [
            "Empleados del cliente que opt-in en cookies analíticas",
        ],
        "recipients": ["PostHog auto-hospedado (planificado MB-13 · EU)"],
        "transfers_outside_eu": False,
        "transfer_safeguards": None,
        "retention_period": (
            "Eventos: 1 año · datos agregados: indefinido anonimizados"
        ),
        "security_measures": (
            "Pseudonimización al ingreso · cookies analíticas opt-in con "
            "consent_audit_log."
        ),
        "processor_name": None,
        "is_sub_processor": False,
        "dpa_signed": False,
    },
]


def upgrade() -> None:
    op.create_table(
        "fulkro_ropa_treatments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("treatment_code", sa.String(50), nullable=False, unique=True),
        sa.Column("treatment_name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("purpose", sa.Text, nullable=False),
        sa.Column("legal_basis", sa.String(100), nullable=False),
        sa.Column(
            "data_categories",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "data_subjects_categories",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("recipients", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column(
            "transfers_outside_eu",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("transfer_safeguards", sa.Text, nullable=True),
        sa.Column("retention_period", sa.String(200), nullable=False),
        sa.Column("security_measures", sa.Text, nullable=False),
        sa.Column("processor_name", sa.String(200), nullable=True),
        sa.Column(
            "is_sub_processor",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "dpa_signed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("dpa_expires_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "controller_dpo",
            sa.String(200),
            nullable=False,
            server_default="Marcos Mata García · dpo@fulkro.es",
        ),
        sa.Column(
            "last_reviewed_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    # Index name matches SQLAlchemy default (`ix_<table>_<column>`) so the
    # ``index=True`` declaration on the model column resolves cleanly in
    # alembic check.
    op.create_index(
        "ix_fulkro_ropa_treatments_last_reviewed_at",
        "fulkro_ropa_treatments",
        ["last_reviewed_at"],
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON fulkro_ropa_treatments "
        "TO fulkro_app"
    )

    # Pre-seed 10 factual treatments.
    bind = op.get_bind()
    for t in _TREATMENTS:
        bind.execute(
            sa.text(
                """
                INSERT INTO fulkro_ropa_treatments (
                    treatment_code, treatment_name, role, purpose,
                    legal_basis, data_categories, data_subjects_categories,
                    recipients, transfers_outside_eu, transfer_safeguards,
                    retention_period, security_measures, processor_name,
                    is_sub_processor, dpa_signed
                ) VALUES (
                    :treatment_code, :treatment_name, :role, :purpose,
                    :legal_basis, :data_categories, :data_subjects_categories,
                    :recipients, :transfers_outside_eu, :transfer_safeguards,
                    :retention_period, :security_measures, :processor_name,
                    :is_sub_processor, :dpa_signed
                )
                """
            ),
            t,
        )

    # Extend clients with DPA Article 28 sign tracking.
    op.add_column(
        "clients",
        sa.Column(
            "dpa_signed_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
    )
    op.add_column("clients", sa.Column("dpa_version", sa.String(20), nullable=True))
    op.add_column(
        "clients", sa.Column("dpa_signed_minio_path", sa.Text, nullable=True)
    )


def downgrade() -> None:
    op.drop_column("clients", "dpa_signed_minio_path")
    op.drop_column("clients", "dpa_version")
    op.drop_column("clients", "dpa_signed_at")
    op.drop_index(
        "ix_fulkro_ropa_treatments_last_reviewed_at",
        table_name="fulkro_ropa_treatments",
    )
    op.drop_table("fulkro_ropa_treatments")
