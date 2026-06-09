"""MB-18 auto-billing milestone + transferencia manual (ADR-040).

Centraliza factura per milestone-completion + email cliente con datos
cuenta bancaria + admin reconciliación manual. Modelo
**transferencia bancaria estándar B2B consultoría · cero providers
externos (Stripe/Redsys/Tink descartados).**
"""
from backend.app.billing.manual_transfer import (  # noqa: F401
    BankInstructions,
    ManualTransferProvider,
)
from backend.app.billing.milestone_factory import (  # noqa: F401
    MilestoneFactory,
    MilestoneFactoryError,
)
from backend.app.billing.auto_billing import (  # noqa: F401
    AutoBillingService,
    AutoBillingError,
    BillMilestoneOutcome,
)
