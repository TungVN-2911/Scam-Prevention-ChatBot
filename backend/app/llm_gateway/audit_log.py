import logging
from datetime import datetime, timezone

logger = logging.getLogger("llm_audit")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    
def log_call(prompt: str, context: str, response: str) -> None:
    logger.info(
        "[%s] prompt_len=%d context_len=%d response_len=%d",
        datetime.now(timezone.utc).isoformat(),
        len(prompt), len(context), len(response)
    )    