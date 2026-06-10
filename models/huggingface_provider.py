from langchain_huggingface import HuggingFaceEndpoint
from models.base_llm_provider import BaseLLMProvider

class HuggingFaceProvider(BaseLLMProvider):
    def __init__(self, hf_token: str):
        self.hf_token = hf_token

    def create_model(self, model_name:str, temperature: float, **kwargs):
        max_tokens = kwargs.get('max_new_token') or kwargs.get('max_new_tokens')

        return HuggingFaceEndpoint(
            model=model_name,
            temperature=temperature,
            huggingfacehub_api_token=self.hf_token,
            max_new_tokens=max_tokens,
            timeout=300,
            **{k: v for k, v in kwargs.items() if k not in ['max_new_token', 'max_new_tokens']}
        )