"""Tests for the vLLM OpenAI-compatible benchmark executor."""

from collections.abc import Iterator
from unittest.mock import patch

import httpx
import pytest

from infrastructure.llm.vllm_benchmark_executor import (
    VLLMBenchmarkError,
    VLLMBenchmarkExecutor,
)


def make_response(
    status_code: int,
    json_body: object,
    *,
    url: str,
) -> httpx.Response:
    request = httpx.Request("GET", url)
    return httpx.Response(
        status_code,
        json=json_body,
        request=request,
    )


def test_execute_success_uses_usage_tokens_and_measures_latency() -> None:
    """Successful execution should return metrics from vLLM usage."""

    clock_values: Iterator[float] = iter([10.0, 12.5])

    executor = VLLMBenchmarkExecutor(
        base_url="http://vllm:8000/",
        timeout_seconds=30.0,
        clock=lambda: next(clock_values),
    )

    models_response = make_response(
        200,
        {
            "data": [
                {"id": "smollm2-360m"},
            ]
        },
        url="http://vllm:8000/v1/models",
    )

    completion_response = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": "Benchmark response",
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 7,
                "completion_tokens": 11,
            },
        },
        request=httpx.Request(
            "POST",
            "http://vllm:8000/v1/chat/completions",
        ),
    )

    with (
        patch(
            "infrastructure.llm.vllm_benchmark_executor.httpx.get",
            return_value=models_response,
        ) as get_mock,
        patch(
            "infrastructure.llm.vllm_benchmark_executor.httpx.post",
            return_value=completion_response,
        ) as post_mock,
    ):
        result = executor.execute(
            model="smollm2-360m",
            prompt="Hello",
        )

    assert result.total_latency_ms == 2500.0
    assert result.ttft_ms == 2500.0
    assert result.duration_seconds == 2.5
    assert result.tokens_generated == 11
    assert result.prompt_tokens == 7
    assert result.prompt_eval_duration_seconds is None

    get_mock.assert_called_once_with(
        "http://vllm:8000/v1/models",
        timeout=30.0,
    )

    post_mock.assert_called_once_with(
        "http://vllm:8000/v1/chat/completions",
        json={
            "model": "smollm2-360m",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                }
            ],
            "max_tokens": 96,
            "temperature": 0.0,
            "stream": False,
        },
        timeout=30.0,
    )


def test_execute_estimates_completion_tokens_when_usage_missing() -> None:
    """Missing completion token usage should fall back to content estimation."""

    clock_values: Iterator[float] = iter([5.0, 6.0])

    executor = VLLMBenchmarkExecutor(
        clock=lambda: next(clock_values),
    )

    models_response = make_response(
        200,
        {
            "data": [
                {"id": "demo-model"},
            ]
        },
        url="http://127.0.0.1:8000/v1/models",
    )

    completion_response = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": "one two three four",
                    }
                }
            ]
        },
        request=httpx.Request(
            "POST",
            "http://127.0.0.1:8000/v1/chat/completions",
        ),
    )

    with (
        patch(
            "infrastructure.llm.vllm_benchmark_executor.httpx.get",
            return_value=models_response,
        ),
        patch(
            "infrastructure.llm.vllm_benchmark_executor.httpx.post",
            return_value=completion_response,
        ),
    ):
        result = executor.execute(
            model="demo-model",
            prompt="Benchmark",
        )

    assert result.tokens_generated == 4
    assert result.prompt_tokens is None
    assert result.duration_seconds == 1.0


def test_execute_clamps_zero_latency_to_minimum_positive_value() -> None:
    """Measured duration should never be zero."""

    executor = VLLMBenchmarkExecutor(
        clock=lambda: 10.0,
    )

    models_response = make_response(
        200,
        {
            "data": [
                {"id": "demo-model"},
            ]
        },
        url="http://127.0.0.1:8000/v1/models",
    )

    completion_response = httpx.Response(
        200,
        json={
            "usage": {
                "completion_tokens": 1,
            }
        },
        request=httpx.Request(
            "POST",
            "http://127.0.0.1:8000/v1/chat/completions",
        ),
    )

    with (
        patch(
            "infrastructure.llm.vllm_benchmark_executor.httpx.get",
            return_value=models_response,
        ),
        patch(
            "infrastructure.llm.vllm_benchmark_executor.httpx.post",
            return_value=completion_response,
        ),
    ):
        result = executor.execute(
            model="demo-model",
            prompt="Benchmark",
        )

    assert result.duration_seconds == 0.000001
    assert result.total_latency_ms == 0.001


def test_execute_raises_clear_error_for_http_failure() -> None:
    """HTTP benchmark failures should preserve status and API detail."""

    executor = VLLMBenchmarkExecutor()

    models_response = make_response(
        200,
        {
            "data": [
                {"id": "demo-model"},
            ]
        },
        url="http://127.0.0.1:8000/v1/models",
    )

    completion_response = httpx.Response(
        500,
        json={
            "detail": "engine crashed",
        },
        request=httpx.Request(
            "POST",
            "http://127.0.0.1:8000/v1/chat/completions",
        ),
    )

    with (
        patch(
            "infrastructure.llm.vllm_benchmark_executor.httpx.get",
            return_value=models_response,
        ),
        patch(
            "infrastructure.llm.vllm_benchmark_executor.httpx.post",
            return_value=completion_response,
        ),
        pytest.raises(VLLMBenchmarkError) as exc_info,
    ):
        executor.execute(
            model="demo-model",
            prompt="Benchmark",
        )

    assert "HTTP 500" in str(exc_info.value)
    assert "engine crashed" in str(exc_info.value)


def test_execute_wraps_request_error() -> None:
    """Network failures should be converted to domain-specific errors."""

    executor = VLLMBenchmarkExecutor(
        base_url="http://vllm.local/",
    )

    models_response = make_response(
        200,
        {
            "data": [
                {"id": "demo-model"},
            ]
        },
        url="http://vllm.local/v1/models",
    )

    request = httpx.Request(
        "POST",
        "http://vllm.local/v1/chat/completions",
    )

    with (
        patch(
            "infrastructure.llm.vllm_benchmark_executor.httpx.get",
            return_value=models_response,
        ),
        patch(
            "infrastructure.llm.vllm_benchmark_executor.httpx.post",
            side_effect=httpx.ConnectError(
                "connection refused",
                request=request,
            ),
        ),
        pytest.raises(VLLMBenchmarkError) as exc_info,
    ):
        executor.execute(
            model="demo-model",
            prompt="Benchmark",
        )

    message = str(exc_info.value)

    assert "Unable to execute benchmark against vLLM" in message
    assert "http://vllm.local" in message


def test_model_listing_http_error_reports_detail() -> None:
    """Model-list HTTP failures should expose useful API detail."""

    executor = VLLMBenchmarkExecutor()

    response = httpx.Response(
        503,
        json={
            "error": "model server unavailable",
        },
        request=httpx.Request(
            "GET",
            "http://127.0.0.1:8000/v1/models",
        ),
    )

    with (
        patch(
            "infrastructure.llm.vllm_benchmark_executor.httpx.get",
            return_value=response,
        ),
        pytest.raises(VLLMBenchmarkError) as exc_info,
    ):
        executor.execute(
            model="demo-model",
            prompt="Benchmark",
        )

    assert "HTTP 503" in str(exc_info.value)
    assert "model server unavailable" in str(exc_info.value)


def test_model_listing_request_error_is_wrapped() -> None:
    """Network errors while listing models should be wrapped."""

    executor = VLLMBenchmarkExecutor(
        base_url="http://vllm.local",
    )

    request = httpx.Request(
        "GET",
        "http://vllm.local/v1/models",
    )

    with (
        patch(
            "infrastructure.llm.vllm_benchmark_executor.httpx.get",
            side_effect=httpx.ConnectError(
                "connection refused",
                request=request,
            ),
        ),
        pytest.raises(VLLMBenchmarkError) as exc_info,
    ):
        executor.execute(
            model="demo-model",
            prompt="Benchmark",
        )

    message = str(exc_info.value)

    assert "Unable to list vLLM models" in message
    assert "http://vllm.local" in message


def test_unavailable_model_lists_available_models() -> None:
    """Unknown model errors should report models currently served by vLLM."""

    executor = VLLMBenchmarkExecutor()

    response = make_response(
        200,
        {
            "data": [
                {"id": "model-b"},
                {"id": "model-a"},
                {"ignored": "missing-id"},
                "invalid",
            ]
        },
        url="http://127.0.0.1:8000/v1/models",
    )

    with (
        patch(
            "infrastructure.llm.vllm_benchmark_executor.httpx.get",
            return_value=response,
        ),
        pytest.raises(VLLMBenchmarkError) as exc_info,
    ):
        executor.execute(
            model="missing-model",
            prompt="Benchmark",
        )

    message = str(exc_info.value)

    assert "Model not available in vLLM: missing-model." in message
    assert "Available models: model-a, model-b." in message


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0),
        (12, 12),
        (-1, None),
        ("12", None),
        (None, None),
    ],
)
def test_positive_int(value: object, expected: int | None) -> None:
    """Only non-negative integers are valid token counts."""

    assert VLLMBenchmarkExecutor._positive_int(value) == expected


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (None, 0),
        ({}, 0),
        ({"choices": "invalid"}, 0),
        ({"choices": []}, 0),
        ({"choices": ["invalid"]}, 0),
        ({"choices": [{}]}, 0),
        ({"choices": [{"message": "invalid"}]}, 0),
        ({"choices": [{"message": {"content": None}}]}, 0),
        (
            {
                "choices": [
                    {
                        "message": {
                            "content": "one two three",
                        }
                    }
                ]
            },
            3,
        ),
    ],
)
def test_estimate_completion_tokens(
    body: object,
    expected: int,
) -> None:
    """Completion token estimation should safely handle malformed responses."""

    assert (
        VLLMBenchmarkExecutor._estimate_completion_tokens(body)
        == expected
    )


def test_response_detail_uses_plain_text_for_non_json_response() -> None:
    """Plain-text API failures should remain readable."""

    response = httpx.Response(
        500,
        text="plain vLLM failure",
        request=httpx.Request(
            "POST",
            "http://127.0.0.1:8000/v1/chat/completions",
        ),
    )

    assert (
        VLLMBenchmarkExecutor._response_detail(response)
        == "plain vLLM failure"
    )


def test_response_detail_falls_back_to_json_body() -> None:
    """JSON without detail/error should still produce a useful message."""

    response = httpx.Response(
        400,
        json={
            "message": "invalid request",
        },
        request=httpx.Request(
            "POST",
            "http://127.0.0.1:8000/v1/chat/completions",
        ),
    )

    detail = VLLMBenchmarkExecutor._response_detail(response)

    assert "invalid request" in detail