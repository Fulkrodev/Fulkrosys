"""Motor 26 — Backup Engine exception hierarchy.

Patron consistente con M12 Magic Link (8 excepciones jerarquicas)
y M3 DdA Engine (5 excepciones jerarquicas).
"""


class BackupError(Exception):
    """Base exception for Motor 26 Backup Engine errors."""


class BackupNotFoundError(BackupError):
    """Base for all not-found errors in backup engine."""


class BackupJobNotFoundError(BackupNotFoundError):
    """Backup job not found by id."""


class RetentionPolicyNotFoundError(BackupNotFoundError):
    """Retention policy not found by id or backup_type."""


class RestoreTestNotFoundError(BackupNotFoundError):
    """Restore test not found by id."""


class DrDrillNotFoundError(BackupNotFoundError):
    """DR drill not found by id."""


class IntegrityVerificationNotFoundError(BackupNotFoundError):
    """Integrity verification not found by id."""


class BackupStateError(BackupError):
    """Invalid state transition."""


class BackupValidationError(BackupError):
    """Invalid input data."""
