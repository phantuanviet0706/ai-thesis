from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from models.base_llm_provider import BaseLLMProvider

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def create_model(self, model_name: str, temperature: float, **kwargs):
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=SecretStr(self.api_key),
            **kwargs
        )