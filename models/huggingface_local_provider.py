import torch
from langchain_community.llms.llamacpp import LlamaCpp
from langchain_huggingface import HuggingFacePipeline
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from models.base_llm_provider import BaseLLMProvider

class HuggingFaceLocalProvider(BaseLLMProvider):
    def __init__(self, hf_token: str):
        """
        @desc Khởi tạo provider HuggingFace cục bộ với token xác thực
        @params hf_token (str): Token xác thực HuggingFace dùng để tải model
        """
        self.hf_token = hf_token

    def create_model(self, model_name:str, temperature: float, **kwargs):
        """
        @desc Khởi tạo model ngôn ngữ cục bộ — hỗ trợ định dạng GGUF (qua LlamaCpp) và HuggingFace thông thường (qua pipeline 4-bit quantization)
        @params model_name (str): Tên model HuggingFace hoặc đường dẫn file .gguf
        @params temperature (float): Nhiệt độ sinh văn bản
        @params kwargs (Any): Tham số bổ sung như max_tokens, n_ctx, max_new_tokens
        @return LlamaCpp | HuggingFacePipeline: Đối tượng model đã khởi tạo tương ứng với định dạng đầu vào
        """
        if model_name.endswith(".gguf"):
            from core.logger import custom_logger
            custom_logger.info(f"[HuggingFaceLocal] Loading GGUF model from: {model_name}")
            return LlamaCpp(
                model_path=model_name,
                temperature=temperature,
                max_tokens=kwargs.get("max_tokens", 512),
                n_ctx=kwargs.get("n_ctx", 2048),
                n_gpu_layers=-1,
                verbose=False,
            )

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )

        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            token=self.hf_token,
            trust_remote_code=True
        )

        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=bnb_config,
            device_map="auto",
            low_cpu_mem_usage=True,
            token=self.hf_token,
            trust_remote_code=True
        )

        model_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=kwargs.get("max_new_tokens", 512),
            pad_token_id=tokenizer.eos_token_id,
            temperature=temperature,
            repetition_penalty=1.1,
            top_p=0.9,
        )

        return HuggingFacePipeline(pipeline=model_pipeline)