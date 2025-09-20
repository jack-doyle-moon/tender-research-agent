"""Base agent class with common functionality."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import settings


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self, name: str, system_prompt: str) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            api_key=settings.openai_api_key,
        )

    def _create_messages(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """Create message list for LLM."""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if context:
            context_str = f"Context: {json.dumps(context, indent=2)}\n\n"
            user_message = context_str + user_message
        
        messages.append({"role": "user", "content": user_message})
        return messages

    def _parse_json_response(self, response: str, expected_model: type[BaseModel]) -> BaseModel:
        """Parse JSON response and validate against Pydantic model."""
        try:
            # Extract JSON from response if it's wrapped in markdown
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()
            
            # Parse JSON
            data = json.loads(response)
            return expected_model(**data)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse JSON response: {e}\nResponse: {response}")

    @abstractmethod
    def process(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> BaseModel:
        """Process input and return structured output."""
        pass
