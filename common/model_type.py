from enum import Enum

class ModelType(Enum):
    HF_ENDPOINT = 'hf_endpoint'
    HF_API = 'hf_api'
    HF_LOCAL = 'hf_local'
    OPENAI = 'openai'
    GEMINI_AI = 'gemini_ai'
    OLLAMA = 'ollama'