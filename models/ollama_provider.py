import json
import requests
from typing import Optional, Generator, Any

class OllamaProvider:
    def __init__(self, base_url: str):
        """
        @desc Khởi tạo OllamaProvider với địa chỉ URL cơ sở của Ollama server
        @params base_url (str): URL cơ sở của Ollama API server (ví dụ: http://localhost:11434)
        """
        self.base_url = base_url

    def create_model(self, model_name: str, **params):
        """
        @desc Tạo và trả về một đối tượng OllamaInstance để tương tác với model được chỉ định
        @params model_name (str): Tên model Ollama cần sử dụng
        @params params (Any): Các tham số mặc định cho model như temperature, top_p, context_length
        @return OllamaInstance: Đối tượng instance đã được cấu hình để gọi model Ollama
        """
        return OllamaInstance(self.base_url, model_name, **params)

class OllamaInstance:
    def __init__(self, base_url: str, model_name: str, **params):
        """
        @desc Khởi tạo OllamaInstance với thông tin kết nối và các tham số mặc định cho model
        @params base_url (str): URL cơ sở của Ollama API server
        @params model_name (str): Tên model Ollama cần sử dụng
        @params params (Any): Các tham số mặc định cho model (temperature, top_p, v.v.)
        """
        self.base_url = base_url
        self.model_name = model_name
        self.default_params = params

    def _prepare_options(self, override_params: dict) -> dict:
        """
        @desc Gộp các tham số mặc định với tham số ghi đè và chuyển đổi tên key sang định dạng Ollama API
        @params override_params (dict): Dictionary các tham số cần ghi đè so với cấu hình mặc định
        @return dict: Dictionary các tùy chọn đã được chuẩn hóa theo định dạng Ollama API
        """
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
        """
        @desc Gọi model Ollama theo chế độ đồng bộ và trả về toàn bộ phản hồi dạng chuỗi
        @params prompt (str): Nội dung prompt gửi đến model
        @params kwargs (Any): Các tham số tùy chọn ghi đè cấu hình mặc định
        @return str: Chuỗi phản hồi đầy đủ từ model
        """
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
        """
        @desc Gọi model Ollama theo chế độ streaming — sinh ra từng chunk phản hồi dưới dạng OllamaResponseChunk
        @params prompt (str): Nội dung prompt gửi đến model
        @params kwargs (Any): Các tham số tùy chọn ghi đè cấu hình mặc định
        @return Generator[OllamaResponseChunk, None, None]: Generator sinh ra từng chunk phản hồi từ model
        """
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
            from core.logger import custom_logger
            custom_logger.error(f"[Ollama] Stream error | model={self.model_name} | error={e}", exc_info=True)
            yield OllamaResponseChunk(f"Error: {str(e)}")

class OllamaResponseChunk:
    def __init__(self, content: str):
        """
        @desc Khởi tạo một chunk phản hồi từ Ollama với nội dung văn bản tương ứng
        @params content (str): Nội dung văn bản của chunk phản hồi
        """
        self.content = content

    def __str__(self):
        """
        @desc Trả về nội dung văn bản của chunk khi chuyển đổi sang chuỗi
        @return str: Nội dung văn bản của chunk phản hồi
        """
        return self.content