from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @abstractmethod
    def create_model(self, model_name:str, temperature: float, **kwargs):
        pass