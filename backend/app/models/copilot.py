"""M11 Copiloto - conversaciones y mensajes persistentes."""
import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class CopilotConversation(FullMixin, Base):
    __tablename__ = "copilot_conversations"

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), index=True,
    )
    # Sesión 3B-2B.4 Phase 2.1 · memoria per cliente foundation (audit
    # Phase 0 D2 gap A). Nullable backward-compat · backfilled via project FK
    # en migración s3b2b4_copilot_client_id_001. Enables scoping conversations
    # per cliente independiente del proyecto activo (multi-project per cliente
    # future).
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clients.id"), index=True,
    )
    titulo: Mapped[str | None] = mapped_column(String(300))
    modelo_default: Mapped[str | None] = mapped_column(String(60))
    autor: Mapped[str | None] = mapped_column(String(200), default="marcos")


class CopilotMessage(FullMixin, Base):
    __tablename__ = "copilot_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("copilot_conversations.id"), nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # "user" | "assistant" | "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[dict | None] = mapped_column(JSONB)
    chunk_ids_used: Mapped[dict | None] = mapped_column(JSONB)
    model_used: Mapped[str | None] = mapped_column(String(60))
    tokens_input: Mapped[int | None] = mapped_column(Integer)
    tokens_output: Mapped[int | None] = mapped_column(Integer)
