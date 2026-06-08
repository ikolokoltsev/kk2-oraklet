import logging
from transformers import pipeline
from pydantic import BaseModel
from app.chain.runnable import Runnable
from app.config import settings
from app.schemas import AskResponse
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

logger = logging.getLogger(__name__)


class PromptBuilderInput(BaseModel):
    question: str
    stats: dict


class PromptBuilderOutput(BaseModel):
    messages: list[dict]
    question: str


class LLMRunnerOutput(BaseModel):
    raw_text: str
    question: str

class PromptBuilder(Runnable[PromptBuilderInput, PromptBuilderOutput]):
    name: str = "prompt_builder"

    def invoke(self, data: PromptBuilderInput) -> PromptBuilderOutput:
        stats_text = "\n".join(f"{col}: {vals}" for col, vals in data.stats.items())
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a data analyst assistant. "
                    "Answer questions about the dataset concisely and accurately. "
                    "Base your answers only on the statistics provided. "
                    "Response in the same language as the question."
                ),
            },  
            {
                "role": "user",
                "content": f"Dataset statistics:\n{stats_text}\n\nQuestion: {data.question}",
            },
        ]   
        logger.info("Prompt built for question: %s", data.question)
        return PromptBuilderOutput(messages=messages, question=data.question)

class LLMRunner(Runnable[PromptBuilderOutput, LLMRunnerOutput]):
    name: str = "llm_runner"
    
    def invoke(self, data: PromptBuilderOutput) -> LLMRunnerOutput:
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            pipe = pipeline("text-generation", model=settings.model_name)
            logger.info("Calling model: %s", settings.model_name)
            future = executor.submit(pipe, data.messages, max_new_tokens=200)
            result = future.result(timeout=settings.model_timeout_seconds)
            raw_text = result[0]["generated_text"]
            if isinstance(raw_text, list):
                raw_text = raw_text[-1].get("content", "")
            return LLMRunnerOutput(raw_text=str(raw_text), question=data.question)
        except FuturesTimeout as e:
            logger.error("Model timed out after %ss", settings.model_timeout_seconds)
            raise RuntimeError("Model timed out") from e
        except Exception as e:
            logger.exception("Model error: %s", e)
            raise RuntimeError(f"Model failed: {e}") from e
        finally:
            executor.shutdown(wait=False)

class ResponseParser(Runnable[LLMRunnerOutput, "AskResponse"]):
    name: str = "response_parser"

    def invoke(self, data: LLMRunnerOutput) -> "AskResponse":
        from app.schemas import AskResponse 
        text = data.raw_text.strip()
        if not text:
            text = "The model did not return a response."
        if "assistant" in text.lower():
            parts = text.split("assistant", 1)
            if len(parts) > 1:
                text = parts[-1].strip().lstrip("\n").strip()
        return AskResponse(
            question=data.question,
            answer=text[:500],
            model=settings.model_name,
        )