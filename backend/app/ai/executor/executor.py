"""
Executor — Milestone 10

The Executor is the heart of the AI Operating System pipeline.

Architecture contract:
  - Input:  ExecutionPlan + ExecutionContext (NEVER raw user messages)
  - Output: FinalResponse (answer + observability data + metrics)
  - Errors: Logged and wrapped. Never silently swallowed.
  - Tools:  Invoked ONLY via the ToolRegistry (never instantiated directly).
  - LLM:    Called ONCE at the end, after all tool outputs are collected.
  - Stream: Handled separately via Executor.run_stream().

Flow:
  1. Validate plan (must be ExecutionPlan, not empty steps).
  2. Execute steps sequentially (or concurrently if step.parallel=True).
     a. Get tool from registry.
     b. Prepare input_data = step.config + plan-level fields.
     c. Execute with timeout + retry policy.
     d. Store result in context.step_outputs.
  3. Build the final LLM prompt from plan + tool outputs + history.
  4. Call LLM (full or streaming).
  5. Build and return FinalResponse with all observability data.

This Executor is designed so that:
  - Adding new tools requires ZERO changes here.
  - Adding parallel step groups requires ZERO changes to individual tools.
  - Streaming vs full-response is transparent to tools — they always return dicts.
"""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from typing import AsyncGenerator, Dict, List, Optional

from app.ai.config import ai_config
from app.ai.executor.schemas import (
    ExecutionContext,
    ExecutorMetrics,
    FinalResponse,
    StepResult,
)
from app.ai.planner.schemas import ExecutionPlan, ExecutionStep, TaskType, ToolName
from app.ai.tools.general_llm import GeneralLLMTool
from app.ai.tools.registry import get_tool, is_registered

logger = logging.getLogger(__name__)


class Executor:
    """
    Stateless executor that runs an ExecutionPlan against an ExecutionContext.

    Instantiate once per ConversationService. It holds no per-request state.
    """

    async def run(
        self,
        plan: ExecutionPlan,
        context: ExecutionContext,
    ) -> FinalResponse:
        """
        Execute a plan and return a complete FinalResponse.

        This is the non-streaming path. For streaming, use run_stream().
        """
        log_pfx = context.log_prefix
        overall_start = time.time()
        metrics = ExecutorMetrics()
        step_results: List[StepResult] = []

        logger.info(
            f"{log_pfx} [Executor] Starting execution: "
            f"plan_id={plan.plan_id} task={plan.task.value} "
            f"steps={[s.tool.value for s in plan.steps]}"
        )

        # ------------------------------------------------------------------
        # 1. Validate & correct plan (override obvious Planner mistakes)
        # ------------------------------------------------------------------
        plan = self._validate_and_correct_plan(plan, context, log_pfx)
        if not plan.steps:
            logger.warning(f"{log_pfx} [Executor] Plan has no steps. Using GENERAL fallback.")
            plan.steps = [ExecutionStep(tool=ToolName.GENERAL_LLM, description="Fallback: empty plan.")]

        # ------------------------------------------------------------------
        # 2. Execute steps
        # ------------------------------------------------------------------
        try:
            step_results = await self._execute_steps(plan, context, metrics, log_pfx)
        except Exception as exc:
            stack = traceback.format_exc()
            logger.error(f"{log_pfx} [Executor] Fatal error during step execution:\n{stack}")
            metrics.total_latency_ms = int((time.time() - overall_start) * 1000)
            return FinalResponse(
                answer="I encountered an error while processing your request. Please try again.",
                error=f"{type(exc).__name__}: {exc}",
                metrics=metrics,
                plan_dump=plan.model_dump(),
                step_results=step_results,
            )

        # ------------------------------------------------------------------
        # 3. Build final prompt
        # ------------------------------------------------------------------
        prompt = self._build_final_prompt(plan, context)

        # ------------------------------------------------------------------
        # 4. Call LLM (non-streaming)
        # ------------------------------------------------------------------
        llm_start = time.time()
        try:
            llm_tool = GeneralLLMTool()
            llm_result = await llm_tool.execute({"prompt": prompt}, context)
            answer = llm_result.get("response", "")
            metrics.prompt_tokens = llm_result.get("prompt_tokens", 0)
            metrics.completion_tokens = llm_result.get("completion_tokens", 0)
            metrics.estimated_cost_usd += llm_result.get("cost", 0.0)
            metrics.llm_latency_ms = int((time.time() - llm_start) * 1000)
        except Exception as exc:
            stack = traceback.format_exc()
            logger.error(f"{log_pfx} [Executor] LLM call failed:\n{stack}")
            metrics.total_latency_ms = int((time.time() - overall_start) * 1000)
            return FinalResponse(
                answer="I couldn't generate a response. Please try again.",
                error=f"LLM error: {exc}",
                metrics=metrics,
                plan_dump=plan.model_dump(),
                step_results=step_results,
            )

        # ------------------------------------------------------------------
        # 5. Extract sources and chunks for the response
        # ------------------------------------------------------------------
        sources, retrieved_chunks = _extract_sources_and_chunks(context)
        provenance = _determine_provenance(plan)

        metrics.total_latency_ms = int((time.time() - overall_start) * 1000)
        metrics.steps_executed = len(step_results)
        metrics.steps_failed = sum(1 for r in step_results if not r.success)

        logger.info(
            f"{log_pfx} [Executor] Completed in {metrics.total_latency_ms}ms. "
            f"steps={metrics.steps_executed} failed={metrics.steps_failed} "
            f"tokens={metrics.prompt_tokens}+{metrics.completion_tokens}"
        )

        return FinalResponse(
            answer=answer,
            sources=sources,
            retrieved_chunks=retrieved_chunks,
            provenance=provenance,
            plan_dump=plan.model_dump(),
            step_results=step_results,
            metrics=metrics,
        )

    async def run_stream(
        self,
        plan: ExecutionPlan,
        context: ExecutionContext,
    ) -> AsyncGenerator[str, None]:
        """
        Execute a plan and stream the LLM response token by token.

        Tools are executed non-streaming (they return dicts). Only the
        final LLM call is streamed. This matches the Planner's contract:
        "The Planner never streams. Only the final answer streams."
        """
        log_pfx = context.log_prefix
        overall_start = time.time()

        logger.info(
            f"{log_pfx} [Executor/Stream] Starting streaming execution: "
            f"plan_id={plan.plan_id} task={plan.task.value}"
        )

        plan = self._validate_and_correct_plan(plan, context, log_pfx)
        if not plan.steps:
            plan.steps = [ExecutionStep(tool=ToolName.GENERAL_LLM, description="Fallback: empty plan.")]

        # Execute all non-LLM steps first
        metrics = ExecutorMetrics()
        try:
            step_results = await self._execute_steps(plan, context, metrics, log_pfx)
        except Exception as exc:
            logger.error(f"{log_pfx} [Executor/Stream] Fatal error in step execution: {exc}", exc_info=True)
            yield f"\n\n[ERROR: {exc}]"
            return

        # Build final prompt
        prompt = self._build_final_prompt(plan, context)

        # Stream LLM response
        llm_tool = GeneralLLMTool()
        try:
            async for token in llm_tool.stream(prompt, context):
                yield token
        except Exception as exc:
            logger.error(f"{log_pfx} [Executor/Stream] LLM streaming failed: {exc}", exc_info=True)
            yield f"\n\n[Streaming error: {exc}]"

        total_ms = int((time.time() - overall_start) * 1000)
        logger.info(f"{log_pfx} [Executor/Stream] Streaming completed in {total_ms}ms.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_and_correct_plan(
        self,
        plan: ExecutionPlan,
        context: ExecutionContext,
        log_pfx: str,
    ) -> ExecutionPlan:
        """
        Override obvious Planner mistakes before tool execution.

        Rules:
          - No attached docs + document tools → GENERAL
          - DOCUMENT_SUMMARY / REWRITE / COMPARISON with only search → swap to reader
          - DOCUMENT_QA with only reader → swap to search
          - Cap max_chunks to config
        """
        has_docs = bool(context.attached_document_ids)
        doc_tools = {ToolName.DOCUMENT_READER, ToolName.DOCUMENT_SEARCH}
        tool_names = [s.tool for s in plan.steps]

        if not has_docs and any(t in doc_tools for t in tool_names):
            logger.warning(f"{log_pfx} [Executor] Overriding plan: doc tools without documents → GENERAL")
            plan.task = TaskType.GENERAL
            plan.steps = [ExecutionStep(tool=ToolName.GENERAL_LLM, description="Override: no documents attached.")]
            plan.requires_documents = False
            plan.requires_retrieval = False
            plan.requires_general_knowledge = True
            plan.reasoning = (plan.reasoning or "") + " | Executor override: no documents."
            return plan

        transform_tasks = {
            TaskType.DOCUMENT_SUMMARY,
            TaskType.DOCUMENT_REWRITE,
            TaskType.DOCUMENT_COMPARISON,
            TaskType.DOCUMENT_TRANSLATION,
        }
        if has_docs and plan.task in transform_tasks:
            if ToolName.DOCUMENT_SEARCH in tool_names and ToolName.DOCUMENT_READER not in tool_names:
                logger.warning(
                    f"{log_pfx} [Executor] Overriding plan: {plan.task.value} used search → reader"
                )
                plan.steps = [
                    ExecutionStep(
                        tool=ToolName.DOCUMENT_READER,
                        description="Override: full document required for transformation.",
                    )
                ]
                plan.requires_retrieval = False
                plan.requires_documents = True

        if has_docs and plan.task == TaskType.DOCUMENT_QA:
            if ToolName.DOCUMENT_READER in tool_names and ToolName.DOCUMENT_SEARCH not in tool_names:
                logger.warning(
                    f"{log_pfx} [Executor] Overriding plan: DOCUMENT_QA used reader → search"
                )
                plan.steps = [
                    ExecutionStep(
                        tool=ToolName.DOCUMENT_SEARCH,
                        description="Override: semantic search for fact lookup.",
                    )
                ]
                plan.requires_retrieval = True
                plan.requires_documents = True
                if not plan.rewritten_query:
                    plan.rewritten_query = context.raw_query

        plan.max_chunks = min(plan.max_chunks or ai_config.MAX_CHUNKS, ai_config.MAX_CHUNKS)
        return plan

    async def _execute_steps(
        self,
        plan: ExecutionPlan,
        context: ExecutionContext,
        metrics: ExecutorMetrics,
        log_pfx: str,
    ) -> List[StepResult]:
        """Execute all steps in order, respecting parallel groups."""
        results: List[StepResult] = []

        # Group steps: collect consecutive parallel=True steps into batches.
        groups = _group_steps(plan.steps)

        for group in groups:
            if len(group) == 1:
                # Sequential step
                result = await self._execute_single_step(group[0], plan, context, metrics, log_pfx)
                results.append(result)
            else:
                # Parallel batch
                logger.info(f"{log_pfx} [Executor] Running {len(group)} steps in parallel.")
                tasks = [
                    self._execute_single_step(step, plan, context, metrics, log_pfx)
                    for step in group
                ]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in batch_results:
                    if isinstance(res, Exception):
                        results.append(StepResult(
                            step_id="unknown",
                            tool_name="unknown",
                            success=False,
                            error=str(res),
                        ))
                    else:
                        results.append(res)

        return results

    async def _execute_single_step(
        self,
        step: ExecutionStep,
        plan: ExecutionPlan,
        context: ExecutionContext,
        metrics: ExecutorMetrics,
        log_pfx: str,
    ) -> StepResult:
        """Execute one step with timeout and retry logic."""
        step_start = time.time()
        tool_name = step.tool
        retried = False

        # Skip GeneralLLM steps — the Executor calls it explicitly after all
        # other steps to build the final prompt from accumulated tool outputs.
        if tool_name == ToolName.GENERAL_LLM:
            reason = "Skipped general_llm step from step sequence: reserved for final LLM generation call after all context is gathered."
            logger.info(f"{log_pfx} [Executor] {reason}")
            return StepResult(
                step_id=step.step_id,
                tool_name=tool_name.value,
                success=True,
                output={"skipped": True, "reason": reason},
                latency_ms=0,
            )

        if not is_registered(tool_name):
            err = f"Tool '{tool_name.value}' is not registered in Tool Registry."
            logger.error(f"{log_pfx} [Executor] Failed step execution: {err}")
            return StepResult(
                step_id=step.step_id,
                tool_name=tool_name.value,
                success=False,
                error=err,
            )

        # Build input_data: merge step.config with plan-level hints
        input_data: Dict = {
            "query": plan.rewritten_query or context.raw_query,
            "max_chunks": plan.max_chunks,
            "task": plan.task.value,
            **step.config,
        }

        # Attempt execution with retry
        last_error: Optional[Exception] = None
        tool_meta = get_tool(tool_name).meta
        max_attempts = tool_meta.retry_policy.max_attempts if step.retry_on_failure else 1
        backoff = tool_meta.retry_policy.backoff_seconds

        logger.info(
            f"{log_pfx} [Executor] [TOOL START] Starting tool '{tool_name.value}' "
            f"with input: {input_data}"
        )

        for attempt in range(1, max_attempts + 1):
            try:
                tool = get_tool(tool_name)
                timeout = tool_meta.timeout_seconds

                logger.info(
                    f"{log_pfx} [Executor] Tool execution attempt {attempt}/{max_attempts} "
                    f"for '{tool_name.value}' (timeout={timeout}s)"
                )

                output = await asyncio.wait_for(
                    tool.execute(input_data, context),
                    timeout=timeout,
                )

                # Store output in context for downstream steps
                context.step_outputs[step.step_id] = output

                latency = int((time.time() - step_start) * 1000)
                metrics.total_tool_latency_ms += latency

                logger.info(
                    f"{log_pfx} [Executor] [TOOL SUCCESS] Tool '{tool_name.value}' completed. "
                    f"Latency: {latency}ms | Attempt: {attempt} | Output preview keys: {list(output.keys())}"
                )

                return StepResult(
                    step_id=step.step_id,
                    tool_name=tool_name.value,
                    success=True,
                    output=output,
                    latency_ms=latency,
                    retried=(attempt > 1),
                )

            except asyncio.TimeoutError as exc:
                last_error = exc
                logger.warning(
                    f"{log_pfx} [Executor] [TOOL TIMEOUT] '{tool_name.value}' timed out "
                    f"after {timeout}s (attempt {attempt}/{max_attempts})"
                )
                if attempt < max_attempts:
                    await asyncio.sleep(backoff)
                    retried = True

            except Exception as exc:
                last_error = exc
                stack = traceback.format_exc()
                logger.error(
                    f"{log_pfx} [Executor] [TOOL ERROR] '{tool_name.value}' raised exception: {exc} "
                    f"(attempt {attempt}/{max_attempts})\nStack trace:\n{stack}"
                )
                if attempt < max_attempts:
                    await asyncio.sleep(backoff)
                    retried = True

        # All attempts exhausted
        metrics.retries += max_attempts - 1
        metrics.steps_failed += 1
        latency = int((time.time() - step_start) * 1000)
        logger.error(
            f"{log_pfx} [Executor] [TOOL FAILURE] Tool '{tool_name.value}' failed all "
            f"{max_attempts} attempts. Latency: {latency}ms | Error: {last_error}"
        )
        return StepResult(
            step_id=step.step_id,
            tool_name=tool_name.value,
            success=False,
            error=f"{type(last_error).__name__}: {last_error}",
            latency_ms=latency,
            retried=retried,
        )

    def _build_final_prompt(
        self,
        plan: ExecutionPlan,
        context: ExecutionContext,
    ) -> str:
        """
        Build the final LLM prompt from the execution plan and all tool outputs.

        Token budget (hard constraints):
          - Max history messages: MAX_HISTORY_MESSAGES (6)
          - Max chunks: MAX_CHUNKS (5)
          - Max context tokens: MAX_CONTEXT_TOKENS (3000)
        Never includes developer/debug information.
        """
        answer_length = getattr(plan, "answer_length", None) or ai_config.DEFAULT_ANSWER_LENGTH
        length_instructions = {
            "short": (
                "Response mode: SHORT. Answer in 1–3 sentences or a tight bullet list. "
                "No preamble. No filler."
            ),
            "medium": (
                "Response mode: MEDIUM. Be concise like Cursor AI or Claude. "
                "Give only the necessary information unless explicitly asked for detail. "
                "Do not provide long explanations unless explicitly requested."
            ),
            "detailed": (
                "Response mode: DETAILED. Provide a thorough, well-structured explanation "
                "with sections where helpful. Still avoid repetition and filler."
            ),
        }
        response_mode_instruction = length_instructions.get(
            answer_length, length_instructions["medium"]
        )

        base_system = (
            "You are Conduit, an AI Knowledge Operating System.\n"
            f"{response_mode_instruction}\n"
        )

        if plan.task == TaskType.DOCUMENT_COMPARISON:
            base_system += (
                "When comparing multiple documents, proactively identify similarities, differences, "
                "relationships, missing skills, and implementation paths using strong reasoning.\n"
            )

        if plan.requires_general_knowledge and not plan.requires_documents:
            system = base_system + "Answer the user's question using your general knowledge."
        elif plan.requires_general_knowledge and plan.requires_documents:
            system = base_system + (
                "KNOWLEDGE PRIORITY:\n"
                "1. ATTACHED DOCUMENTS (Highest priority)\n"
                "2. CONVERSATION HISTORY (Follow-ups)\n"
                "3. GENERAL KNOWLEDGE (Only if docs/history are insufficient)\n"
                "Cite sources as [DocumentTitle]."
            )
        else:
            system = base_system + (
                "KNOWLEDGE PRIORITY:\n"
                "1. ATTACHED DOCUMENTS (Must use ONLY this context)\n"
                "2. CONVERSATION HISTORY (Follow-ups only)\n"
                "Do NOT hallucinate. Say if the answer isn't in context.\n"
                "Cite sources as [DocumentTitle]."
            )

        # Collect chunks; cap at MAX_CHUNKS; strip duplicate metadata
        all_chunks = []
        seen_keys = set()
        for _step_id, output in context.step_outputs.items():
            if not isinstance(output, dict):
                continue
            # Never send debug/developer fields to the LLM
            chunks = output.get("chunks") or output.get("optimized_chunks", [])
            for chunk in chunks:
                payload = chunk.get("payload", {})
                title = payload.get("document_title", "Doc")
                content = (payload.get("content") or "").strip()
                chunk_index = payload.get("chunk_index", "")
                key = (title, str(chunk_index), content[:80])
                if not content or key in seen_keys:
                    continue
                seen_keys.add(key)
                all_chunks.append(chunk)
                if len(all_chunks) >= ai_config.MAX_CHUNKS:
                    break
            if len(all_chunks) >= ai_config.MAX_CHUNKS:
                break

        context_section = ""
        if all_chunks:
            blocks = []
            for i, chunk in enumerate(all_chunks):
                payload = chunk.get("payload", {})
                title = payload.get("document_title", "Doc")
                content = payload.get("content", "").strip()
                chunk_index = payload.get("chunk_index", i)
                blocks.append(f"[{title} | §{chunk_index}]\n{content}")
            context_section = "### Context\n" + "\n---\n".join(blocks)

        full_text_parts = []
        for _step_id, output in context.step_outputs.items():
            if isinstance(output, dict) and output.get("source") == "document_reader":
                full_text = output.get("full_text", "")
                if full_text and not all_chunks:
                    full_text_parts.append(full_text)

        if full_text_parts and not context_section:
            context_section = "### Document Content\n" + "\n\n---\n\n".join(full_text_parts)

        # History: hard cap at MAX_HISTORY_MESSAGES
        history_section = ""
        history = (context.history or [])[-ai_config.MAX_HISTORY_MESSAGES:]
        if history:
            history_lines = [
                f"{m['role'].capitalize()}: {m['content']}"
                for m in history
            ]
            history_section = "### Conversation History\n" + "\n".join(history_lines)

        query_section = f"### Query\n{context.raw_query}"

        parts = [system]
        if context_section:
            parts.append(context_section)
        if history_section:
            parts.append(history_section)
        parts.append(query_section)

        prompt = "\n\n".join(parts)
        prompt = _enforce_token_budget(prompt, ai_config.MAX_CONTEXT_TOKENS)

        # Store built prompt for developer panel only (already assembled without debug fields)
        context.current_execution_state["built_prompt"] = prompt
        return prompt


# ------------------------------------------------------------------
# Helper utilities
# ------------------------------------------------------------------

def _enforce_token_budget(prompt: str, max_tokens: int) -> str:
    """Trim prompt to max_tokens using tiktoken; keep system head + query tail."""
    try:
        from tiktoken import get_encoding
        enc = get_encoding("cl100k_base")
        tokens = enc.encode(prompt)
        if len(tokens) <= max_tokens:
            return prompt
        # Keep first ~20% (system) and last ~70% (context/query), leave room for marker
        head = int(max_tokens * 0.20)
        tail = int(max_tokens * 0.70)
        marker = enc.encode("\n\n... [CONTEXT TRUNCATED TO FIT TOKEN BUDGET] ...\n\n")
        trimmed = tokens[:head] + marker + tokens[-(tail):]
        return enc.decode(trimmed[:max_tokens])
    except Exception:
        # Fallback: character approx (~4 chars / token)
        max_chars = max_tokens * 4
        if len(prompt) <= max_chars:
            return prompt
        top_keep = int(max_chars * 0.25)
        bottom_keep = int(max_chars * 0.70)
        return (
            prompt[:top_keep]
            + "\n\n... [CONTEXT TRUNCATED TO FIT TOKEN BUDGET] ...\n\n"
            + prompt[-bottom_keep:]
        )


def _group_steps(steps: List[ExecutionStep]) -> List[List[ExecutionStep]]:
    """Group consecutive parallel=True steps into batches for asyncio.gather."""
    groups: List[List[ExecutionStep]] = []
    current_group: List[ExecutionStep] = []

    for step in steps:
        if step.parallel:
            current_group.append(step)
        else:
            if current_group:
                groups.append(current_group)
                current_group = []
            groups.append([step])

    if current_group:
        groups.append(current_group)

    return groups


def _extract_sources_and_chunks(context: ExecutionContext):
    """Extract citation sources and retrieved chunks from step outputs."""
    sources = []
    retrieved_chunks = []
    seen = set()

    for _step_id, output in context.step_outputs.items():
        if not isinstance(output, dict):
            continue

        chunks = output.get("optimized_chunks") or output.get("chunks", [])
        for chunk in chunks:
            payload = chunk.get("payload", {})
            score = chunk.get("score", 0.0)
            title = payload.get("document_title", "Unknown Document")
            provider = payload.get("provider", "unknown")
            chunk_index = payload.get("chunk_index", 0)
            content = payload.get("content", "")
            band = chunk.get("band")

            try:
                ci = int(str(chunk_index).split("-")[0])
            except (ValueError, AttributeError):
                ci = 0

            dedupe_key = (title, ci)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            sources.append({
                "document_title": title,
                "provider": provider,
                "chunk_index": ci,
                "score": score,
                "band": band,
            })
            retrieved_chunks.append({
                "score": score,
                "document_title": title,
                "content": content,
                "band": band,
            })

    return sources, retrieved_chunks


def _determine_provenance(plan: ExecutionPlan) -> str:
    """Determine the provenance string for the response."""
    if plan.task == TaskType.GENERAL:
        return "general"
    elif plan.requires_documents and plan.requires_general_knowledge:
        return "hybrid"
    elif plan.requires_documents:
        return "knowledge_only"
    return "general"
