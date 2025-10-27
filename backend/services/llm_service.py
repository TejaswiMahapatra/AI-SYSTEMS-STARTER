"""
LLM Service - Unified interface for language model generation.

Supports multiple providers: Ollama (local), OpenAI, Anthropic
Handles prompt formatting, streaming, and error recovery.

Copyright 2025 Tejaswi Mahapatra
"""

import logging
from typing import Optional, AsyncGenerator
import httpx
from backend.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM text generation with multiple provider support."""

    def __init__(self):
        self.provider = settings.llm_provider
        self.model_name = self._get_model_name()

    def _get_model_name(self) -> str:
        """Get model name based on provider."""
        if self.provider == "ollama":
            return settings.ollama_model
        elif self.provider == "openai":
            return "gpt-4-turbo-preview"
        elif self.provider == "anthropic":
            return "claude-3-sonnet-20240229"
        return "llama3.1:8b"

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.1,
        stop: Optional[list] = None
    ) -> str:
        """
        Generate text completion from prompt.

        Args:
            prompt: Input prompt text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            stop: Stop sequences

        Returns:
            Generated text string

        Raises:
            Exception: If generation fails
        """
        if self.provider == "ollama":
            return await self._generate_ollama(prompt, max_tokens, temperature, stop)
        elif self.provider == "openai":
            return await self._generate_openai(prompt, max_tokens, temperature, stop)
        elif self.provider == "anthropic":
            return await self._generate_anthropic(prompt, max_tokens, temperature, stop)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    async def _generate_ollama(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stop: Optional[list]
    ) -> str:
        """Generate using Ollama local LLM."""
        try:
            url = f"{settings.ollama_url}/api/generate"
            payload = {
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "stop": stop or [],
                }
            }

            logger.info(f"Ollama request to {url} with model {settings.ollama_model}")

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(url, json=payload)

                if response.status_code != 200:
                    logger.error(f"Ollama returned {response.status_code}: {response.text[:200]}")

                response.raise_for_status()
                data = response.json()
                return data["response"]

        except httpx.TimeoutException:
            logger.error("Ollama request timed out")
            raise Exception("LLM request timed out. The model may be overloaded.")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e}")
            logger.error(f"Response content: {e.response.text[:500]}")
            raise Exception(f"LLM service error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    async def _generate_openai(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stop: Optional[list]
    ) -> str:
        """Generate using OpenAI."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

    async def _generate_anthropic(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stop: Optional[list]
    ) -> str:
        """Generate using Anthropic Claude."""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            response = await client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                stop_sequences=stop,
            )
            return response.content[0].text

        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise

    async def stream(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.1
    ) -> AsyncGenerator[str, None]:
        """
        Stream text generation token by token.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Yields:
            Text tokens as they are generated
        """
        if self.provider == "ollama":
            async for token in self._stream_ollama(prompt, max_tokens, temperature):
                yield token
        else:
            response = await self.generate(prompt, max_tokens, temperature)
            for word in response.split():
                yield word + " "

    async def _stream_ollama(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> AsyncGenerator[str, None]:
        """Stream from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{settings.ollama_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "stream": True,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature,
                        }
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            import json
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]

        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            raise


def get_llm_service() -> LLMService:
    """Get LLM service instance."""
    return LLMService()
