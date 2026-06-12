import os, json
from pathlib import Path

from dotenv import load_dotenv
from constants.model_type import ModelType
from models.huggingface_local_provider import HuggingFaceLocalProvider
from models.huggingface_provider import HuggingFaceProvider
from models.ollama_provider import OllamaProvider
from models.open_ai_provider import OpenAIProvider

load_dotenv()

class ModelFactory:
    def __init__(self, config_path: str = None):
        """
        @desc Khởi tạo ModelFactory, nạp cấu hình model từ file JSON và chuẩn bị cache model đã tải
        @params config_path (str): Đường dẫn tùy chọn đến file cấu hình JSON — mặc định dùng config/models_config.json
        """
        if config_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.config_path = str(base_dir / "config" / "models_config.json")
        else:
            self.config_path = config_path

        self.model_configs = self._load_config()
        self._loaded_models = {}

    def _load_config(self):
        """
        @desc Đọc file cấu hình JSON và trả về dictionary ánh xạ ID model sang thông tin cấu hình tương ứng
        @return dict: Dictionary với key là ID model và value là thông tin cấu hình của model đó
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Không tìm thấy file config tại: {self.config_path}")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {m['id']: m for m in data['models']}

    def _get_provider_instance(self, provider_type: str, token: str):
        """
        @desc Khởi tạo và trả về đối tượng provider phù hợp dựa trên loại provider và token xác thực
        @params provider_type (str): Loại provider (hf_local, openai, hf_api, ollama)
        @params token (str): Token xác thực hoặc URL cơ sở tương ứng với từng loại provider
        @return BaseLLMProvider: Đối tượng provider đã được khởi tạo
        """
        if provider_type == ModelType.HF_LOCAL:
            return HuggingFaceLocalProvider(hf_token=token)
        elif provider_type == ModelType.OPENAI:
            return OpenAIProvider(api_key=token)
        elif provider_type == ModelType.HF_API:
            return HuggingFaceProvider(hf_token=token)
        elif provider_type == ModelType.OLLAMA:
            return OllamaProvider(base_url=token)
        else:
            raise ValueError(f"Provider '{provider_type}' không được hỗ trợ.")

    def get_model(self, model_id: str, **override_params):
        """
        @desc Lấy đối tượng model dựa trên ID trong file cấu hình JSON — hỗ trợ ghi đè tham số và cache model đã khởi tạo
        @params model_id (str): ID định danh của model trong file cấu hình JSON
        @params override_params (Any): Các tham số cần ghi đè so với cấu hình mặc định (ví dụ: temperature)
        @return Any: Đối tượng model ngôn ngữ đã được khởi tạo
        """
        if model_id not in self.model_configs:
            raise ValueError(f"Model ID '{model_id}' chưa được cấu hình trong JSON.")

        if model_id in self._loaded_models:
            return self._loaded_models[model_id]

        config = self.model_configs[model_id]

        from core.logger import custom_logger
        token = os.getenv(config['env_token_key'])
        if not token:
            custom_logger.warning(
                f"[ModelFactory] Missing env var '{config['env_token_key']}' for model '{model_id}'"
            )

        provider = self._get_provider_instance(config['provider'], token)

        final_params = {**config['default_params'], **override_params}

        custom_logger.info(
            f"[ModelFactory] Initializing model='{config['model_name']}' id='{model_id}'"
        )

        model_instance = provider.create_model(
            model_name=config['model_name'],
            **final_params
        )

        if provider == "hf_local":
            self._loaded_models[model_id] = model_instance

        return model_instance