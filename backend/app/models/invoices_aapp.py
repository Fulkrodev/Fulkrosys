"""Invoice AAPP model · SAN-C MB-11.3.

Facturas para AAPP con metadata DIR3 (Oficina Contable, Órgano Gestor,
Unidad Tramitadora) + Facturae 3.2.x XML + XAdES signed flag +
seguimiento payment_due_date Ley 3/2004 morosidad.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class InvoiceAapp(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "invoices_aapp"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"),
        nullable=False, index=True,
    )
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    amount_eur: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # DIR3 mandatory para AAPP (Orden HAP/1074/2014 + 492/2014)
    dir3_oficina_contable: Mapped[str] = mapped_column(String(20), nullable=False)
    dir3_organo_gestor: Mapped[str] = mapped_column(String(20), nullable=False)
    dir3_unidad_tramitadora: Mapped[str] = mapped_column(String(20), nullable=False)

    facturae_xml: Mapped[str | None] = mapped_column(Text)
    facturae_xml_signed: Mapped[str | None] = mapped_column(Text)

    submitted_to_face_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    face_reference: Mapped[str | None] = mapped_column(String(100))

    # Ley 3/2004 morosidad: 30 días desde conformidad factura
    payment_due_date: Mapped[date | None] = mapped_column(Date)
    paid_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    interest_owed_eur: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False,
    )
    """draft · submitted · accepted · paid · late · disputed."""
