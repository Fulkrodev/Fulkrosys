"""Motor Meetings — reuniones externas + interlocutor M30 (FASE 7).

ADR-024 supersedes ADR-004 (videocall propio cancelado).

Arquitectura:
  - Modelo `ExploratoryMeetingRow` en
    `backend/app/models/conformity_lifecycle.py:302` (path mantenido
    por dominio compartido H5 audit pre-FASE 7).
  - Service core (CRUD + workflow + cross-motor M30).
  - API `/api/v1/admin/meetings` con `require_owner` router-level.
  - SSE A18 stream para insight live (TODO-A18-LATENCY RESOLVED).
  - PostMeetingActions: 4 acciones cross-motor (A19/projects/M12/email).

Cross-motor:
  - M30 log_interaction(meeting_attended) al complete_meeting.
  - A19 RedactorPropuestasAgent para P-001.
  - M12 magic link FIRMA_DOCUMENTO para K.6 firma.
  - EmailSender consolidado para resúmenes out-of-band.
"""
