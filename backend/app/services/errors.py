class ServiceError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFound(ServiceError):
    status_code = 404


class Conflict(ServiceError):
    status_code = 409


class BadRequest(ServiceError):
    status_code = 400


class Unprocessable(ServiceError):
    """The request was fine but the camera/vision could not do it (retryable)."""

    status_code = 422
