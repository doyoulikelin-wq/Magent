from app.core.config import settings
from app.providers.base import LLMProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.mock_provider import MockProvider
from app.providers.openai_provider import OpenAIProvider


def get_provider() -> LLMProvider:
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        if settings.OPENAI_API_KEY:
            return OpenAIProvider()
        return MockProvider()

    if provider == "gemini":
        if settings.GEMINI_API_KEY:
            return GeminiProvider()
        return MockProvider()

    return MockProvider()
