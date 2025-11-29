# Little Thinking Model (LTM)

<html>
    <h2 align="center">
      <img src="https://raw.githubusercontent.com/sumkincpp/ltm-agent/refs/heads/main/assets/little-thinking-model.jpg" width="256"/>
    </h2>
</html>

**Little Thinking Model (LTM)** is an agentic system built on Google's ADK that implements iterative multi-step reasoning with verification of user constraints.

It combines:

- **The Model** (Brain): Gemini models for reasoning and decision-making
- **Tools** (Hands): External function calling capabilities for real-world actions
- **Orchestration Layer** (Nervous System): Agent classes and YAML-configured agent pipelines managing the "Think, Act, Observe" loop

The agent system enables the creation of complex agent pipelines using simple YAML configuration files,
allowing for easy integration of external tools via function calling and multi-step reasoning with context engineering.

> **Note:** This project was developed as a capstone project for the [5-Day AI Agents Intensive Course with Google](https://www.kaggle.com/learn-guide/5-day-agents) (Nov 10–14, 2025).

## Features

- YAML-configured agent pipelines
- Easy-to-use command-line interface
- Easy external tool integration via function calling
- Orchestration layer with multi-step reasoning and context engineering
- Google ADK-based agents: Agent, LoopAgent, ParallelAgent, SequentialAgent
  - New agents: ThinkingAgent

## Goals

Before starting this project, the following goals were set:

- YAML-based configuration for defining agent pipelines using Google's ADK Agent classes (Agent, LoopAgent, ParallelAgent, SequentialAgent)
- Easy integration of external tools

> Iterative multi-step reasoning with verification of user constraints was not a key focus of this project, but it was possible to achieve.

## Little "thinking agent"

### Motivation

Complex tasks we provide to Large Language Models often require multiple steps of reasoning with complex logical reasoning (filtering, aggregation, ..), tool calling, and verification of user constraints. In these scenarios, simple LLM-based agents frequently struggle to provide complete and correct answers due to their limited attention capabilities.

While LLMs excel at generating human-like text, they face challenges with deep reasoning tasks that require maintaining context across multiple steps and ensuring all user requirements are satisfied.

For example, lets's consider following query:

```bash
"show 2 cities where temp > 10, round temperatures, show fibonacci F(temp)"
```

A simple agent may get confused how many cities should be shown or queried. Some agents may also forget to filter temperatures or calculate Fibonacci values on rounded temperatures. Others will provide partial answers without verifying that all user constraints are met.

### Concepts - The Thinking Agent Pattern

Inspired by [Google's ADK LoopAgent](https://google.github.io/adk-docs/agents/workflow-agents/loop-agents/) architecture, iterative refinement pattern was implemented in the thinking agent. The key idea is to break down complex tasks into smaller, manageable steps, allowing the model to plan, verify, and refine its approach iteratively.

1. **Decompose** - Break the request down into clear, testable requirements.
2. **Plan** - Plan in small steps and keep a transparent record of choices and tool use.
3. **Verify** - Verify constraints after each step and measure progress against the goal.
4. **Refine** - Correct itself when needed by re-planning if checks fail.
5. **Observe** - Expose the full reasoning path so it’s easy to review and debug.

The model effectively examines and adjusts its own reasoning as it goes.

When it comes to implementation of this idea, we need to use prompt and context engineering techniques to guide the model's reasoning process.

This involves explicitly instructing the model on how to approach the problem:

- We should explain what a model is capable of: math operations, filtering, counting,
  comparing, aggregating
- We may explain what a model is NOT capable of
- We should explain how to decompose user requests into specific requirements
- We should explain how to evaluate progress and fulfill requirements step by step
- We should remind a model that it can infer knowledge based on facts
  (e.g., Wien and Vienna are the same city)

One technique to achieve this is to reconcile user requests with the model itself, forcing the model to remind itself of the problem at each step. The model should be encouraged to analyze its own progress and verify ongoing work. Verification can be performed by other AI agents as well.

No matter how good a model is, there's no way around but to rely on sophisticated prompting and orchestration layer techniques to guide the model's reasoning process.

### Results

Experiments with the lightweight gemini-2.5-flash-lite model show that agents using iterative steps and verification loops often outperform much larger LLMs that try to handle a problem in a single pass.

This matches Google’s observation that domain-specific agents tend to surpass single, monolithic agents on complex tasks:

> "Single agents that try to do research, writing, editing, and fact-checking all at once become problematic. The instruction prompt gets long and confusing, making them hard to debug and often producing unreliable results." — Google ADK Documentation

It is well known that large LLMs with billions of parameters (32B, 400B) require substantial computational resources, yet they do not automatically produce better results on tasks that involve several reasoning steps. Without structure and guidance, their performance tends to stall as task complexity increases.

To conclude, large LLMs are capable of sophisticated, domain-specific reasoning, but that capability does not necessarily translate into better performance on multi-step reasoning tasks without proper guidance. Domain-specific knowledge is often handled more effectively by agentic systems, since they allow external tools to be integrated via function calling and give precise control over the reasoning process through the orchestration layer.

### Iterative Problem-Solving Process

Current system prompt used is available at [src/ltm_agent/prompts/thinking_agent.txt](src/ltm_agent/prompts/thinking_agent.txt)

![Iterative Problem-Solving Flow](./docs/iterative-process.svg)

### Architecture

This project implements a modular architecture for building agentic systems using Google's ADK framework.

![Architecture Diagram](./docs/ltm-agent-architecture.svg)

#### Components

- **YAML Configuration**: Defines defaults, agents, pipelines, and tools
- **Pipeline Builder**: Builds agents from YAML config (Supports dynamic module loading, sync/async tools, automatic logging wrappers)
- **Agent Registry**: Lazy instantiation of discovered agents for pipelines
- **Agent Types** (Google ADK): Agent, SequentialAgent, ParallelAgent, LoopAgent, CodeExecutorAgent, ThinkingAgent (novel),
- **Tool System**: Tool registry, Tool Proxy, external Tool Loader
- **External Tools**: external pluggable tools via YAML config (eg. weather_tool, fibonacci_tool, db_search, current_time, google_search)
- **InMemoryRunner**: Google ADK backend for session management and event streaming

## Usage

### Requirements

- Python 3.10+
- [uv (package manager)](https://docs.astral.sh/uv/getting-started/installation/) or python pip 

### Configuring Project 

Next a Gemini API key is needed. See [Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key#api-keys)

```bash
export GOOGLE_API_KEY="your_gemini_api_key_here"
```

Alternatively, save it in a `.env` file in the project root:

```bash
GOOGLE_API_KEY="your_gemini_api_key_here"
```

If uv is used as package manager, install dependencies and activate the environment with:

```bash
uv install
source .venv/bin/activate
```

Alternatively, with pip, create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Next, to check that everything is set up correctly, list available pipelines with:

```bash
ltm-agent list
```

API Key is required to run pipelines that use Gemini model.

### Running Pipelines

Pipelines are defined in the `pipelines/` directory, which is loaded automatically. Pipelines get a name of the form `[pipeline_file_name]::[pipeline_name]`.

To list available pipelines, use:

```bash
$ ltm-agent list

Available pipelines:

[google-day1] pipelines/google-day1.yaml
  * google-day1::research_coordinator (Agent)
  * google-day1::blog_pipeline (SequentialAgent)
  * google-day1::parallel_research (SequentialAgent)
  * google-day1::story_pipeline (SequentialAgent)

[planning] pipelines/planning.yml
  External tools: weather_tool, fibonacci_tool, db_search
  * planning::planning_math (ThinkingAgent)
  * planning::planning_weather (ThinkingAgent)
  * planning::planning_full (ThinkingAgent)
  * planning::planning_custom (ThinkingAgent)
  * planning::planning (DispatcherAgent)
```

To run a specific pipeline, use:

```bash
ltm-agent run [pipeline_file_name]::[pipeline_name] "your query here"
```

### Example: complex multi-step reasoning pipeline

This example uses tool calling and iterative planning: it queries an external weather tool for multiple cities, filters them to keep only those with temperature > 10 °C, rounds the selected temperatures, then computes the corresponding Fibonacci values F(t). 

At each step it checks that all user constraints are met (correct number of cities, temp filter, rounding, Fibonacci on rounded temps) before presenting the final, verified result.

```bash
$ ltm-agent run planning_weather "show 2 cities where temp > 10, round temperatures, show fibonacci F
(temp)"
INFO: ================================================================================
INFO: Pipeline: planning_weather
INFO: Config: pipelines/planning.yml
INFO: Query: show 2 cities where temp > 10, round temperatures, show fibonacci F
(temp)
INFO: ================================================================================
INFO: Loading 4 external tool(s)...
INFO: Building agent 'weather_agent' with tools: ['weather_tool']
INFO: Building iterative planning agent 'planning_weather' with 1 executor(s)
INFO:   - Executor: weather_agent
INFO: Starting pipeline execution...
INFO: Starting planning_weather - Max iterations: 5
INFO: Iteration 1/5
INFO: HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent "HTTP/1.1 200 OK"
INFO: HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent "HTTP/1.1 200 OK"
INFO: Calling tool: weather_tool
INFO: HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent "HTTP/1.1 200 OK"
INFO: Calling tool: weather_tool
INFO: HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent "HTTP/1.1 200 OK"
INFO: HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent "HTTP/1.1 200 OK"
INFO: HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent "HTTP/1.1 200 OK"
INFO: SUCCESS Problem solved - FINAL RESULTS detected
INFO: ✓ Iteration 1 completed (3 events)
INFO: SUCCESS planning_weather completed successfully in 1 iterations

ITERATION 2: PROGRESS ANALYSIS & NEXT STEP

1. Restate the original goal with ALL requirements:
   - Show 2 cities where temp > 10.
   - Round their temperatures.
   - Show the Fibonacci number F(temp) for each rounded temperature.

2. Restate the required output format:
   The user did not specify an output format, so I will present the information clearly.

3. Check each requirement one by one:
   - Requirement 1: Find 2 cities with temp > 10.
     - London: 12.1°C (met)
     - Paris: 11.1°C (met)
     - Status: DONE
   - Requirement 2: Round the temperatures.
     - London: 12.1°C rounds to 12°C.
     - Paris: 11.1°C rounds to 11°C.
     - Status: DONE
   - Requirement 3: Calculate Fibonacci for rounded temperatures.
     - F(12): I need to calculate this.
     - F(11): I need to calculate this.
     - Status: NOT DONE (Need to calculate Fibonacci)

4. Calculations:
   - London temperature: 12.1°C. Rounded: 12°C.
   - Paris temperature: 11.1°C. Rounded: 11°C.

   Fibonacci calculation for F(12):
   F(0) = 0
   F(1) = 1
   F(2) = 1
   F(3) = 2
   F(4) = 3
   F(5) = 5
   F(6) = 8
   F(7) = 13
   F(8) = 21
   F(9) = 34
   F(10) = 55
   F(11) = 89
   F(12) = 144

   Fibonacci calculation for F(11):
   F(11) = 89 (already calculated above)

5. What still needs to be done?
   - Present the final output with the cities, rounded temperatures, and Fibonacci numbers.

6. Evaluate Status:
   [Q1] Do I have ALL the DATA needed?
        YES. I have the temperatures for London and Paris, and I have calculated the rounded temperatures and their corresponding Fibonacci numbers.

   [Q2] Can I produce output in EXACT user-requested format?
        The user did not specify an exact format, so I will present the information clearly. I have all the information to do so.
        YES.

   Status: SOLVED

   Do simple formatting/extraction/rounding inline right now.

London: 12.1°C rounds to 12°C. F(12) = 144.
Paris: 11.1°C rounds to 11°C. F(11) = 89.

London has a temperature of 12.1°C which rounds to 12°C. The 12th Fibonacci number is 144.
Paris has a temperature of 11.1°C which rounds to 11°C. The 11th Fibonacci number is 89.

London: 12°C, F(12) = 144
Paris: 11°C, F(11) = 89

INFO: Pipeline execution complete
```

## Extensibility

### Adding new Tools with Agents

To add a new external tool:

1. Write the callable function or class in a Python module.
2. Register the tool in the YAML config:

```yaml
external_tools:
  db_search: "./path/module.py:db_search"
```

Reference tool in agent:

```yaml
agents:
  database_agent:
    instruction: "I can search through database records."
    tools:
      - db_search
```

## Tests

Tests play crucial role in ensuring the reliability and correctness of the little thinking model. A little change in a prompt or agent configuration may lead to significant differences in behavior. To catch such issues early, a thorough test suite is implemented.

To run tests, use:

```bash
uv run pytest tests/ -s -v
```

Following test cases are implemented:

- `show temperature in London in one line as WEATHER:<TEMP>`
- `calculate the 10th fibonacci number and show result as FIB:<NUMBER>`
- `compare temperatures in London and Paris, show which is colder as COLDER:<CITY>`
- `calculate the sum of all numbers from 1 to 100 using code execution and show result as SUM:<NUMBER>` (this test is known to fail often)

To ensure consistent results across test runs, mocked outputs for external tools are used.

Each test is configured to run several times (right now - 3 times) to catch intermittent failures due to model variability.

### Some complex queries examples

Little thinking model is capable of solving some more complex multi-step reasoning tasks. Here are some example queries that can be used to test its capabilities:

- show 2 cities where temperature equals current time hours
- show temperature and time and some news title for 3 european cities where temperature > 5, output as markdown table
- calculate factorial of 10

To provide answers to such complex queries, a full pipeline was used that combines multiple tools and agents:

```bash
$ ltm-agent run planning_full "how temperature and time and some news title for 3 european cities where temperature > 5, output as markdown table"
...
I have found a news title for Madrid. Now I will compile all the information and present it as a Markdown table.

Cities: Paris, Berlin, Madrid
Temperatures: Paris (9.3°C), Berlin (5.9°C), Madrid (6.2°C)
Times: Paris (2025-11-28 22:35:03), Berlin (2025-11-28 22:35:06), Madrid (2025-11-28 22:35:08)
News Titles:
Paris: "Arrests made in connection with Louvre heist, fourth suspect apprehended."
Berlin: "Third shooting at a Berlin driving school reported."
Madrid: "Real Madrid fans divided over plans to allow external investment in the club."

Here is the Markdown table:

| City   | Temperature | Time                | News Title                                                                    |
| :----- | :---------- | :------------------ | :---------------------------------------------------------------------------- |
| Paris  | 9.3°C       | 2025-11-28 22:35:03 | Arrests made in connection with Louvre heist, fourth suspect apprehended.     |
| Berlin | 5.9°C       | 2025-11-28 22:35:06 | Third shooting at a Berlin driving school reported.                           |
| Madrid | 6.2°C       | 2025-11-28 22:35:08 | Real Madrid fans divided over plans to allow external investment in the club. |
```

## Resources

- Kaggle - [5-Day AI Agents Intensive Course with Google (Nov 10 - 14, 2025)](https://www.kaggle.com/learn-guide/5-day-agents)
- Kaggle - [Agents Intensive - Capstone Project](https://www.kaggle.com/competitions/agents-intensive-capstone-project/overview)

### Google AI Agent Development

- [Google Agent Development Kit (ADK) Documentation](https://google.github.io/adk-docs/) - Official ADK documentation
- [ADK Agent Architectures](https://google.github.io/adk-docs/agents/)
- [Loop Agents for Iterative Refinement](https://google.github.io/adk-docs/agents/workflow-agents/loop-agents/)
- [Sequential Agents](https://google.github.io/adk-docs/agents/workflow-agents/sequential-agents/)
- [Parallel Agents](https://google.github.io/adk-docs/agents/workflow-agents/parallel-agents/)
- [Agent Evaluation Best Practices](https://google.github.io/adk-docs/evaluate/)
- [Trajectory-Based Agent Testing](https://google.github.io/adk-docs/evaluate/criteria/)
- [Tool Context and Function Tools](https://google.github.io/adk-docs/tools/function-tools/)
- [MCP Tools Documentation](https://google.github.io/adk-docs/tools/mcp-tools/)

### Gemini Enterprise Agent Ready (GEAR)

- [GEAR Educational Sprint](https://developers.google.com/profile/badges/events/community/gear/gear-interest) - Gemini Enterprise Agent Ready program launching in 2026

### Related Research

- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/) - Standardized tool integration protocol


## Authors

  - Fedor Vompe