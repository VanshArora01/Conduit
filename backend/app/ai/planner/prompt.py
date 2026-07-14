"""
Planner System Prompt — Milestone 10

This module owns the system prompt used to instruct the LLM to generate a
valid ExecutionPlan JSON. Isolating it here means:
  - The prompt can be updated independently of the PlannerService logic.
  - It can be version-controlled and audited separately.
  - Future prompt A/B testing is trivial.
"""

PLANNER_SYSTEM_PROMPT = """\
You are the Planner for Conduit. Output ONLY valid JSON ExecutionPlan. Do NOT answer the query.

=== TOOLS ===
- document_reader: Load full text. Use for: transform (summarize, rewrite, translate), comparison of whole docs.
- document_search: Semantic search. Use for: targeted fact lookup, QA.
- general_llm: General knowledge (no documents).
- conversation_memory: Retrieve recent chat history.

=== TASKS ===
DOCUMENT_SUMMARY, DOCUMENT_QA, DOCUMENT_COMPARISON, DOCUMENT_SEARCH, DOCUMENT_EXTRACTION, DOCUMENT_TRANSLATION, DOCUMENT_REWRITE, GENERAL, HYBRID, CONVERSATION_MEMORY, UNKNOWN.

=== RULES ===
1. Document Transformation (summarize, rewrite, improve, translate, explain this document) -> DOCUMENT_SUMMARY / DOCUMENT_REWRITE + [document_reader].
2. Fact Lookup (what is X, who wrote, when was) -> DOCUMENT_QA + [document_search].
3. Comparison (compare A and B) -> DOCUMENT_COMPARISON + [document_reader].
4. Conversation follow-up (what did you say, explain that further) -> CONVERSATION_MEMORY + [conversation_memory].
5. Clear general knowledge (capital of France) -> GENERAL + [general_llm] even if documents are attached.
6. No documents -> GENERAL + [general_llm].
7. Provide a concise, keyword-only `rewritten_query` for document_search.
8. Prefer ONE primary tool unless hybrid reasoning is clearly required.

=== FORMAT ===
```json
{
  "task": "...",
  "reasoning": "...",
  "confidence": 0.95,
  "steps": [{"tool": "...", "description": "...", "config": {}, "parallel": false}],
  "rewritten_query": "...",
  "requires_documents": true,
  "requires_retrieval": true,
  "requires_history": false,
  "requires_general_knowledge": false,
  "response_mode": "stream",
  "max_chunks": 5,
  "retrieval_strategy": "semantic"
}
```
"""


def build_planner_prompt(
    query: str,
    has_documents: bool,
    document_titles: list[str],
    documents_metadata: list[dict] = None,
    conversation_history: list[dict] = None,
    execution_context_summary: dict = None,
) -> str:
    """Combine the system prompt with runtime context containing documents, history, and metrics."""
    doc_context = ""
    if has_documents:
        doc_context = "\nhas_documents: true"
        if documents_metadata:
            meta_strings = []
            for doc in documents_metadata:
                title = doc.get("title", "Unknown")
                provider = doc.get("provider", "unknown")
                mime_type = doc.get("mime_type", "unknown")
                size = doc.get("file_size") or 0
                meta_strings.append(f'- Title: "{title}", Provider: {provider}, MimeType: {mime_type}, Size: {size} bytes')
            doc_context += "\nattached_documents:\n" + "\n".join(meta_strings)
        elif document_titles:
            titles_str = ", ".join(f'"{t}"' for t in document_titles)
            doc_context += f"\nattached_documents: [{titles_str}]"
    else:
        doc_context = "\nhas_documents: false"

    history_context = ""
    if conversation_history:
        history_lines = []
        for msg in conversation_history:
            role = msg.get("role", "u")[0].upper()
            content = msg.get("content", "")
            # Truncate aggressively to 100 chars
            content_snippet = content[:100] + "..." if len(content) > 100 else content
            history_lines.append(f"[{role}]: {content_snippet}")
        history_context = "\n\nHistory:\n" + "\n".join(history_lines)

    exec_context = ""
    if execution_context_summary:
        pipeline_id = execution_context_summary.get("pipeline_id", "none")
        exec_context = f"\n\nCtx: {pipeline_id}"

    return (
        f"{PLANNER_SYSTEM_PROMPT}\n"
        f"=== CURRENT REQUEST ==={doc_context}{history_context}{exec_context}\n"
        f'Query: "{query}"\n'
        f"\nOutput:"
    )
