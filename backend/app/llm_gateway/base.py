from typing import Protocol


class LLMGateway(Protocol):
    async def generate(
        self, prompt: str, context: str = "", history: list = None, mcp_session=None
    ) -> str: ...