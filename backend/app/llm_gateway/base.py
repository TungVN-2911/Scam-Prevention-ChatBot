from typing import Protocol

class LLMGateway(Protocol):
    def generate(self, prompt: str, context: str = "") -> str: ...