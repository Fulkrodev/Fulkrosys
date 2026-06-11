"""FULKRO application configuration."""
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database — app uses fulkro_app (NOSUPERUSER) for RLS enforcement
    database_url: str = "postgresql+asyncpg://fulkro_app:changeme@localhost:5433/fulkro"
    database_url_sync: str = "postgresql://fulkro_app:changeme@localhost:5433/fulkro"
    # Alembic uses fulkro_migrate (SUPERUSER) for DDL — read by migrations/env.py
    database_migrate_url: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Anthropic
    anthropic_api_key: SecretStr = SecretStr("")
    anthropic_default_model: str = "claude-sonnet-4-5"
    anthropic_fallback_model: str = "claude-opus-4-6"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "fulkro"
    minio_secret_key: SecretStr = SecretStr("changeme")
    minio_bucket: str = "fulkro"
    # URL pública absoluta para construir links a assets en buckets
    # con public read (ej: fulkro-admin-assets logos). En dev coincide
    # con minio_endpoint via http://; en staging/prod puede ser un
    # CDN o nginx proxy delante.
    minio_public_url: str = "http://localhost:9000"

    # Application
    app_env: str = "development"
    app_secret_key: SecretStr = SecretStr("change-this")
    app_base_url: str = "http://localhost:8000"
    allowed_hosts: str = "localhost,127.0.0.1"
    # #25 · base del endpoint AEAT para el QR Verifactu (RD 1007/2023). Default
    # PRE-PRODUCCIÓN; en Hetzner/producción override con
    # VERIFACTU_QR_BASE_URL="https://www2.aeat.es/wlpl/TIKE-CONT/ValidarQR?"
    # (con el pre-prod hardcodeado el QR sería inescaneable en prod).
    verifactu_qr_base_url: str = (
        "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR?"
    )
    # Versión de la app expuesta vía /admin/settings/about. Override
    # via FULKRO_APP_VERSION en deploy CI (e.g. lectura de pyproject.toml
    # o git describe). Default "dev" para entornos no-deploy.
    app_version: str = "dev"

    # Operacional
    # Datos de contacto del consultor expuestos en pentester-portal y
    # otros flows magic-link cliente. Override via env en producción
    # (FULKRO_CONSULTOR_NAME / FULKRO_CONSULTOR_EMAIL /
    # FULKRO_CONSULTOR_PHONE_EMERGENCY). Default valores no operativos
    # para detectar dev/staging que olvidó override.
    consultor_name: str = "FULKRO Consultor"
    consultor_email: str = "consultor@fulkro.es"
    consultor_phone_emergency: str = "+34 000 000 000"

    # Embeddings
    embeddings_model: str = "intfloat/multilingual-e5-large"
    embeddings_endpoint: str = "http://localhost:8080"

    # WebAuthn
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "FULKRO"

    # OAuth providers — M16 portal connectors (SAN-E v3.MB-4.2.bis · Q2-A)
    # Vacíos por default · Marcos configura via .env real cuando necesite
    # cliente in-portal connectors. AWS NO usa OAuth · IAM access key paste.
    github_client_id: str = ""
    github_client_secret: SecretStr = SecretStr("")
    microsoft_client_id: str = ""
    microsoft_client_secret: SecretStr = SecretStr("")
    microsoft_tenant_id: str = "common"
    azure_client_id: str = ""
    azure_client_secret: SecretStr = SecretStr("")
    azure_tenant_id: str = "common"
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    base_client_id: str = ""
    base_client_secret: SecretStr = SecretStr("")
    base_oauth_authorize_url: str = ""
    base_oauth_token_url: str = ""
    base_oauth_scopes: str = ""

    # Backup (Motor 26)
    pgbackrest_stanza: str = "fulkro"
    backup_s3_endpoint: str = ""
    backup_s3_bucket: str = "fulkro-backups"
    backup_s3_access_key: str = ""
    backup_s3_secret_key: SecretStr = SecretStr("")
    backup_encryption_key: SecretStr = SecretStr("")

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = "FULKRO <noreply@fulkro.es>"
    smtp_use_tls: bool = True
    # Backend selector + Postmark token (TODO-EMAIL-SENDER-CONSOLIDATION-001):
    # antes leídos vía ``os.environ`` directo en EmailSender; centralizados
    # aquí para single source of truth (Settings env).
    email_backend: str = "mock"  # one of: smtp · postmark_api · mock
    postmark_api_token: SecretStr = SecretStr("")

    # SAN-D MB-16.3 · WhatsApp info-only en pie email (ADR-039 modelo
    # Marcos). Si vacío → degradación elegante · pie email NO incluye
    # sección WhatsApp. Si set → texto plano "+34 666 123 456" con
    # espacios legibles · NO link clickeable · cliente copia/pega
    # manualmente si decide. NO automatización pushy.
    marcos_whatsapp_number: str = ""
    marcos_whatsapp_hours: str = "de 9:00 a 18:00 L-V"

    # SAN-E MB-8 atom 8.1 · M31 WhatsApp Business Cloud API (Q1.B 360dialog)
    # Provider switch · 'mock' default permite tests + dev sin KYC done.
    # KYC Meta Business 360dialog (1-2 semanas) paralelo · NO bloquea backend.
    whatsapp_provider: str = "mock"  # 'mock' | '360dialog'
    dialog_360_api_key: SecretStr = SecretStr("")
    dialog_360_phone_number_id: str = ""
    dialog_360_webhook_secret: SecretStr = SecretStr("")
    # Plantilla aprobada para el OTP de opt-in (primer contacto · WhatsApp exige
    # plantilla para mensajes business-initiated). Ej. plantilla de autenticación
    # con {{1}}=código. Vacío → fallback a texto libre (solo válido en mock/dev
    # o dentro de la ventana de 24h). Override env: DIALOG_360_OTP_TEMPLATE.
    dialog_360_otp_template: str = ""

    # SAN-D MB-16.4 · email destino notificaciones admin generadas por
    # NotificationOrchestrator (ej. client_inactivity_admin) Y email de
    # identidad de login del admin (single-admin Marcos). Override via
    # FULKRO_MARCOS_ADMIN_EMAIL en deploy si Marcos rota dominio.
    marcos_admin_email: str = "marcosmata@fulkro.es"

    # SAN-D MB-16.4 · umbral inactividad cliente (días) para alert
    # client_inactivity. Default 14d (2 semanas). Si Marcos lo rebaja
    # vía env (ej. 7) recibirá más alerts; si sube (ej. 30) menos.
    client_inactivity_threshold_days: int = 14

    # SAN-D MB-18 · datos cuenta bancaria Marcos para
    # ManualTransferProvider info-mode (ADR-040 modelo B2B consultoría).
    # Si MARCOS_BANK_IBAN vacío → degradación elegante · email factura
    # NO incluye sección instrucciones transferencia (Marcos las añade
    # a mano editando email Postmark template antes de enviar).
    # NO link clickeable · NO botón "Copiar IBAN" · cliente selecciona
    # y copia manualmente (cross-reference filosofía WhatsApp MB-16
    # cero automatización pushy).
    marcos_bank_iban: str = ""
    marcos_bank_holder: str = "Marcos Mata García"
    marcos_bank_institution: str = "Banco Santander"
    marcos_bank_bic: str = ""  # opcional · solo SEPA internacional

    # A14 Copilot RAG (Motor 11)
    # Confidence threshold por debajo del cual se considera "corpus gap"
    # (top-K hybrid search insuficiente · activa fallback prompt LLM).
    # Override env: FULKRO_CORPUS_GAP_CONFIDENCE_THRESHOLD.
    # Refs: SAN-B.MB-6.6 cierre TODO-S11-POST-FASE11-COPILOT-CORPUS-GAP-THRESHOLD-001.
    corpus_gap_confidence_threshold: float = 0.45

    # MCP wire-up flag (Motor 8 verification)
    # Cuando true, runners m08 (lynis/nmap/nuclei/openvas/prowler/scoutsuite/
    # testssl/zap/dns_checker/ad_password) intentan invocar MCP wrapper antes
    # de fallback al subprocess directo. Override env: USE_MCP_REAL.
    # Refs: SAN-B.MB-7.1 cierre TODO-MCP-G1 + TODO-FASE-13-MCPS-FULL-MIGRATION-001.
    use_mcp_real: bool = False

    # Sub-atom 1.D.X.B v3.12 · production-safety guard m_cloud_connectors.
    # Cuando False (DEFAULT · prod-safe) · trigger_sync con m16_credentials=None
    # raises MockModeNotAllowedError. Solo establecer True para dev/test/piloto
    # demo donde quieres que el flujo "Forzar sync" sin OAuth devuelva 0 resources
    # sin tocar el cloud cliente. NEVER enable in production · auto-resolve gaps
    # con dataset vacío puede borrar trazabilidad ENAC silenciosamente.
    # Override env: CLOUD_MOCK_MODE_ALLOWED=true.
    # Detected by 1.D.X.VERIFY audit · production-safety blindaje.
    cloud_mock_mode_allowed: bool = False

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        # Permitir env vars no declaradas como fields de Settings
        # (ej. FULKRO_AUTH_PRIVATE_KEY que se lee directo desde
        # os.environ en backend.app.auth.crypto._load_keys, no
        # vía Settings). Sin esto, pydantic-settings v2 lanza
        # "extra_forbidden" al ver vars no declaradas.
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
