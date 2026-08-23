"""Tests for benchmark prompt domain models."""

import pytest

from domain.benchmarks.prompt import BenchmarkPrompt, PromptCategory


def test_benchmark_prompt_can_be_created() -> None:
    prompt = BenchmarkPrompt(
        prompt_id="prompt-1",
        category=PromptCategory.SHORT,
        text="What is artificial intelligence?",
    )

    assert prompt.prompt_id == "prompt-1"
    assert prompt.category is PromptCategory.SHORT
    assert prompt.text == "What is artificial intelligence?"


@pytest.mark.parametrize(
    "category",
    [
        PromptCategory.SHORT,
        PromptCategory.REASONING,
        PromptCategory.GENERATION,
        PromptCategory.CODE,
    ],
)
def test_benchmark_prompt_supports_categories(
    category: PromptCategory,
) -> None:
    prompt = BenchmarkPrompt(
        prompt_id="prompt-1",
        category=category,
        text="Benchmark this prompt.",
    )

    assert prompt.category is category


@pytest.mark.parametrize(
    "prompt_id",
    [
        "",
        " ",
        "   ",
    ],
)
def test_benchmark_prompt_rejects_empty_id(
    prompt_id: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="prompt_id cannot be empty",
    ):
        BenchmarkPrompt(
            prompt_id=prompt_id,
            category=PromptCategory.SHORT,
            text="Valid prompt",
        )


@pytest.mark.parametrize(
    "text",
    [
        "",
        " ",
        "   ",
    ],
)
def test_benchmark_prompt_rejects_empty_text(
    text: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="prompt text cannot be empty",
    ):
        BenchmarkPrompt(
            prompt_id="prompt-1",
            category=PromptCategory.SHORT,
            text=text,
        )