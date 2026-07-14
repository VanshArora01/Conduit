import time
import logging
import asyncio
from typing import AsyncGenerator
from groq import AsyncGroq
from app.ai.interfaces.llm import BaseLLMProvider
from app.core.config import get_settings
from app.ai.config import ai_config

logger = logging.getLogger(__name__)

class GroqProvider(BaseLLMProvider):
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or "llama-3.1-8b-instant"
        
        # Verify model name
        if not self.model_name.strip():
            raise ValueError("LLM model name is empty or invalid.")
            
        settings = get_settings()
        # Verify authentication
        if not settings.GROQ_API_KEY or not settings.GROQ_API_KEY.startswith("gsk_"):
            raise ValueError("GROQ_API_KEY is not set or invalid in configuration.")
            
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        
        # approximate Llama 3 70B pricing on Groq (per token)
        self.input_cost_per_token = 0.59 / 1_000_000
        self.output_cost_per_token = 0.79 / 1_000_000

    async def generate(self, prompt: str) -> str:
        # We also want to record metrics for this LLM call
        start_time = time.time()
        
        # Groq client will throw an error on timeout if configured
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=ai_config.MAX_OUTPUT_TOKENS,
            timeout=ai_config.TIMEOUT_LLM
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        choice = response.choices[0]
        content = choice.message.content or ""
        finish_reason = choice.finish_reason or "stop"
        
        # Token usage
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        cost = (prompt_tokens * self.input_cost_per_token) + (completion_tokens * self.output_cost_per_token)
        
        logger.info(
            f"Groq LLM Call complete:\n"
            f"  Model: {self.model_name}\n"
            f"  Latency: {latency_ms}ms\n"
            f"  Finish Reason: {finish_reason}\n"
            f"  Prompt Tokens: {prompt_tokens}\n"
            f"  Completion Tokens: {completion_tokens}\n"
            f"  Estimated Cost: ${cost:.6f}\n"
            f"  Raw Completion: {content[:200]}..."
        )
        
        # Save metrics on the provider instance so the caller can extract them if needed
        self.last_metrics = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": latency_ms,
            "finish_reason": finish_reason,
            "cost": cost,
            "raw_completion": content
        }
        
        return content

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        start_time = time.time()
        
        stream = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=ai_config.MAX_OUTPUT_TOKENS,
            stream=True,
            timeout=ai_config.TIMEOUT_LLM
        )
        
        full_completion = []
        finish_reason = None
        prompt_tokens = 0
        completion_tokens = 0
        
        async for chunk in stream:
            if chunk.choices:
                choice = chunk.choices[0]
                content = choice.delta.content
                if content:
                    full_completion.append(content)
                    yield content
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
            
            # Check for usage info in the stream chunk
            if hasattr(chunk, "x_groq") and chunk.x_groq and chunk.x_groq.usage:
                usage = chunk.x_groq.usage
                prompt_tokens = usage.prompt_tokens
                completion_tokens = usage.completion_tokens
            elif hasattr(chunk, "usage") and chunk.usage:
                usage = chunk.usage
                prompt_tokens = usage.prompt_tokens
                completion_tokens = usage.completion_tokens
                
        latency_ms = int((time.time() - start_time) * 1000)
        full_content = "".join(full_completion)
        finish_reason = finish_reason or "stop"
        
        # Fallback token estimation using tiktoken if Groq stream didn't include usage
        if prompt_tokens == 0:
            import tiktoken
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
                prompt_tokens = len(encoding.encode(prompt))
                completion_tokens = len(encoding.encode(full_content))
            except Exception:
                prompt_tokens = len(prompt.split())
                completion_tokens = len(full_content.split())
                
        cost = (prompt_tokens * self.input_cost_per_token) + (completion_tokens * self.output_cost_per_token)
        
        logger.info(
            f"Groq LLM Stream complete:\n"
            f"  Model: {self.model_name}\n"
            f"  Latency: {latency_ms}ms\n"
            f"  Finish Reason: {finish_reason}\n"
            f"  Prompt Tokens: {prompt_tokens}\n"
            f"  Completion Tokens: {completion_tokens}\n"
            f"  Estimated Cost: ${cost:.6f}"
        )
        
        self.last_metrics = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": latency_ms,
            "finish_reason": finish_reason,
            "cost": cost,
            "raw_completion": full_content
        }
