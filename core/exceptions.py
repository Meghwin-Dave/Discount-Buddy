class ImageValidationError(Exception):
    """Raised when an uploaded image fails validation."""

    def __init__(self, message: str, code: str = "invalid_image"):
        self.message = message
        self.code = code
        super().__init__(message)


class ImageProcessingError(Exception):
    """Raised when image processing fails in the worker."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
