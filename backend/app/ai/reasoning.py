import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.ai.llm.manager import DynamicLLMProvider

logger = logging.getLogger(__name__)

class ExecutionPlan(BaseModel):
    intent: str = Field(description="One of: DOCUMENT, GENERAL, HYBRID")
    response_mode: str = Field(description="One of: KNOWLEDGE_ONLY, GENERAL_ONLY, HYBRID, AUTO")
    knowledge_mode: str = Field(description="One of: KNOWLEDGE_BASE, NONE, HYBRID, AUTO")
    tools: List[str] = Field(description="List of tools to execute, e.g., ['retrieval']")
    rewritten_query: Optional[str] = Field(description="Optimized query for vector search, if applicable", default=None)

class FastIntentRouter:
    """
    Lightweight heuristic router to bypass LLM for simple queries.
    """
    def __init__(self):
        self.general_keywords = {"hi", "hello", "thanks", "ok", "okay", "bye"}
    
    def route(self, query: str) -> Optional[ExecutionPlan]:
        q_lower = query.strip().lower()
        
        # Simple greetings or short non-questions
        if q_lower in self.general_keywords or (len(q_lower.split()) < 3 and "who" not in q_lower and "what" not in q_lower and "how" not in q_lower and "why" not in q_lower):
            return ExecutionPlan(
                intent="GENERAL",
                response_mode="GENERAL_ONLY",
                knowledge_mode="NONE",
                tools=[],
                rewritten_query=None
            )
            
        # Obvious document requests
        if q_lower.startswith("summarize this") or q_lower == "summarize":
            return ExecutionPlan(
                intent="DOCUMENT",
                response_mode="KNOWLEDGE_ONLY",
                knowledge_mode="KNOWLEDGE_BASE",
                tools=["retrieval"],
                rewritten_query="Summarize the entire document covering key points, architecture, and conclusions."
            )
            
        # Return None for complex queries to fallback to ReasoningEngine
        return None

class ReasoningEngine:
    """
    LLM-based decision engine that generates execution plans for complex queries.
    """
    def __init__(self):
        self.llm = DynamicLLMProvider()
        
    async def generate_plan(self, query: str, has_documents: bool) -> ExecutionPlan:
        if not has_documents:
            return ExecutionPlan(
                intent="GENERAL",
                response_mode="GENERAL_ONLY",
                knowledge_mode="NONE",
                tools=[],
                rewritten_query=None
            )
            
        prompt = f"""You are a Reasoning Engine for an AI Knowledge Operating System.
Your task is to analyze the user's query and output a JSON execution plan.

Available Tools: ["retrieval"]

Rules for intent, response_mode, and knowledge_mode:
- If the user asks to summarize, explain, or query their uploaded documents, set intent="DOCUMENT", response_mode="KNOWLEDGE_ONLY", knowledge_mode="KNOWLEDGE_BASE", tools=["retrieval"].
- If the user asks a general knowledge question (e.g. "What is OAuth?"), set intent="GENERAL", response_mode="GENERAL_ONLY", knowledge_mode="NONE", tools=[].
- If the user asks a question that requires both their documents and your general expertise (e.g. "How can I improve my project architecture?"), set intent="HYBRID", response_mode="HYBRID", knowledge_mode="HYBRID", tools=["retrieval"].

Query Rewriting:
- If tools includes "retrieval", provide a `rewritten_query` optimized for vector search.
- Do NOT mention "the user" or "the document" in the rewritten query, just write the core concepts to search for.

User Query: "{query}"

Respond ONLY with valid JSON matching this schema:
{{
    "intent": "DOCUMENT | GENERAL | HYBRID",
    "response_mode": "KNOWLEDGE_ONLY | GENERAL_ONLY | HYBRID",
    "knowledge_mode": "KNOWLEDGE_BASE | NONE | HYBRID",
    "tools": ["retrieval"],
    "rewritten_query": "string or null"
}}
"""
        response_text = ""
        try:
            response_text = await self.llm.generate(prompt)
            # Clean markdown code blocks if any
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
            
            clean_text = clean_text.strip()
            
            plan_dict = json.loads(clean_text)
            
            # Verify required fields
            required_fields = ["intent", "response_mode", "knowledge_mode", "rewritten_query", "tools"]
            for field in required_fields:
                if field not in plan_dict:
                    raise ValueError(f"Missing required field in planner: {field}")
            
            return ExecutionPlan(**plan_dict)
            
        except Exception as e:
            logger.error(
                f"Planner validation failed!\n"
                f"Raw LLM output: {response_text}\n"
                f"Parsing/Validation Error: {str(e)}\n"
                f"Fallback Reason: Failed to parse planner JSON or invalid Pydantic schema."
            )
            # Graceful fallback to default plan
            return ExecutionPlan(
                intent="DOCUMENT",
                response_mode="AUTO",
                knowledge_mode="AUTO",
                tools=["retrieval"],
                rewritten_query=query
            )
