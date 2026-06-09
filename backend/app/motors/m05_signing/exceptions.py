"""Domain exceptions · M05 signing · SAN-E v3.MB-5.2."""
from __future__ import annotations


class SigningError(Exception):
    """Base error M05 signing."""


class IntentNotFoundError(SigningError):
    """Signing intent no existe o eliminado."""


class IntentExpiredError(SigningError):
    """Signing intent expirado · expires_at < now."""


class InvalidIntentStateError(SigningError):
    """Estado del intent no permite la operación solicitada."""


class StepUpOtpRequiredError(SigningError):
    """Intent requires step-up OTP verified antes de firmar."""


class OtpExpiredError(SigningError):
    """OTP code expirado o nunca sent."""


class OtpInvalidError(SigningError):
    """OTP code incorrecto."""


class OtpMaxAttemptsError(SigningError):
    """Max OTP attempts reached · intent locked."""


class ProjectMismatchError(SigningError):
    """ClientUser intenta acceder a intent de project distinto a su client."""


class HashChainBrokenError(SigningError):
    """Hash chain integrity check failed durante verify."""
