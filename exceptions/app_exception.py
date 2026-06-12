from constants.error_code import ErrorCode


class AppException(Exception):
    def __init__(self, error_code: ErrorCode):
        """
        @desc Khởi tạo ngoại lệ ứng dụng với mã lỗi định nghĩa sẵn. Gọi constructor của lớp cha với thông điệp lỗi và lưu lại mã lỗi để xử lý sau.
        @params error_code (ErrorCode): Mã lỗi định nghĩa sẵn chứa thông tin HTTP status, code và message
        """
        super().__init__(error_code.message)
        self.error_code = error_code