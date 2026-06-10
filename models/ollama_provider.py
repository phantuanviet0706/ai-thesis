import json
import requests
from typing import Optional, Generator, Any

class OllamaProvider:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def create_model(self, model_name: str, **params):
        return OllamaInstance(self.base_url, model_name, **params)

class OllamaInstance:
    def __init__(self, base_url: str, model_name: str, **params):
        self.base_url = base_url
        self.model_name = model_name
        self.default_params = params

    def _prepare_options(self, override_params: dict) -> dict:
        """Merge thông số mặc định với thông số override"""
        options = {**self.default_params, **override_params}

        mapping = {
            "max_new_token": "num_predict",
            "max_tokens": "num_predict",
            "temperature": "temperature",
            "top_p": "top_p",
            "tok_k": "tok_k",
            "context_length": "num_ctx", # Đọc tài liệu dài
            "repeat_penalty": "repeat_penalty",
            "stop": "stop"
        }

        ollama_options = {}
        for k, v in options.items():
            target_key = mapping.get(k, k)
            ollama_options[target_key] = v

        if "num_ctx" not in ollama_options:
            ollama_options["num_ctx"] = 4096

        return ollama_options

    def invoke(self, prompt: str, **kwargs) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": self._prepare_options(kwargs),
            "keep_alive": "1h"
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json().get("response", "")

    def stream(self, prompt: str, **kwargs) -> Generator[Any, None, None]:
        """Gọi model dạng streaming"""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": self._prepare_options(kwargs)
        }

        try:
            with requests.post(url, json=payload, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        chunk_data = json.loads(line)
                        content = chunk_data.get("response", "")
                        # Trả về object có .content để tương thích với code event_generator của bạn
                        yield OllamaResponseChunk(content)

                        if chunk_data.get("done"):
                            break
        except Exception as e:
            print(f"Lỗi Stream Ollama: {e}")
            yield OllamaResponseChunk(f"Error: {str(e)}")

class OllamaResponseChunk:
    def __init__(self, content: str):
        self.content = content

    def __str__(self):
        return self.content