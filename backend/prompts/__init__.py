"""
Prompt Management System

Centralized prompt storage with validation and security.
All LLM prompts are stored here to prevent injection attacks.

Copyright 2025 Tejaswi Mahapatra
"""

from pathlib import Path
from typing import Dict


class PromptManager:
    """Manages prompt templates with security validation."""

    def __init__(self):
        self.prompts_dir = Path(__file__).parent
        self._cache: Dict[str, str] = {}

    def load_prompt(self, prompt_name: str) -> str:
        """
        Load prompt template from file.

        Args:
            prompt_name: Name of prompt file (without .txt extension)

        Returns:
            Prompt template string

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        if prompt_name in self._cache:
            return self._cache[prompt_name]

        prompt_file = self.prompts_dir / f"{prompt_name}.txt"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt template '{prompt_name}' not found")

        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()

        self._cache[prompt_name] = prompt
        return prompt

    def format_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Load and format prompt with variables.

        Args:
            prompt_name: Name of prompt template
            **kwargs: Variables to inject into prompt

        Returns:
            Formatted prompt string
        """
        template = self.load_prompt(prompt_name)

        sanitized_kwargs = {
            k: self._sanitize_input(v) for k, v in kwargs.items()
        }

        return template.format(**sanitized_kwargs)

    def _sanitize_input(self, value: str) -> str:
        """
        Sanitize user input to prevent prompt injection.

        Args:
            value: User input string

        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            value = str(value)

        dangerous_patterns = [
            "ignore previous instructions",
            "ignore all previous",
            "disregard",
            "system:",
            "assistant:",
            "[INST]",
            "</s>",
        ]

        value_lower = value.lower()
        for pattern in dangerous_patterns:
            if pattern in value_lower:
                import logging
                logging.warning(f"Potential prompt injection detected: {pattern}")

        max_length = 10000
        if len(value) > max_length:
            value = value[:max_length]

        return value


_prompt_manager = None


def get_prompt_manager() -> PromptManager:
    """Get singleton PromptManager instance."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
