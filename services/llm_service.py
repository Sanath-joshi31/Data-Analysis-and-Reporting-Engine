"""LLM service providing OpenAI client integration with structured outputs and fallback generation."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel
from config.settings import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """Wrapper around OpenAI API supporting structured outputs, temperature control, and resilient fallback."""

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.model_name = self.settings.openai_model
        self.client = None

        if self.api_key and self.api_key.strip():
            try:
                from openai import OpenAI
                kwargs = {"api_key": self.api_key}
                if self.settings.openai_api_base:
                    kwargs["base_url"] = self.settings.openai_api_base
                self.client = OpenAI(**kwargs)
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client: {e}")

    @property
    def is_configured(self) -> bool:
        """Returns True if a live OpenAI API client is configured."""
        return self.client is not None

    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: int = 2500
    ) -> str:
        """Generate a chat response from the configured LLM."""
        if not self.is_configured:
            raise RuntimeError("OpenAI API key is not configured.")

        temp = temperature if temperature is not None else self.settings.openai_temperature
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temp,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Error calling OpenAI chat completion: {e}")
            raise

    def generate_structured_output(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: Optional[float] = None
    ) -> T:
        """Request structured JSON adhering to a Pydantic model schema."""
        if not self.is_configured:
            raise RuntimeError("OpenAI API key is not configured.")

        temp = temperature if temperature is not None else self.settings.openai_temperature
        
        # Format instruction with model schema
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        system_instructions = (
            f"\nYou must return ONLY a valid JSON object strictly matching this JSON Schema:\n{schema_json}\n"
            "Do not include Markdown backticks or commentary outside the JSON object."
        )

        enhanced_messages = list(messages)
        if enhanced_messages and enhanced_messages[0]["role"] == "system":
            enhanced_messages[0] = {
                "role": "system",
                "content": enhanced_messages[0]["content"] + "\n" + system_instructions
            }
        else:
            enhanced_messages.insert(0, {"role": "system", "content": system_instructions})

        try:
            # First attempt: JSON object response format
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=enhanced_messages,
                temperature=temp,
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content or "{}"
            parsed = json.loads(raw_content)
            return response_model.model_validate(parsed)
        except Exception as e:
            logger.warning(f"Standard structured call failed: {e}. Attempting raw text extraction.")
            # Fallback to direct parse
            text = self.generate_chat_completion(enhanced_messages, temperature=temp)
            # Strip backticks
            cleaned = text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed = json.loads(cleaned.strip())
            return response_model.model_validate(parsed)


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
