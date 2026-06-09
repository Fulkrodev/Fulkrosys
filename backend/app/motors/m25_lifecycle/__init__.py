"""Motor 25 - Project Lifecycle & Archival Engine.

Gestiona el ciclo de vida completo del proyecto: DRAFT → PURGED.
State machine con transiciones explícitas. Archive packages con SHA-256
+ firma Ed25519. Purge condicionado a purge_after <= hoy.

Reutiliza modelos existentes ProjectLifecycleState y ArchivedProject.
"""
