"""
ConversationService — Milestone 10 (Planner + Executor architecture)

Internal flow for every query:
  1. Validate conversation ownership.
  2. Load attached document IDs and titles.
  3. Load conversation history.
  4. Build PlannerRequest and call PlannerService → ExecutionPlan.
  5. Create ExecutionContext.
  6. Call Executor.run (or run_stream for streaming).
  7. Persist messages to DB.
  8. Return FinalResponse wrapped in ChatQueryResponse.

Design invariants:
  - Frontend never knows about Planner, ExecutionPlan, Executor, or Tools.
  - Existing /query and /stream endpoints remain unchanged.
  - All planner + executor observability data flows through PipelineExecution.
  - Streaming uses asyncio.Queue + worker pattern (unchanged from prior design).
"""

import json
import logging
import time
from typing import AsyncGenerator, Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException
import uuid
import datetime

from app.ai.executor.executor import Executor
from app.ai.executor.schemas import ExecutionContext, FinalResponse
from app.ai.planner.planner import PlannerService
from app.ai.planner.schemas import PlannerRequest
from app.ai.pipeline.manager import PipelineManager, PipelineState
from app.ai.pipeline.health import ComponentHealth
from app.schemas.conversation import (
    ConversationQueryRequest, ChatQueryResponse, CitationSchema,
    RetrievedChunkSchema, SearchResponse, ConversationCreate,
    ConversationResponse, MessageResponse, ConversationDocumentResponse, TimingMetrics
)
from app.models.conversation import Conversation, ConversationMessage, ConversationDocument
from app.models.document import Document
from app.ai.config import ai_config
import asyncio

logger = logging.getLogger(__name__)

# Simple in-process query cache: key → (timestamp, response_dict)
query_cache: Dict[str, Any] = {}


class ConversationService:
    """
    High-level service that orchestrates the full AI pipeline.

    Every public method is called by the API layer. The Planner and Executor
    are internal — the API layer never interacts with them directly.
    """

    def __init__(self):
        self._planner = PlannerService()
        self._executor = Executor()

    # ------------------------------------------------------------------
    # CRUD helpers (unchanged)
    # ------------------------------------------------------------------

    async def get_all(self, db: AsyncSession, user_id: uuid.UUID) -> List[ConversationResponse]:
        result = await db.execute(
            select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc())
        )
        conversations = result.scalars().all()

        response_list = []
        for conv in conversations:
            doc_result = await db.execute(
                select(Document, ConversationDocument)
                .join(ConversationDocument, Document.id == ConversationDocument.document_id)
                .where(ConversationDocument.conversation_id == conv.id)
            )
            documents = []
            for doc, conv_doc in doc_result.all():
                documents.append({
                    "document_id": doc.id,
                    "title": doc.title,
                    "provider": doc.provider,
                    "status": doc.status,
                    "attached_at": conv_doc.attached_at
                })

            last_msg_result = await db.execute(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conv.id)
                .order_by(ConversationMessage.created_at.desc())
                .limit(1)
            )
            last_msg = last_msg_result.scalar_one_or_none()

            response_list.append(ConversationResponse(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                document_count=len(documents),
                last_message=last_msg.content if last_msg else None,
                documents=documents
            ))

        return response_list

    async def get_one(self, db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID) -> ConversationResponse:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        msg_result = await db.execute(
            select(ConversationMessage).where(ConversationMessage.conversation_id == conv.id).order_by(ConversationMessage.created_at.asc())
        )
        messages = msg_result.scalars().all()

        doc_result = await db.execute(
            select(Document, ConversationDocument)
            .join(ConversationDocument, Document.id == ConversationDocument.document_id)
            .where(ConversationDocument.conversation_id == conv.id)
        )
        documents = []
        for doc, conv_doc in doc_result.all():
            documents.append({
                "document_id": doc.id,
                "title": doc.title,
                "provider": doc.provider,
                "status": doc.status,
                "attached_at": conv_doc.attached_at
            })

        return ConversationResponse(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=[MessageResponse.model_validate(m) for m in messages],
            documents=documents
        )

    async def create(self, db: AsyncSession, user_id: uuid.UUID, data: ConversationCreate) -> ConversationResponse:
        conv = Conversation(user_id=user_id, title=data.title)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return await self.get_one(db, user_id, conv.id)

    async def delete(self, db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID):
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await db.delete(conv)
        await db.commit()

    async def attach_document(self, db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID, document_id: uuid.UUID):
        conv_result = await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))
        if not conv_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Conversation not found")

        doc_result = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == user_id))
        if not doc_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Document not found")

        existing = await db.execute(
            select(ConversationDocument).where(
                ConversationDocument.conversation_id == conversation_id,
                ConversationDocument.document_id == document_id
            )
        )
        if existing.scalar_one_or_none():
            return {"status": "already_attached"}

        conv_doc = ConversationDocument(conversation_id=conversation_id, document_id=document_id)
        db.add(conv_doc)
        await db.commit()
        return {"status": "success"}

    async def detach_document(self, db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID, document_id: uuid.UUID):
        conv_result = await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))
        if not conv_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Conversation not found")

        await db.execute(
            delete(ConversationDocument).where(
                ConversationDocument.conversation_id == conversation_id,
                ConversationDocument.document_id == document_id
            )
        )
        await db.commit()
        return {"status": "success"}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_attached_documents(self, db: AsyncSession, conversation_id: uuid.UUID):
        """Return (doc_ids: List[str], doc_titles: List[str], doc_metadata: List[Dict[str, Any]])."""
        result = await db.execute(
            select(Document)
            .join(ConversationDocument, Document.id == ConversationDocument.document_id)
            .where(ConversationDocument.conversation_id == conversation_id)
        )
        docs = result.scalars().all()
        doc_metadata = []
        for d in docs:
            doc_metadata.append({
                "id": str(d.id),
                "title": d.title,
                "provider": d.provider,
                "mime_type": d.mime_type,
                "file_size": d.file_size,
                "status": d.status,
            })
        return (
            [str(d.id) for d in docs],
            [d.title for d in docs],
            doc_metadata,
        )

    async def _get_conversation_history(self, db: AsyncSession, conversation_id: uuid.UUID) -> List[Dict[str, str]]:
        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(ai_config.MAX_HISTORY_MESSAGES)
        )
        messages = result.scalars().all()
        return [{"role": m.role, "content": m.content} for m in reversed(messages)]

    async def _save_messages(self, db: AsyncSession, conversation_id: uuid.UUID, user_query: str, ai_answer: str, citations: list):
        user_msg = ConversationMessage(conversation_id=conversation_id, role="user", content=user_query)
        ai_msg = ConversationMessage(
            conversation_id=conversation_id, role="assistant",
            content=ai_answer, citations={"sources": citations}
        )
        db.add_all([user_msg, ai_msg])
        conv_result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        conv = conv_result.scalar_one()
        conv.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()

    async def _build_filters(self, db: AsyncSession, conversation_id: uuid.UUID, request: ConversationQueryRequest) -> Dict[str, Any]:
        """Legacy helper for search_only endpoint."""
        doc_ids, _, _ = await self._get_attached_documents(db, conversation_id)
        if not doc_ids:
            return {}
        filters = {"document_id": doc_ids}
        if request.provider:
            filters["provider"] = request.provider
        if request.mime_type:
            filters["mime_type"] = request.mime_type
        return filters

    def _check_cache(self, conversation_id: uuid.UUID, query: str) -> Optional[Dict[str, Any]]:
        key = f"{conversation_id}_{query}"
        if key in query_cache:
            ts, data = query_cache[key]
            if time.time() - ts < ai_config.QUERY_CACHE_TTL_SECONDS:
                return data
        return None

    def _set_cache(self, conversation_id: uuid.UUID, query: str, data: Dict[str, Any]):
        key = f"{conversation_id}_{query}"
        query_cache[key] = (time.time(), data)

    # ------------------------------------------------------------------
    # Core pipeline — shared between query() and query_stream()
    # ------------------------------------------------------------------

    async def _run_pipeline(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        request: ConversationQueryRequest,
        user_id: Optional[uuid.UUID],
        pipeline: PipelineManager,
    ) -> FinalResponse:
        """
        The core Planner → Executor pipeline.

        Shared by both the synchronous query() and the streaming query_stream()
        so that all logic lives in one place.
        """
        log_pfx = f"[pipe={pipeline.pipeline_id}] [conv={conversation_id}]"

        # 1. Validate conversation + ownership
        pipeline.transition_to(PipelineState.VALIDATING)
        if user_id:
            conv_result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
            )
        else:
            conv_result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        conv = conv_result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Health check
        await ComponentHealth.run_all(db)

        # 2. Load attached documents
        doc_ids, doc_titles, doc_metadata = await self._get_attached_documents(db, conversation_id)
        has_documents = bool(doc_ids)

        # 3. Load conversation history (pre-loaded; ConversationMemoryTool may also load it)
        history = await self._get_conversation_history(db, conversation_id)

        # 4. PLANNING
        pipeline.transition_to(PipelineState.PLANNING)
        planner_request = PlannerRequest(
            query=request.query,
            conversation_id=str(conversation_id),
            has_documents=has_documents,
            attached_document_titles=doc_titles,
            attached_documents_metadata=doc_metadata,
            conversation_history=history,
            execution_context_summary={
                "pipeline_id": pipeline.pipeline_id,
                "user_id": str(user_id) if user_id else "anonymous",
                "config_settings": {
                    "max_context_tokens": ai_config.MAX_CONTEXT_TOKENS,
                    "retrieval_top_k": ai_config.RETRIEVAL_TOP_K,
                }
            },
            response_mode_override=request.response_mode if request.response_mode != "AUTO" else None,
        )

        plan = await pipeline.execute_with_timeout(
            lambda: self._planner.plan(
                planner_request,
                pipeline_id=pipeline.pipeline_id,
                conversation_id=str(conversation_id),
            ),
            timeout_seconds=ai_config.TIMEOUT_PLANNER,
            stage_name="Planning",
            retries=0,  # PlannerService handles its own retries internally
        )

        # Record plan in pipeline execution for Developer Panel
        pipeline.execution.planner = {
            "task": plan.task.value,
            "reasoning": plan.reasoning,
            "confidence": plan.confidence,
            "steps": [s.tool.value for s in plan.steps],
            "is_fallback": plan.is_fallback,
            "fallback_reason": plan.fallback_reason,
        }
        pipeline.execution.planner_plan = plan.model_dump()
        pipeline.save_checkpoint("planner_result", pipeline.execution.planner)
        if pipeline.debugger:
            pipeline.debugger.save_planner(pipeline.execution.planner)

        # 5. Build ExecutionContext
        context = ExecutionContext(
            pipeline_id=pipeline.pipeline_id,
            request_id=pipeline.request_id,
            conversation_id=str(conversation_id),
            user_id=str(user_id) if user_id else "anonymous",
            db=db,
            attached_document_ids=doc_ids,
            attached_document_titles=doc_titles,
            attached_documents=doc_metadata,
            history=history,
            raw_query=request.query,
            config=ai_config.model_dump() if hasattr(ai_config, "model_dump") else getattr(ai_config, "__dict__", {}),
            current_execution_state={"status": "initialized"},
        )

        # 6. EXECUTOR
        pipeline.transition_to(PipelineState.RETRIEVING)
        final_response = await self._executor.run(plan, context)

        # Record executor output in pipeline execution
        pipeline.execution.tool_graph = [
            {
                "step_id": r.step_id,
                "tool": r.tool_name,
                "success": r.success,
                "latency_ms": r.latency_ms,
                "retried": r.retried,
                "error": r.error,
            }
            for r in final_response.step_results
        ]
        pipeline.execution.executor_metrics = {
            "planner_latency_ms": final_response.metrics.planner_latency_ms,
            "total_tool_latency_ms": final_response.metrics.total_tool_latency_ms,
            "llm_latency_ms": final_response.metrics.llm_latency_ms,
            "total_latency_ms": final_response.metrics.total_latency_ms,
            "prompt_tokens": final_response.metrics.prompt_tokens,
            "completion_tokens": final_response.metrics.completion_tokens,
            "estimated_cost_usd": final_response.metrics.estimated_cost_usd,
            "retries": final_response.metrics.retries,
            "steps_executed": final_response.metrics.steps_executed,
            "steps_failed": final_response.metrics.steps_failed,
        }

        # Populate retrieval block (for backwards compat with Developer Panel)
        all_raw_chunks = []
        all_records = []
        for r in final_response.step_results:
            if isinstance(r.output, dict):
                all_raw_chunks.extend(r.output.get("raw_chunks", []))
                all_records.extend(r.output.get("retrieval_records", []))

        pipeline.execution.retrieval = {
            "chunks_retrieved": len(all_raw_chunks),
            "scores": [c.get("score", 0.0) for c in all_raw_chunks],
            "document_ids": [c.get("payload", {}).get("document_id") for c in all_raw_chunks],
            "chunk_ids": [c.get("id") for c in all_raw_chunks],
            "similarity_threshold": ai_config.SIMILARITY_THRESHOLD_MEDIUM,
            "selected_chunks_count": len(final_response.retrieved_chunks),
            "records": all_records,
        }

        pipeline.execution.prompt = {
            "built_prompt": context.current_execution_state.get("built_prompt")
        }

        return final_response

    # ------------------------------------------------------------------
    # Search-only (unchanged)
    # ------------------------------------------------------------------

    async def search_only(self, db: AsyncSession, conversation_id: uuid.UUID, request: ConversationQueryRequest, user_id: uuid.UUID) -> SearchResponse:
        logger.info(f"Running search only for query: '{request.query}' in conversation {conversation_id}")
        conv_result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        )
        if not conv_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Conversation not found")

        filters = await self._build_filters(db, conversation_id, request)
        if not filters:
            return SearchResponse(chunks=[])

        from app.ai.retrieval.service import RetrievalService
        retrieval_service = RetrievalService()
        raw_chunks = await retrieval_service.retrieve(
            query=request.query,
            top_k=request.top_k,
            filters=filters
        )

        retrieved_chunks = []
        for chunk in raw_chunks:
            payload = chunk.get("payload", {})
            retrieved_chunks.append(RetrievedChunkSchema(
                score=chunk.get("score", 0.0),
                document_title=payload.get("document_title", "Unknown Document"),
                content=payload.get("content", "")
            ))

        return SearchResponse(chunks=retrieved_chunks)

    # ------------------------------------------------------------------
    # Non-streaming query
    # ------------------------------------------------------------------

    async def query(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        request: ConversationQueryRequest,
        user_id: Optional[uuid.UUID] = None,
    ) -> ChatQueryResponse:
        pipeline = PipelineManager(
            request_id=uuid.uuid4().hex[:8],
            conversation_id=str(conversation_id),
            user_id=str(user_id) if user_id else "sync"
        )

        try:
            # Cache check
            cached = self._check_cache(conversation_id, request.query)
            if cached:
                pipeline.log("Cache hit!")
                pipeline.finish(success=True)
                return ChatQueryResponse(**cached)

            pipeline.execution.request = {
                "query": request.query,
                "top_k": request.top_k,
                "provider": request.provider,
                "mime_type": request.mime_type,
                "response_mode": request.response_mode
            }

            final_response = await self._run_pipeline(db, conversation_id, request, user_id, pipeline)

            # Persist messages
            pipeline.transition_to(PipelineState.SAVING)
            await self._save_messages(
                db, conversation_id, request.query,
                final_response.answer,
                final_response.sources,
            )
            pipeline.save_checkpoint("assistant_saved", True)
            pipeline.save_checkpoint("llm_output_exists", bool(final_response.answer))
            pipeline.save_checkpoint("prompt_exists", True)

            pipeline.finish(success=True)
            pipeline.validate_final_state()

            m = final_response.metrics
            timing_metrics = TimingMetrics(
                planning_ms=pipeline.timings.get("PLANNING_ms", 0),
                retrieval_ms=pipeline.timings.get("RETRIEVING_ms", 0),
                embedding_ms=0,
                llm_ms=m.llm_latency_ms,
                total_ms=m.total_latency_ms,
            )

            debug_meta = {
                "pipeline_id": pipeline.pipeline_id,
                "request_id": pipeline.request_id,
                "conversation_id": pipeline.conversation_id,
                "user_id": pipeline.user_id,
                "planner_version": getattr(ai_config, "PLANNER_VERSION", "2.0.0"),
                "executor_version": getattr(ai_config, "EXECUTOR_VERSION", "2.0.0"),
                "llm_provider": request.provider or getattr(ai_config, "DEFAULT_LLM_PROVIDER", "gemini"),
                "built_prompt": pipeline.execution.prompt.get("built_prompt"),
                "errors": pipeline.execution.errors,
                "plan": pipeline.execution.planner,
                "execution_plan": pipeline.execution.planner_plan,
                "tool_graph": pipeline.execution.tool_graph,
                "executor_metrics": pipeline.execution.executor_metrics,
                "retrieval": pipeline.execution.retrieval,
                "planner_time_ms": pipeline.timings.get("PLANNING_ms", 0),
                "total_time_ms": m.total_latency_ms,
                "prompt_tokens": m.prompt_tokens,
                "completion_tokens": m.completion_tokens,
                "cost": m.estimated_cost_usd,
            }

            response_data = {
                "answer": final_response.answer,
                "sources": [CitationSchema(**s) for s in final_response.sources],
                "retrieved_chunks": [RetrievedChunkSchema(**c) for c in final_response.retrieved_chunks],
                "provenance": final_response.provenance,
                "timing": timing_metrics,
                "debug_metadata": debug_meta,
            }
            self._set_cache(conversation_id, request.query, {
                **{k: v.model_dump() if hasattr(v, 'model_dump') else v for k, v in response_data.items()},
                "sources": final_response.sources,
                "retrieved_chunks": final_response.retrieved_chunks,
            })
            return ChatQueryResponse(**response_data)

        except Exception as e:
            pipeline.handle_exception(e)
            raise e

    # ------------------------------------------------------------------
    # Streaming query
    # ------------------------------------------------------------------

    async def query_stream(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        request: ConversationQueryRequest,
        user_id: Optional[uuid.UUID] = None,
    ) -> AsyncGenerator[dict, None]:
        pipeline = PipelineManager(
            request_id=uuid.uuid4().hex[:8],
            conversation_id=str(conversation_id),
            user_id=str(user_id) if user_id else "stream"
        )
        queue: asyncio.Queue = asyncio.Queue()

        async def pipeline_worker():
            try:
                # Cache check
                cached = self._check_cache(conversation_id, request.query)
                if cached:
                    pipeline.log("Cache hit!")
                    await queue.put({"event": "planning", "data": json.dumps({"status": "cache_hit"})})
                    await queue.put({"event": "chunk", "data": json.dumps({"text": cached.get("answer", "")})})
                    await queue.put({"event": "done", "data": json.dumps({"timing": {}, "debug_metadata": {}})})
                    pipeline.finish(success=True)
                    return

                pipeline.execution.request = {
                    "query": request.query,
                    "top_k": request.top_k,
                    "provider": request.provider,
                    "mime_type": request.mime_type,
                    "response_mode": request.response_mode
                }

                # Validate + load documents + plan
                pipeline.transition_to(PipelineState.VALIDATING)
                if user_id:
                    conv_result = await db.execute(
                        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
                    )
                else:
                    conv_result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
                conv = conv_result.scalar_one_or_none()
                if not conv:
                    raise HTTPException(status_code=404, detail="Conversation not found")

                await ComponentHealth.run_all(db)

                doc_ids, doc_titles, doc_metadata = await self._get_attached_documents(db, conversation_id)
                has_documents = bool(doc_ids)
                history = await self._get_conversation_history(db, conversation_id)

                # PLANNING
                pipeline.transition_to(PipelineState.PLANNING)
                await queue.put({"event": "planning", "data": json.dumps({"status": "started"})})

                planner_request = PlannerRequest(
                    query=request.query,
                    conversation_id=str(conversation_id),
                    has_documents=has_documents,
                    attached_document_titles=doc_titles,
                    attached_documents_metadata=doc_metadata,
                    conversation_history=history,
                    execution_context_summary={
                        "pipeline_id": pipeline.pipeline_id,
                        "user_id": str(user_id) if user_id else "anonymous",
                        "config_settings": {
                            "max_context_tokens": ai_config.MAX_CONTEXT_TOKENS,
                            "retrieval_top_k": ai_config.RETRIEVAL_TOP_K,
                        }
                    },
                    response_mode_override=request.response_mode if request.response_mode != "AUTO" else None,
                )
                plan = await pipeline.execute_with_timeout(
                    lambda: self._planner.plan(
                        planner_request,
                        pipeline_id=pipeline.pipeline_id,
                        conversation_id=str(conversation_id),
                    ),
                    timeout_seconds=ai_config.TIMEOUT_PLANNER,
                    stage_name="Planning",
                    retries=0,
                )

                pipeline.execution.planner = {
                    "task": plan.task.value,
                    "reasoning": plan.reasoning,
                    "confidence": plan.confidence,
                    "steps": [s.tool.value for s in plan.steps],
                    "is_fallback": plan.is_fallback,
                }
                pipeline.execution.planner_plan = plan.model_dump()
                pipeline.save_checkpoint("planner_result", pipeline.execution.planner)

                await queue.put({"event": "planning", "data": json.dumps({
                    "task": plan.task.value,
                    "steps": [s.tool.value for s in plan.steps],
                    "reasoning": plan.reasoning,
                })})

                # Build context
                context = ExecutionContext(
                    pipeline_id=pipeline.pipeline_id,
                    request_id=pipeline.request_id,
                    conversation_id=str(conversation_id),
                    user_id=str(user_id) if user_id else "anonymous",
                    db=db,
                    attached_document_ids=doc_ids,
                    attached_document_titles=doc_titles,
                    attached_documents=doc_metadata,
                    history=history,
                    raw_query=request.query,
                    config=ai_config.model_dump() if hasattr(ai_config, "model_dump") else getattr(ai_config, "__dict__", {}),
                    current_execution_state={"status": "initialized"},
                )

                # Validate & correct plan (same path as Executor.run)
                plan = self._executor._validate_and_correct_plan(plan, context, context.log_prefix)

                # Execute all non-LLM tool steps
                pipeline.transition_to(PipelineState.RETRIEVING)
                await queue.put({"event": "retrieving", "data": json.dumps({"status": "started"})})

                from app.ai.executor.schemas import ExecutorMetrics as _ExecMetrics
                _stream_metrics = _ExecMetrics()
                step_results = await self._executor._execute_steps(
                    plan, context, _stream_metrics, context.log_prefix,
                )

                # Build metadata for client
                sources = []
                retrieved_chunks_info = []
                for r in step_results:
                    if isinstance(r.output, dict):
                        for chunk in (r.output.get("optimized_chunks") or r.output.get("chunks", [])):
                            payload = chunk.get("payload", {})
                            score = chunk.get("score", 0.0)
                            title = payload.get("document_title", "Unknown")
                            provider = payload.get("provider", "unknown")
                            try:
                                ci = int(str(payload.get("chunk_index", 0)).split("-")[0])
                            except (ValueError, AttributeError):
                                ci = 0
                            sources.append({
                                "document_title": title,
                                "provider": provider,
                                "chunk_index": ci,
                                "score": score,
                            })
                            retrieved_chunks_info.append({
                                "score": score,
                                "document_title": title,
                                "content": payload.get("content", ""),
                            })

                await queue.put({"event": "metadata", "data": json.dumps({
                    "sources": sources,
                    "provenance": plan.task.value.lower(),
                })})

                # Build final prompt
                pipeline.transition_to(PipelineState.PROMPT_BUILDING)
                await queue.put({"event": "building_prompt", "data": json.dumps({"status": "started"})})
                prompt = self._executor._build_final_prompt(plan, context)
                pipeline.save_checkpoint("prompt_exists", True)

                # Stream LLM response
                pipeline.transition_to(PipelineState.GENERATING)
                await queue.put({"event": "calling_llm", "data": json.dumps({"status": "started"})})
                pipeline.transition_to(PipelineState.STREAMING)
                await queue.put({"event": "streaming", "data": json.dumps({"status": "started"})})

                full_answer = ""
                from app.ai.llm.manager import DynamicLLMProvider
                llm = DynamicLLMProvider()
                try:
                    async for text_chunk in llm.generate_stream(prompt):
                        full_answer += text_chunk
                        await queue.put({"event": "chunk", "data": json.dumps({"text": text_chunk})})
                except Exception as e:
                    pipeline.error(f"Error during LLM streaming: {e}")
                    raise e

                pipeline.save_checkpoint("llm_output_exists", True)
                llm_metrics = getattr(llm, "last_metrics", {})

                # Persist
                pipeline.transition_to(PipelineState.SAVING)
                await self._save_messages(db, conversation_id, request.query, full_answer, sources)
                pipeline.save_checkpoint("assistant_saved", True)

                pipeline.finish(success=True)
                pipeline.validate_final_state()

                timing_metrics = TimingMetrics(
                    planning_ms=pipeline.timings.get("PLANNING_ms", 0),
                    retrieval_ms=pipeline.timings.get("RETRIEVING_ms", 0),
                    embedding_ms=0,
                    llm_ms=pipeline.timings.get("GENERATING_ms", 0) + pipeline.timings.get("STREAMING_ms", 0),
                    total_ms=pipeline.timings.get("total_ms", 0),
                )

                debug_meta = {
                    "pipeline_id": pipeline.pipeline_id,
                    "request_id": pipeline.request_id,
                    "conversation_id": pipeline.conversation_id,
                    "user_id": pipeline.user_id,
                    "planner_version": getattr(ai_config, "PLANNER_VERSION", "2.0.0"),
                    "executor_version": getattr(ai_config, "EXECUTOR_VERSION", "2.0.0"),
                    "llm_provider": request.provider or getattr(ai_config, "DEFAULT_LLM_PROVIDER", "gemini"),
                    "built_prompt": prompt,
                    "errors": pipeline.execution.errors,
                    "plan": pipeline.execution.planner,
                    "execution_plan": pipeline.execution.planner_plan,
                    "tool_graph": [
                        {
                            "step_id": r.step_id,
                            "tool": r.tool_name,
                            "success": r.success,
                            "latency_ms": r.latency_ms,
                            "error": getattr(r, "error", None),
                            "retried": getattr(r, "retried", False)
                        }
                        for r in step_results
                    ],
                    "executor_metrics": {
                        "total_tool_latency_ms": _stream_metrics.total_tool_latency_ms,
                        "retries": _stream_metrics.retries,
                        "steps_executed": _stream_metrics.steps_executed,
                        "steps_failed": _stream_metrics.steps_failed,
                    },
                    "prompt_tokens": llm_metrics.get("prompt_tokens", 0),
                    "completion_tokens": llm_metrics.get("completion_tokens", 0),
                    "cost": llm_metrics.get("cost", 0.0),
                    "planner_time_ms": pipeline.timings.get("PLANNING_ms", 0),
                    "total_time_ms": pipeline.timings.get("total_ms", 0),
                }

                self._set_cache(conversation_id, request.query, {
                    "answer": full_answer,
                    "sources": sources,
                    "retrieved_chunks": retrieved_chunks_info,
                    "provenance": plan.task.value.lower(),
                    "timing": timing_metrics.model_dump(),
                    "debug_metadata": debug_meta,
                })

                await queue.put({"event": "done", "data": json.dumps({
                    "timing": timing_metrics.model_dump(),
                    "debug_metadata": debug_meta,
                })})

            except Exception as e:
                try:
                    pipeline.handle_exception(e)
                except Exception as inner_e:
                    logger.error(f"Error inside handle_exception: {inner_e}")
                await queue.put({"event": "error", "data": json.dumps({"detail": str(e)})})
            finally:
                await queue.put({"event": "_TERMINAL", "data": None})

        # Launch background worker
        worker_task = asyncio.create_task(pipeline_worker())

        stream_started = False
        chunks_sent = 0
        terminal_event_sent = False

        start_time = time.time()
        max_duration = getattr(ai_config, "TIMEOUT_STREAMING", 90)

        try:
            while True:
                if time.time() - start_time > max_duration:
                    logger.error(f"[Conv {conversation_id}] Stream exceeded max duration {max_duration}s. Forcing terminate.")
                    yield {"event": "error", "data": json.dumps({"detail": "Stream exceeded maximum allowed duration."})}
                    break

                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=ai_config.HEARTBEAT_INTERVAL)

                    if msg["event"] == "_TERMINAL":
                        break

                    if msg["event"] == "planning":
                        stream_started = True
                    elif msg["event"] == "chunk":
                        chunks_sent += 1
                    elif msg["event"] in ("done", "error", "action_required"):
                        terminal_event_sent = True

                    yield msg
                except asyncio.TimeoutError:
                    stage = pipeline.current_stage
                    status_text = "Still processing..."
                    if stage == PipelineState.PLANNING:
                        status_text = "Still thinking about your plan..."
                    elif stage == PipelineState.RETRIEVING:
                        status_text = "Still searching your knowledge base..."
                    elif stage == PipelineState.OPTIMIZING:
                        status_text = "Still filtering and ranking sources..."
                    elif stage == PipelineState.PROMPT_BUILDING:
                        status_text = "Still preparing prompt instructions..."
                    elif stage == PipelineState.GENERATING:
                        status_text = "Still generating completion response..."
                    elif stage == PipelineState.STREAMING:
                        status_text = "Still streaming response chunks..."
                    elif stage == PipelineState.SAVING:
                        status_text = "Still saving message to database..."

                    pipeline.log(f"Watchdog triggered: {status_text}")
                    yield {"event": "heartbeat", "data": json.dumps({"status": status_text})}
        finally:
            if not worker_task.done():
                worker_task.cancel()
                pipeline.log("Streaming worker cancelled successfully.")

        try:
            assert stream_started, "Stream integrity failure: Stream was never started."
            assert terminal_event_sent, "Stream integrity failure: Stream closed without a terminal event."
        except AssertionError as integrity_err:
            pipeline.error(str(integrity_err))
            yield {"event": "error", "data": json.dumps({"detail": str(integrity_err)})}
