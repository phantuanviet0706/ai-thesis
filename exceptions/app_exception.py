from constants.error_code import ErrorCode


class AppException(Exception):
    def __init__(self, error_code: ErrorCode):
        super().__init__(error_code.message)
        self.error_code = error_code