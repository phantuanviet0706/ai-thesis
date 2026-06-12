from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from models.base_llm_provider import BaseLLMProvider

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        """
        @desc Khởi tạo OpenAI provider với API key xác thực
        @params api_key (str): API key dùng để xác thực với OpenAI API
        """
        self.api_key = api_key

    def create_model(self, model_name: str, temperature: float, **kwargs):
        """
        @desc Khởi tạo model ChatOpenAI với tên model, nhiệt độ và các tham số bổ sung
        @params model_name (str): Tên model OpenAI cần sử dụng (ví dụ: gpt-4o, gpt-4o-mini)
        @params temperature (float): Nhiệt độ sinh văn bản
        @params kwargs (Any): Các tham số bổ sung truyền thẳng vào ChatOpenAI
        @return ChatOpenAI: Đối tượng model ChatOpenAI đã khởi tạo
        """
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=SecretStr(self.api_key),
            **kwargs
        )