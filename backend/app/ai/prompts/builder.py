import hashlib
import tiktoken
from typing import List, Dict, Any, Optional
from app.ai.interfaces.prompt import PromptBuilder as IPromptBuilder

class PromptBuilder(IPromptBuilder):
    BUILDER_VERSION = "1.2.0"
    TEMPLATE_VERSION = "2.1.0"

    def build_prompt(self, query: str, chunks: List[Dict[str, Any]], conversation_history: Optional[List[Dict[str, str]]] = None, response_mode: str = "KNOWLEDGE_ONLY") -> str:
        
        base_instructions = "You are an intelligent, production-grade AI Knowledge Operating System.\n"
        
        if response_mode == "GENERAL_ONLY":
            system_instructions = base_instructions + """Your goal is to answer the user's question using your general knowledge.
You do NOT need to restrict yourself to uploaded documents.
Be helpful, concise, and professional.
"""
        elif response_mode == "HYBRID":
            system_instructions = base_instructions + """Your goal is to answer the user's question.
Use the uploaded knowledge provided in the Context section below as your PRIMARY source.
Whenever the uploaded knowledge is insufficient, supplement it using your own general knowledge.
CRITICAL RULE: Clearly distinguish which recommendations or facts come from the uploaded documents and which are your own general expertise.
Cite the uploaded documents using the provided metadata (e.g., [document_title, Chunk N]).
Never fabricate document content.
"""
        else: # KNOWLEDGE_ONLY
            system_instructions = base_instructions + """Your goal is to answer the user's question based ONLY on the provided context.
Follow these strict rules:
1. NEVER hallucinate. ONLY use the information provided in the Context section below. Do not use outside knowledge.
2. If the answer cannot be found explicitly in the context, explicitly admit that you do not know. State clearly that the information is unavailable.
3. Preserve technical wording and factual accuracy at all times.
4. Use concise professional formatting.
5. Cite your sources for every claim using the provided metadata (e.g., [document_title, Chunk N]). Never invent citations.
"""
 
        context_blocks = []
        for i, chunk in enumerate(chunks):
            payload = chunk.get("payload", {})
            title = payload.get("document_title", "Unknown Document")
            provider = payload.get("provider", "Unknown Provider")
            chunk_index = payload.get("chunk_index", "Unknown Index")
            content = payload.get("content", "").strip()
            
            context_blocks.append(f"--- SOURCE {i+1} ---\nDocument: {title}\nProvider: {provider}\nChunk Index: {chunk_index}\nContent:\n{content}\n")
            
        context_section = "### Context\n" + "\n".join(context_blocks) if context_blocks else ""
        
        history_section = ""
        if conversation_history:
            history_blocks = []
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_blocks.append(f"{role.capitalize()}: {content}")
            history_section = "### Conversation History\n" + "\n".join(history_blocks) + "\n"

        query_section = f"### User Question\n{query}"

        prompt = f"{system_instructions}\n{context_section}\n{history_section}\n{query_section}"
        
        # Validation: check if prompt is empty
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")
            
        return prompt

    def get_system_prompt_hash(self, response_mode: str = "KNOWLEDGE_ONLY") -> str:
        # Generate hash of system instructions for response mode
        dummy_prompt = self.build_prompt("", [], [], response_mode)
        # Grab first part containing system prompt
        system_part = dummy_prompt.split("### Context")[0].strip()
        return hashlib.sha256(system_part.encode("utf-8")).hexdigest()[:16]

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            # Fallback length estimation
            return len(text.split())
