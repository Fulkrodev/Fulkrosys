"""m_audit_accompaniment · post-implantación audit accompaniment cycle motor.

Sesión 3B-4 Ejecutable 7.5 (2026-05-27).

Tracks ENS audit accompaniment cycle post-implantación:
- BÁSICO category: 7 states (autodeclaración · NO ENAC · incl. comunicación al CCN/AMPARO)
- MEDIO/ALTO category: 11 states unified (ENAC certification + biannual renewal)

Patterns reused:
- #18 state machine canonical (corrective_loop_service Ejecutable 5 reference)
- #22 advisory lock per project_id (Ejecutable 6 mirror audit_log)
- #14 SSE + ClientNotification dual emit (auto-trigger cliente updates)
- #21 SSE event_id + Last-Event-ID (cliente resume on reconnect)
- P-CL2-4 ENRICH project page (admin tab embed dentro existing /audit)

Cliente-mínimo filosofía: cliente RECIBE timeline updates · NO opera proceso ·
admin advances state · auto-SSE emit cliente realtime.
"""
