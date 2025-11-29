import asyncio
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List
from unittest.mock import patch

import pytest
from dotenv import load_dotenv

from ltm_agent.pipeline import run_pipeline
from ltm_agent.tools import ToolRegistry, load_external_tool

load_dotenv()


@dataclass
class ToolMock:
    """Configuration for mocking a tool."""

    tool_spec_pattern: str
    mock_function: Callable
    call_log: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PipelineTestCase:
    """Test case for pipeline execution."""

    test_id: str
    query: str
    tool_mocks: List[ToolMock]
    verify_output: Callable[[List[Any], List[ToolMock]], None]
    pipeline_name: str = "planning_full"
    config_path: str = "pipelines"
    flaky: bool = False
    flaky_reason: str = ""


def extract_final_output(events: List[Any]) -> str:
    """Extract final text output from events."""
    for event in reversed(events):
        if hasattr(event, "content") and event.content:
            if hasattr(event.content, "parts") and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        text = part.text.strip()
                        if text and not text.startswith("FINAL"):
                            return text
    return ""


def create_weather_mock(location_response_map: Dict[str, Dict[str, Any]]) -> ToolMock:
    """Create a weather tool mock with specified responses."""
    call_log = []

    def mock_weather_func(location: str):
        call_log.append({"location": location})
        for key, response in location_response_map.items():
            if key.lower() in location.lower():
                return response
        return location_response_map.get("default", {"error": "location not found"})

    return ToolMock(tool_spec_pattern="get_weather", mock_function=mock_weather_func, call_log=call_log)


def create_fibonacci_mock(number_response_map: Dict[int, int]) -> ToolMock:
    """Create a fibonacci tool mock with specified responses."""
    call_log = []

    def mock_fibonacci_func(n: int):
        call_log.append({"n": n})
        return number_response_map.get(n, 0)

    return ToolMock(tool_spec_pattern="calculate_fibonacci", mock_function=mock_fibonacci_func, call_log=call_log)


def verify_weather_output(events: List[Any], mocks: List[ToolMock]) -> None:
    """Verify weather query output."""
    weather_mock = next((m for m in mocks if "weather" in m.tool_spec_pattern), None)
    assert weather_mock is not None, "Weather mock not found"
    assert len(weather_mock.call_log) > 0, "Weather tool should have been called"

    call_locations = [call["location"].lower() for call in weather_mock.call_log]
    assert any("london" in loc for loc in call_locations), f"Weather tool should have been called with 'london', got: {call_locations}"

    final_output = extract_final_output(events)
    assert final_output is not None, "Should have a final output"

    weather_pattern = re.compile(r"WEATHER:\s*(\d+\.?\d*)")
    match = weather_pattern.search(final_output)

    assert match is not None, f"Output should match WEATHER:<TEMP> format, got: {final_output}"

    extracted_temp = float(match.group(1))
    expected_temp = 15.0

    assert abs(extracted_temp - expected_temp) <= 1.0, f"Temperature should be close to {expected_temp}, got {extracted_temp}"


def verify_fibonacci_output(events: List[Any], mocks: List[ToolMock]) -> None:
    """Verify fibonacci query output matches expected format FIB:<NUMBER>."""
    fib_mock = next((m for m in mocks if "fibonacci" in m.tool_spec_pattern), None)
    assert fib_mock is not None, "Fibonacci mock not found"
    assert len(fib_mock.call_log) > 0, "Fibonacci tool should have been called"

    called_numbers = [call["n"] for call in fib_mock.call_log]
    assert 10 in called_numbers, f"Fibonacci tool should have been called with n=10, got: {called_numbers}"

    final_output = extract_final_output(events)
    assert final_output is not None, "Should have a final output"

    fib_pattern = re.compile(r"FIB:\s*(\d+)")
    match = fib_pattern.search(final_output)
    assert match is not None, f"Output should match FIB:<NUMBER> format, got: {final_output}"

    extracted_value = int(match.group(1))
    expected_value = 55

    assert extracted_value == expected_value, f"Fibonacci value should be {expected_value}, got {extracted_value}"


def verify_multiple_cities_weather(events: List[Any], mocks: List[ToolMock]) -> None:
    """Verify weather comparison output matches expected format COLDER:<CITY>."""
    weather_mock = next((m for m in mocks if "weather" in m.tool_spec_pattern), None)
    assert weather_mock is not None, "Weather mock not found"
    assert len(weather_mock.call_log) >= 2, "Weather tool should have been called at least twice"

    call_locations = [call["location"].lower() for call in weather_mock.call_log]
    assert any("london" in loc for loc in call_locations), "Should have queried London"
    assert any("paris" in loc for loc in call_locations), "Should have queried Paris"

    final_output = extract_final_output(events)
    assert final_output is not None, "Should have a final output"

    colder_pattern = re.compile(r"COLDER:\s*(\w+)", re.IGNORECASE)
    colder_matches = colder_pattern.findall(final_output)

    assert colder_matches, f"Output should match COLDER:<CITY> format, got: {final_output}"

    extracted_city = colder_matches[-1].lower()
    expected_colder_city = "london"

    assert extracted_city == expected_colder_city, f"Colder city should be {expected_colder_city}, got {extracted_city} in {final_output}"


def verify_code_execution_calculation(events: List[Any], mocks: List[ToolMock]) -> None:
    """Verify code executor can solve complex calculations and output in correct format."""
    final_output = extract_final_output(events)
    assert final_output is not None, "Should have a final output"

    sum_pattern = re.compile(r"SUM:\s*(\d+)")
    match = sum_pattern.search(final_output)

    assert match is not None, f"Output should match SUM:<NUMBER> format, got: {final_output}"

    extracted_sum = int(match.group(1))
    expected_sum = sum(range(1, 101))

    assert extracted_sum == expected_sum, f"Sum should be {expected_sum}, got {extracted_sum}"


TEST_CASES = [
    PipelineTestCase(
        test_id="weather_london",
        query="show temperature in london in one line as WEATHER:<TEMP>",
        tool_mocks=[create_weather_mock({"london": {"location": "London", "temperature": 15.0, "humidity": 65, "weather_code": 0}})],
        verify_output=verify_weather_output,
    ),
    PipelineTestCase(
        test_id="fibonacci_10",
        query="calculate the 10th fibonacci number and show result as FIB:<NUMBER>",
        tool_mocks=[create_fibonacci_mock({10: 55})],
        verify_output=verify_fibonacci_output,
    ),
    PipelineTestCase(
        test_id="weather_multiple_cities",
        query="compare temperatures in London and Paris, show which is colder as COLDER:<CITY>",
        tool_mocks=[
            create_weather_mock(
                {
                    "london": {"location": "London", "temperature": 15.0, "humidity": 65, "weather_code": 0},
                    "paris": {"location": "Paris", "temperature": 18.0, "humidity": 70, "weather_code": 1},
                }
            )
        ],
        verify_output=verify_multiple_cities_weather,
    ),
    PipelineTestCase(
        test_id="code_executor_sum",
        query="calculate the sum of all numbers from 1 to 100 using code execution and show result as SUM:<NUMBER>",
        tool_mocks=[],
        verify_output=verify_code_execution_calculation,
        flaky=True,
        flaky_reason="Code executor test is flaky due to timing and environment dependencies",
    ),
]

MAX_RUNS_PER_TEST = int(os.environ.get("LTM_AGENT_TEST_MAX_RUNS_PER_TEST", "3"))
PIPELINE_TIMEOUT_SECONDS = 15


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda tc: tc.test_id)
@pytest.mark.parametrize("executions", range(0, MAX_RUNS_PER_TEST), ids=lambda i: f"run_{i + 1}")
async def test_pipeline_with_mocks(test_case: PipelineTestCase, executions: int, request):
    """Generic test for pipeline execution with mocked tools."""

    # Mark flaky tests with xfail
    if test_case.flaky:
        marker = pytest.mark.xfail(
            reason=test_case.flaky_reason,
            strict=False,  # Don't fail if test passes
            run=True,  # Still run the test
        )
        request.node.add_marker(marker)

    original_load_external_tool = load_external_tool

    def patched_load_external_tool(tool_spec: str):
        for mock in test_case.tool_mocks:
            if mock.tool_spec_pattern in tool_spec:
                return mock.mock_function
        return original_load_external_tool(tool_spec)

    tool_registry = ToolRegistry()

    with patch("ltm_agent.tools.load_external_tool", side_effect=patched_load_external_tool):
        try:
            events = await asyncio.wait_for(
                run_pipeline(test_case.config_path, test_case.pipeline_name, test_case.query, tool_registry, debug=False, verbose=False),
                timeout=PIPELINE_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            pytest.fail(f"Pipeline execution exceeded {PIPELINE_TIMEOUT_SECONDS} seconds timeout for test: {test_case.test_id}")

        test_case.verify_output(events, test_case.tool_mocks)
