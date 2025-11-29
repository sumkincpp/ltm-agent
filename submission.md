# Little Thinking Model (LTM)

**Little Thinking Model (LTM)** is an agentic system built on Google's ADK that implements iterative multi-step reasoning with verification of user constraints.

It combines:

- **The Model** (Brain): Gemini models for reasoning and decision-making
- **Tools** (Hands): External function calling capabilities for real-world actions
- **Orchestration Layer** (Nervous System): Agent classes and YAML-configured agent pipelines managing the "Think, Act, Observe" loop

The agent system enables the creation of complex agent pipelines using simple YAML configuration files,
allowing for easy integration of external tools via function calling and multi-step reasoning with context engineering.

## Problem Statement and Motivation

Complex tasks we provide to Large Language Models often require multiple steps of reasoning with complex logical reasoning (filtering, aggregation, ..), tool calling, and verification of user constraints. In these scenarios, simple LLM-based agents frequently struggle to provide complete and correct answers due to their limited attention capabilities.

While LLMs excel at generating human-like text, they face challenges with deep reasoning tasks that require maintaining context across multiple steps and ensuring all user requirements are satisfied.

For example, lets's consider following query:

```bash
"show 2 cities where temp > 10, round temperatures, show fibonacci F(temp)"
```

A simple agent may get confused how many cities should be shown or queried. Some agents may also forget to filter temperatures or calculate Fibonacci values on rounded temperatures. Others will provide partial answers without verifying that all user constraints are met.

## Concepts - The Thinking Agent Pattern

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

## Results

Experiments with the lightweight gemini-2.5-flash-lite model show that agents using iterative steps and verification loops often outperform much larger LLMs that try to handle a problem in a single pass.

This matches Google’s observation that domain-specific agents tend to surpass single, monolithic agents on complex tasks:

> "Single agents that try to do research, writing, editing, and fact-checking all at once become problematic. The instruction prompt gets long and confusing, making them hard to debug and often producing unreliable results." — Google ADK Documentation

It is well known that large LLMs with billions of parameters (32B, 400B) require substantial computational resources, yet they do not automatically produce better results on tasks that involve several reasoning steps. Without structure and guidance, their performance tends to stall as task complexity increases.

To conclude, large LLMs are capable of sophisticated, domain-specific reasoning, but that capability does not necessarily translate into better performance on multi-step reasoning tasks without proper guidance. Domain-specific knowledge is often handled more effectively by agentic systems, since they allow external tools to be integrated via function calling and give precise control over the reasoning process through the orchestration layer.

## Iterative Problem-Solving Process

Current system prompt used is available at [src/ltm_agent/prompts/thinking_agent.txt](src/ltm_agent/prompts/thinking_agent.txt)

![Iterative Problem-Solving Flow](https://raw.githubusercontent.com/sumkincpp/ltm-agent/refs/heads/main/docs/iterative-process.svg) 

## Architecture

This project implements a modular architecture for building agentic systems using Google's ADK framework.

![Architecture Diagram](https://raw.githubusercontent.com/sumkincpp/ltm-agent/refs/heads/main/docs/ltm-agent-architecture.svg)

## Demo

Little thinking model is capable of solving some  complex multi-step reasoning tasks. Here are some example queries that can be used to test its capabilities:

- show 2 cities where temperature equals current time hours
- show temperature and time and some news title for 3 european cities where temperature > 5, output as markdown table
- calculate factorial of 10

## Components

- **YAML Configuration**: Defines defaults, agents, pipelines, and tools
- **Pipeline Builder**: Builds agents from YAML config (Supports dynamic module loading, sync/async tools, automatic logging wrappers)
- **Agent Registry**: Lazy instantiation of discovered agents for pipelines
- **Agent Types** (Google ADK): Agent, SequentialAgent, ParallelAgent, LoopAgent, CodeExecutorAgent, ThinkingAgent (novel),
- **Tool System**: Tool registry, Tool Proxy, external Tool Loader
- **External Tools**: external pluggable tools via YAML config (eg. weather_tool, fibonacci_tool, db_search, current_time, google_search)
- **InMemoryRunner**: Google ADK backend for session management and event streaming

## Demonstration of Course Concepts

This project demonstrates key course concepts, including:

- Multi-agent setups (LLM agents, parallel/sequential flow, loop agents)
- Tool use (custom tools, built-in tools, long-running tasks)
- State handling (sessions and memory)
- Extra concepts (context engineering, logging/tracing/metrics, agent self-evaluation)