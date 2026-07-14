import logging
from typing import AsyncGenerator, Optional
from app.ai.interfaces.llm import BaseLLMProvider
from app.ai.llm.gemini import GeminiProvider
from app.ai.llm.groq_provider import GroqProvider
from app.ai.llm.openrouter_provider import OpenRouterProvider
from app.ai.config import ai_config

logger = logging.getLogger(__name__)

class DynamicLLMProvider(BaseLLMProvider):
    """
    LLM Provider that dynamically wraps Groq and Gemini providers.
    Supports failover / fallback: if the primary provider fails, it transparently
    falls back to the secondary provider.
    """
    def __init__(self, primary_provider_name: Optional[str] = None):
        self.primary_name = primary_provider_name or ai_config.DEFAULT_LLM_PROVIDER
        self.last_metrics = {}
        
    def _get_provider(self, name: str) -> BaseLLMProvider:
        if name.lower() == "gemini":
            return GeminiProvider()
        elif name.lower() == "groq":
            return GroqProvider()
        elif name.lower() == "openrouter":
            return OpenRouterProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {name}")

    async def generate(self, prompt: str) -> str:
        providers_to_try = [self.primary_name]
        secondary = "gemini" if self.primary_name.lower() == "groq" else "groq"
        providers_to_try.append(secondary)
        
        last_err = None
        for prov_name in providers_to_try:
            try:
                logger.info(f"Attempting generate using LLM provider: {prov_name}")
                provider = self._get_provider(prov_name)
                res = await provider.generate(prompt)
                self.last_metrics = getattr(provider, "last_metrics", {})
                return res
            except Exception as e:
                logger.warning(f"LLM provider {prov_name} failed: {e}. Trying fallback...")
                last_err = e
        raise last_err

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        # Provider order: primary, then a secondary, finally OpenRouter as last resort
        providers_to_try = [self.primary_name]
        secondary = "gemini" if self.primary_name.lower() == "groq" else "groq"
        providers_to_try.append(secondary)
        providers_to_try.append("openrouter")  # always try OpenRouter as final fallback
        
        success = False
        last_err = None
        for prov_name in providers_to_try:
            try:
                logger.info(f"Attempting generate_stream using LLM provider: {prov_name}")
                provider = self._get_provider(prov_name)
                async for chunk in provider.generate_stream(prompt):
                    yield chunk
                self.last_metrics = getattr(provider, "last_metrics", {})
                success = True
                break
            except Exception as e:
                # If the error is a rate‑limit / token‑size problem, we want to fall back immediately.
                if "rate_limit_exceeded" in str(e).lower() or "request too large" in str(e).lower():
                    logger.warning(f"{prov_name} hit token limit: {e}. Falling back to next provider.")
                else:
                    logger.warning(f"LLM provider {prov_name} failed in stream: {e}. Trying fallback...")
                last_err = e
                if success:
                    # Already streaming some chunks – we cannot restart safely.
                    raise e
                continue
        if not success:
            raise RuntimeError(f"All LLM providers failed to generate stream. Last error: {last_err}")
