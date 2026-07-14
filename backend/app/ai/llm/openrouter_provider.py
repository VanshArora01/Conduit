import time
import json
import logging
import httpx
from typing import AsyncGenerator
from app.ai.interfaces.llm import BaseLLMProvider
from app.core.config import get_settings
from app.ai.config import ai_config

logger = logging.getLogger(__name__)

class OpenRouterProvider(BaseLLMProvider):
    def __init__(self, model_name: str | None = None):
        # OpenRouter offers completely free tiers for many models.
        self.model_name = model_name or "meta-llama/llama-3-8b-instruct:free"
        
        if not self.model_name.strip():
            raise ValueError("LLM model name is empty or invalid.")
            
        settings = get_settings()
        self.api_key = getattr(settings, "OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set or invalid in configuration.")
            
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Conduit AI OS",
            "Content-Type": "application/json"
        }
        
        # Free models on OpenRouter generally cost $0
        self.input_cost_per_token = 0.0
        self.output_cost_per_token = 0.0

    async def generate(self, prompt: str) -> str:
        start_time = time.time()
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=ai_config.TIMEOUT_LLM) as client:
            response = await client.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
        latency_ms = int((time.time() - start_time) * 1000)
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        finish_reason = choice.get("finish_reason", "stop")
        
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        cost = (prompt_tokens * self.input_cost_per_token) + (completion_tokens * self.output_cost_per_token)
        
        logger.info(
            f"OpenRouter LLM Call complete:\n"
            f"  Model: {self.model_name}\n"
            f"  Latency: {latency_ms}ms\n"
            f"  Finish Reason: {finish_reason}\n"
            f"  Prompt Tokens: {prompt_tokens}\n"
            f"  Completion Tokens: {completion_tokens}\n"
            f"  Estimated Cost: ${cost:.6f}\n"
            f"  Raw Completion: {content[:200]}..."
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
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "stream": True
        }
        
        full_completion = []
        finish_reason = None
        prompt_tokens = 0
        completion_tokens = 0
        
        async with httpx.AsyncClient(timeout=ai_config.TIMEOUT_LLM) as client:
            async with client.stream("POST", self.base_url, headers=self.headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if line == "data: [DONE]":
                        break
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            choice = data.get("choices", [{}])[0]
                            delta = choice.get("delta", {})
                            content = delta.get("content")
                            if content:
                                full_completion.append(content)
                                yield content
                            if choice.get("finish_reason"):
                                finish_reason = choice.get("finish_reason")
                                
                            if "usage" in data and data["usage"]:
                                prompt_tokens = data["usage"].get("prompt_tokens", 0)
                                completion_tokens = data["usage"].get("completion_tokens", 0)
                        except json.JSONDecodeError:
                            continue
                            
        latency_ms = int((time.time() - start_time) * 1000)
        full_content = "".join(full_completion)
        finish_reason = finish_reason or "stop"
        
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
            f"OpenRouter LLM Stream complete:\n"
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
