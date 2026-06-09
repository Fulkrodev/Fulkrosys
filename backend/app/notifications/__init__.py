"""NotificationOrchestrator MB-16 (ADR-039).

Centraliza despacho cross-canal con preferencias usuario + DND
timezone-aware + retry + audit immutable. Modelo email-first +
SSE-complementario + WhatsApp-info-opcional.
"""
from backend.app.notifications.orchestrator import (  # noqa: F401
    NotificationOrchestrator,
    OrchestratorError,
    DispatchOutcome,
)
from backend.app.notifications.dnd import (  # noqa: F401
    is_dnd_active,
    parse_hhmm,
)
from backend.app.notifications.deep_links import (  # noqa: F401
    DeepLinkGenerator,
)
from backend.app.notifications.whatsapp_info import (  # noqa: F401
    WhatsAppInfo,
    WhatsAppInfoFormatter,
)
from backend.app.notifications.templates_resolver import (  # noqa: F401
    RenderedTemplate,
    TemplateError,
    TemplateResolver,
    clear_template_cache,
)
