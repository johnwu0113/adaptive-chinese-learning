import os
from dataclasses import dataclass


@dataclass
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    use_mock_llm: bool = str(os.getenv("USE_MOCK_LLM", "true")).strip().lower() not in {"0", "false", "no", "off"}

    @property
    def has_real_llm(self) -> bool:
        return bool(self.openai_api_key) and not self.use_mock_llm


settings = Settings()
