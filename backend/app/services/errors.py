"""Erreurs métier, traduites en codes HTTP par main.py : {"detail": message, ...extra}."""


class ServiceError(Exception):
    status_code = 422

    def __init__(self, message: str, **extra):
        super().__init__(message)
        self.message, self.extra = message, extra


class NotFound(ServiceError):
    status_code = 404


class Invalid(ServiceError):
    status_code = 422


class ConfirmationRequired(ServiceError):
    status_code = 409
