from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class PromptBuilder(ABC):
    @abstractmethod
    def build_prompt(self, query: str, chunks: List[Dict[str, Any]], conversation_history: Optional[List[Dict[str, str]]] = None, response_mode: str = "KNOWLEDGE_ONLY") -> str:
        """
        Builds a structured prompt for the LLM.
        """
        pass
