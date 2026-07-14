import os
import json
import logging
from datetime import datetime
from app.ai.config import ai_config

logger = logging.getLogger(__name__)

class DebugLogger:
    def __init__(self, pipeline_id: str):
        self.pipeline_id = pipeline_id
        self.enabled = ai_config.AI_DEBUG
        
        if not self.enabled:
            self.debug_dir = None
            return
            
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Anchor directory to backend/logs/
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.debug_dir = os.path.join(base_dir, "logs", today, f"pipeline_{pipeline_id}")
        
        try:
            os.makedirs(self.debug_dir, exist_ok=True)
            logger.info(f"Initialized debug directory at {self.debug_dir}")
        except Exception as e:
            logger.error(f"Failed to create debug directory: {e}")
            self.debug_dir = None

    def save_request(self, data: dict):
        self._write_json("request.json", data)

    def save_planner(self, plan_dict: dict):
        self._write_json("planner.json", plan_dict)

    def save_retrieval(self, chunks: list):
        self._write_json("retrieval.json", chunks)

    def save_optimized_context(self, context_chunks: list):
        self._write_json("optimized_context.json", context_chunks)

    def save_prompt(self, prompt: str, builder_version: str = "1.0.0", template_version: str = "1.0.0", system_prompt_hash: str = "N/A"):
        header = (
            f"============================================================\n"
            f"PROMPT METADATA:\n"
            f"Prompt Builder Version: {builder_version}\n"
            f"Prompt Template Version: {template_version}\n"
            f"System Prompt Hash: {system_prompt_hash}\n"
            f"============================================================\n\n"
        )
        self._write_text("prompt.txt", header + prompt)

    def save_completion(self, completion: str):
        self._write_text("completion.txt", completion)

    def save_timings(self, timings: dict):
        self._write_json("timings.json", timings)

    def log_error(self, error: str):
        self._append_text("errors.log", f"[{datetime.now().isoformat()}] {error}")

    def save_execution(self, execution_dict: dict):
        self._write_json("execution.json", execution_dict)

    def _write_json(self, filename: str, data: dict | list):
        if not self.debug_dir:
            return
        try:
            with open(os.path.join(self.debug_dir, filename), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to write debug json {filename}: {e}")

    def _write_text(self, filename: str, text: str):
        if not self.debug_dir:
            return
        try:
            with open(os.path.join(self.debug_dir, filename), "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            logger.error(f"Failed to write debug text {filename}: {e}")
            
    def _append_text(self, filename: str, text: str):
        if not self.debug_dir:
            return
        try:
            with open(os.path.join(self.debug_dir, filename), "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception as e:
            logger.error(f"Failed to append debug text {filename}: {e}")
