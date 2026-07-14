import time
import logging
import asyncio
from typing import AsyncGenerator
from google import genai
from google.genai import types
from app.ai.interfaces.llm import BaseLLMProvider
from app.core.config import get_settings
from app.ai.config import ai_config

logger = logging.getLogger(__name__)

class GeminiProvider(BaseLLMProvider):
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or ai_config.DEFAULT_LLM_MODEL
        settings = get_settings()
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in configuration.")
        # GenAI SDK uses standard initialization
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # Approximate Gemini 2.0 Flash pricing (per token)
        self.input_cost_per_token = 0.075 / 1_000_000
        self.output_cost_per_token = 0.30 / 1_000_000
        self.last_metrics = {}
        
    async def generate(self, prompt: str) -> str:
        start_time = time.time()
        
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=ai_config.MAX_OUTPUT_TOKENS
            )
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        content = response.text or ""
        
        # Extract metadata
        prompt_tokens = 0
        completion_tokens = 0
        finish_reason = "stop"
        
        if response.usage_metadata:
            prompt_tokens = response.usage_metadata.prompt_token_count or 0
            completion_tokens = response.usage_metadata.candidates_token_count or 0
            
        if response.candidates and len(response.candidates) > 0:
            finish_reason = str(response.candidates[0].finish_reason or "stop").lower()
            
        cost = (prompt_tokens * self.input_cost_per_token) + (completion_tokens * self.output_cost_per_token)
        
        logger.info(
            f"Gemini LLM Call complete:\n"
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
            "raw_completion": content
        }
        
        return content
        
    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        start_time = time.time()
        
        response = await self.client.aio.models.generate_content_stream(
            model=self.model_name,
            contents=prompt,
            temperature=0.7,
            generation_config={"max_output_tokens": ai_config.MAX_OUTPUT_TOKENS},
            stream=True
        )
        
        full_completion = []
        finish_reason = "stop"
        prompt_tokens = 0
        completion_tokens = 0
        
        async for chunk in response:
            if chunk.text:
                full_completion.append(chunk.text)
                yield chunk.text
                
            # Try to grab final usage metadata if populated in a chunk
            if chunk.usage_metadata:
                prompt_tokens = chunk.usage_metadata.prompt_token_count or 0
                completion_tokens = chunk.usage_metadata.candidates_token_count or 0
                
            if chunk.candidates and len(chunk.candidates) > 0:
                finish_reason = str(chunk.candidates[0].finish_reason or "stop").lower()
                
        latency_ms = int((time.time() - start_time) * 1000)
        full_content = "".join(full_completion)
        
        # Fallback token estimation using tiktoken
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
            f"Gemini LLM Stream complete:\n"
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
