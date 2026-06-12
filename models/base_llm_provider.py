from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @abstractmethod
    def create_model(self, model_name:str, temperature: float, **kwargs):
        """
        @desc Phương thức trừu tượng — khởi tạo và trả về đối tượng model ngôn ngữ dựa trên tên model và các tham số cấu hình
        @params model_name (str): Tên hoặc đường dẫn đến model cần khởi tạo
        @params temperature (float): Nhiệt độ sinh văn bản, kiểm soát mức độ ngẫu nhiên của đầu ra
        @params kwargs (Any): Các tham số bổ sung tuỳ theo từng nhà cung cấp
        @return Any: Đối tượng model ngôn ngữ đã được khởi tạo
        """
        pass