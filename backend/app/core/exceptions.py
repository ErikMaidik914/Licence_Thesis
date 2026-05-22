class BusinessException(Exception):
    """
    Exception for business rule violations mapped to HTTP 400.
    """
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class NotFoundException(Exception):
    """
    Exception for missing resources mapped to HTTP 404.
    """
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message