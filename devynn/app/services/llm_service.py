"""
LLM inference service wrapper to load models async and serve responses.
"""
import asyncio
import time
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._loaded = False
        self._version = "unknown"

    async def load(self, model_path: str, version: str = "unknown"):
        # Run sync model loading in executor so it doesn't block event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._load_sync(model_path))
        self._version = version
        self._loaded = True
        logger.info(f"Loaded LLM model: {model_path} / {version}")

    def _load_sync(self, model_path: str):
        if model_path == "mock":
            return
            
        try:
            from peft import PeftModel, PeftConfig
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            import torch
            from huggingface_hub import login
            
            # Optional Hub login if needed
            try:
                login(token="your_hf_api_key")
            except Exception:
                pass

            base_model_id = "mistralai/Mistral-7B-Instruct-v0.2"
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_id,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
            )

            tokenizer = AutoTokenizer.from_pretrained(
                base_model_id,
                model_max_length=512,
                padding_side="left",
                add_eos_token=True
            )
            tokenizer.pad_token = tokenizer.eos_token

            self._model = PeftModel.from_pretrained(base_model, model_path)
            self._tokenizer = tokenizer
            
        except Exception as e:
            logger.error(f"Failed to load LLM sync step: {e}")
            raise

    async def generate(self, transcript: str, domain: str) -> tuple[str, list[str], int]:
        from model.inference import generate_output
        start = time.perf_counter()
        
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(
            None, lambda: generate_output(transcript, domain, self._model, self._tokenizer)
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        # Parse "Grammar:" section from raw output if present
        if "Grammar:" in raw:
            parts = raw.split("Grammar:", 1)
            ai_resp = parts[0].strip()
            grammar_notes = [l.strip() for l in parts[1].splitlines() if l.strip()]
            return ai_resp, grammar_notes, latency_ms
            
        return raw.strip(), [], latency_ms

    @property
    def is_loaded(self): return self._loaded
    @property
    def version(self): return self._version
