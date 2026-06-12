from langchain_huggingface import HuggingFaceEndpoint
from models.base_llm_provider import BaseLLMProvider

class HuggingFaceProvider(BaseLLMProvider):
    def __init__(self, hf_token: str):
        """
        @desc Khởi tạo provider HuggingFace API với token xác thực
        @params hf_token (str): Token xác thực HuggingFace dùng để gọi Inference API
        """
        self.hf_token = hf_token

    def create_model(self, model_name:str, temperature: float, **kwargs):
        """
        @desc Khởi tạo model ngôn ngữ thông qua HuggingFace Inference Endpoint API
        @params model_name (str): Tên model trên HuggingFace Hub
        @params temperature (float): Nhiệt độ sinh văn bản
        @params kwargs (Any): Tham số bổ sung như max_new_token, max_new_tokens
        @return HuggingFaceEndpoint: Đối tượng model endpoint đã khởi tạo
        """
        max_tokens = kwargs.get('max_new_token') or kwargs.get('max_new_tokens')

        return HuggingFaceEndpoint(
            model=model_name,
            temperature=temperature,
            huggingfacehub_api_token=self.hf_token,
            max_new_tokens=max_tokens,
            timeout=300,
            **{k: v for k, v in kwargs.items() if k not in ['max_new_token', 'max_new_tokens']}
        )