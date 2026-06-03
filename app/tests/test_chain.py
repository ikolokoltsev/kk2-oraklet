from app.chain.steps import (
    PromptBuilder, PromptBuilderInput,
    ResponseParser, LLMRunnerOutput,
)   


def test_prompt_builder_includes_question():
    step = PromptBuilder()
    result = step.invoke(PromptBuilderInput(
        question="What is the average?",
        stats={"col1": {"mean": 2.0}}
    ))
    assert "What is the average?" in str(result.messages)
    assert "mean" in str(result.messages)
    

def test_prompt_builder_has_system_message():
    step = PromptBuilder()
    result = step.invoke(PromptBuilderInput(question="q", stats={}))
    assert result.messages[0]["role"] == "system"


def test_response_parser_extracts_answer():
    step = ResponseParser()
    result = step.invoke(LLMRunnerOutput(raw_text="The answer is 42.", question="What?"))
    assert result.answer == "The answer is 42."
    assert result.question == "What?"
    

def test_response_parser_fallback_on_empty():
    step = ResponseParser()
    result = step.invoke(LLMRunnerOutput(raw_text="", question="What?"))
    assert len(result.answer) > 0