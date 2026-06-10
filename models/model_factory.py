import os, json
from pathlib import Path

from dotenv import load_dotenv
from common.model_type import ModelType
from models.huggingface_local_provider import HuggingFaceLocalProvider
from models.huggingface_provider import HuggingFaceProvider
from models.ollama_provider import OllamaProvider
from models.open_ai_provider import OpenAIProvider

load_dotenv()

class ModelFactory:
    def __init__(self, config_path: str = None):
        if config_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.config_path = str(base_dir / "config" / "models_config.json")
        else:
            self.config_path = config_path

        self.model_configs = self._load_config()
        self._loaded_models = {}

    def _load_config(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Không tìm thấy file config tại: {self.config_path}")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {m['id']: m for m in data['models']}

    def _get_provider_instance(self, provider_type: str, token: str):
        """Khởi tạo Provider dựa trên loại và token tương ứng"""
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
        Lấy model dựa trên ID trong file JSON.
        Cho phép ghi đè (override) các tham số như temperature nếu cần.
        """
        if model_id not in self.model_configs:
            raise ValueError(f"Model ID '{model_id}' chưa được cấu hình trong JSON.")

        if model_id in self._loaded_models:
            return self._loaded_models[model_id]

        config = self.model_configs[model_id]

        token = os.getenv(config['env_token_key'])
        if not token:
            print(f"Cảnh báo: Không tìm thấy giá trị cho {config['env_token_key']} trong .env")

        provider = self._get_provider_instance(config['provider'], token)

        final_params = {**config['default_params'], **override_params}

        print(f"--- Đang khởi tạo model: {config['model_name']} (ID: {model_id}) ---")

        model_instance = provider.create_model(
            model_name=config['model_name'],
            **final_params
        )

        if provider == "hf_local":
            self._loaded_models[model_id] = model_instance

        return model_instance