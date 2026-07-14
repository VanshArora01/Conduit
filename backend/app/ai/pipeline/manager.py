import uuid
import time
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.ai.pipeline.debugger import DebugLogger
from app.ai.config import ai_config

logger = logging.getLogger(__name__)

class PipelineState:
    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    VALIDATING = "VALIDATING"
    PLANNING = "PLANNING"
    RETRIEVING = "RETRIEVING"
    OPTIMIZING = "OPTIMIZING"
    PROMPT_BUILDING = "PROMPT_BUILDING"
    GENERATING = "GENERATING"
    STREAMING = "STREAMING"
    SAVING = "SAVING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class PipelineManager:
    def __init__(self, request_id: str, conversation_id: str, user_id: str):
        self.pipeline_id = f"pipe_{uuid.uuid4().hex[:8]}"
        self.request_id = request_id
        self.conversation_id = conversation_id
        self.user_id = user_id
        
        self.current_stage = PipelineState.REQUEST_RECEIVED
        self.timings = {}
        self.stage_start_time = time.time()
        
        # Checkpoints for resumability
        self.context = {}
        
        self.debugger = DebugLogger(self.pipeline_id) if ai_config.DEBUG_AI else None
        
        # Instantiate PipelineExecution object
        from app.ai.pipeline.recorder import PipelineExecution, register_pipeline_execution
        self.execution = PipelineExecution(
            pipeline_id=self.pipeline_id,
            request_id=self.request_id,
            conversation_id=self.conversation_id,
            user_id=self.user_id
        )
        register_pipeline_execution(self.execution)
        
        self.log(f"Initialized Pipeline")

    def log(self, message: str, level: int = logging.INFO):
        prefix = f"[Pipeline: {self.pipeline_id}] [Conv: {self.conversation_id}] [Req: {self.request_id}] [User: {self.user_id}]"
        logger.log(level, f"{prefix} | {self.current_stage} | {message}")

    def error(self, message: str, exc_info=False):
        self.log(message, level=logging.ERROR)
        if self.debugger:
            self.debugger.log_error(message)

    def transition_to(self, new_stage: str):
        duration_ms = int((time.time() - self.stage_start_time) * 1000)
        if self.current_stage != PipelineState.REQUEST_RECEIVED:
            self.timings[f"{self.current_stage}_ms"] = duration_ms
            self.log(f"Finished {self.current_stage} in {duration_ms}ms")
            
        self.current_stage = new_stage
        self.stage_start_time = time.time()
        self.log(f"Started {self.current_stage}")
        
        # Track timing changes in execution object
        self.execution.timings = self.timings

    def save_checkpoint(self, key: str, value: Any):
        self.context[key] = value

    async def execute_with_timeout(self, callable_obj, timeout_seconds: int, stage_name="Unknown", retries: int = 1):
        attempts = retries + 1
        last_exception = None
        
        for attempt in range(1, attempts + 1):
            try:
                coro = callable_obj() if callable(callable_obj) else callable_obj
                return await asyncio.wait_for(coro, timeout=timeout_seconds)
            except asyncio.TimeoutError as e:
                self.error(f"Timeout in {stage_name} on attempt {attempt}/{attempts} after {timeout_seconds}s")
                last_exception = TimeoutError(f"Timeout in {stage_name} after {timeout_seconds}s")
                if attempt < attempts:
                    await asyncio.sleep(0.5)
            except Exception as e:
                self.error(f"Exception in {stage_name} on attempt {attempt}/{attempts}: {str(e)}", exc_info=True)
                last_exception = e
                if attempt < attempts:
                    await asyncio.sleep(0.5)
                    
        raise last_exception

    def handle_exception(self, error: Exception):
        import traceback
        stack_trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        
        stage = self.current_stage
        conv_id = self.conversation_id
        req_id = self.request_id
        planner_state = self.execution.planner
        chunk_count = self.execution.retrieval.get("chunks_retrieved", 0)
        
        # Log to error system with exact parameters
        error_msg = (
            f"Pipeline Exception Occurred!\n"
            f"FAILED_AT = {stage}\n"
            f"CONVERSATION_ID = {conv_id}\n"
            f"REQUEST_ID = {req_id}\n"
            f"PLANNER_STATE = {planner_state}\n"
            f"RETRIEVED_CHUNK_COUNT = {chunk_count}\n"
            f"Stack Trace:\n{stack_trace}"
        )
        self.error(error_msg, exc_info=True)
        self.execution.errors.append(error_msg)
        self.transition_to(PipelineState.FAILED)
        
        # Save execution logs on failure
        if self.debugger:
            self.debugger.save_execution(self.execution.model_dump())

    def finish(self, success: bool = True):
        duration_ms = int((time.time() - self.stage_start_time) * 1000)
        self.timings[f"{self.current_stage}_ms"] = duration_ms
        self.current_stage = PipelineState.COMPLETED if success else PipelineState.FAILED
        
        total_time = sum(v for k, v in self.timings.items() if k.endswith("_ms"))
        self.timings["total_ms"] = total_time
        
        self.execution.timings = self.timings
        self.execution.completed = success
        
        if self.debugger:
            self.debugger.save_timings(self.timings)
            self.debugger.save_execution(self.execution.model_dump())
            
        self.log(f"Pipeline finished with success={success}. Total time: {total_time}ms")
        
    def validate_final_state(self):
        if not self.context.get("prompt_exists"):
            self.error("Validation Failed: Prompt was not built.")
            return False
        if not self.context.get("llm_output_exists"):
            self.error("Validation Failed: LLM did not produce output.")
            return False
        if not self.context.get("assistant_saved"):
            self.error("Validation Failed: Assistant message was not persisted.")
            return False
        return True
