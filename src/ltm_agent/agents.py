import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union

from google.adk.agents import Agent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.agents.base_agent import BaseAgentState
from google.adk.agents.invocation_context import InvocationContext
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.events.event import Event
from google.adk.models.google_llm import Gemini
from google.adk.tools import AgentTool
from google.genai import types
from pydantic import Field

from ltm_agent.config import PipelineConfig

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
DEFAULT_MAX_ITERATIONS = 5
DEFAULT_MAX_TOOLS_PER_STEP = 5


class PlanningAgentState(BaseAgentState):
    """State tracking for iterative planning agent."""

    current_step: int = Field(default=0, description="Current step being executed (0-indexed)")
    total_steps: int = Field(default=0, description="Total number of planned steps")
    completed_steps: List[str] = Field(default_factory=list, description="List of completed step descriptions")
    step_results: Dict[int, Any] = Field(default_factory=dict, description="Results from each completed step")
    step_verifications: Dict[int, Dict[str, Any]] = Field(default_factory=dict, description="Verification status for each step")
    iterations_count: int = Field(default=0, description="Number of iterations executed")
    problem_solved: bool = Field(default=False, description="Whether the problem has been solved")
    cannot_solve: bool = Field(default=False, description="Whether we've determined the problem cannot be solved")
    failure_reason: Optional[str] = Field(default=None, description="Reason if problem cannot be solved")


class ThinkingAgent(Agent):
    """
    Enhanced Planning agent that:
    1. Creates a structured plan with verification steps
    2. Executes plan iteratively, one step at a time
    3. Verifies each step before proceeding
    4. Tracks progress and results across iterations
    5. Loops until problem is solved or determined unsolvable
    6. Can refine plan based on intermediate results

    Similar to LoopAgent but runs a single planning agent in iterations
    rather than cycling through sub-agents.
    """

    max_iterations: Optional[int] = None
    max_tools_per_step: int = DEFAULT_MAX_TOOLS_PER_STEP

    def __init__(
        self,
        name: str,
        model: Gemini,
        executor_agents: List[Agent],
        instruction: Optional[str] = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        max_tools_per_step: int = DEFAULT_MAX_TOOLS_PER_STEP,
        **kwargs,
    ):
        if instruction is None:
            instruction = self._build_instruction_static(executor_agents, max_iterations, max_tools_per_step)

        tools = [AgentTool(agent) for agent in executor_agents]

        super().__init__(name=name, model=model, instruction=instruction, tools=tools, **kwargs)

        self.max_iterations = max_iterations
        self.max_tools_per_step = max_tools_per_step

    @staticmethod
    def _load_instruction_template() -> str:
        """Load instruction template from external file."""
        template_path = Path(__file__).parent / "prompts" / "thinking_agent.txt"
        return template_path.read_text()

    @staticmethod
    def _build_instruction_static(executor_agents: List[Agent], max_iterations: int, max_tools_per_step: int) -> str:
        """Build iterative planning instruction with loop-based execution."""

        executor_descriptions = []
        for agent in executor_agents:
            agent_name = agent.name
            agent_instruction = getattr(agent, "instruction", "No description")

            tool_names = []
            if hasattr(agent, "tools") and agent.tools:
                tool_names = [tool.name if hasattr(tool, "name") else str(tool) for tool in agent.tools]

            desc = f"- **{agent_name}**: {agent_instruction}"
            if tool_names:
                desc += f"\n  Tools: {', '.join(tool_names)}"

            executor_descriptions.append(desc)

        template = ThinkingAgent._load_instruction_template()

        instruction = template.format(
            executor_descriptions="\n".join(executor_descriptions), max_iterations=max_iterations, max_tools_per_step=max_tools_per_step
        )

        return instruction

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Execute the iterative planning loop.

        Follows the LoopAgent pattern but loops a single agent's execution
        rather than cycling through sub-agents.
        """

        agent_state = self._load_agent_state(ctx, PlanningAgentState)
        is_resuming = agent_state is not None

        iterations_count = agent_state.iterations_count if agent_state else 0
        problem_solved = agent_state.problem_solved if agent_state else False
        cannot_solve = agent_state.cannot_solve if agent_state else False

        should_exit = problem_solved or cannot_solve
        pause_invocation = False

        if iterations_count == 0:
            logger.info(f"Starting {self.name} - Max iterations: {self.max_iterations}")
        else:
            logger.info(f"Resuming {self.name} at iteration {iterations_count}")

        while (not self.max_iterations or iterations_count < self.max_iterations) and not (should_exit or pause_invocation):
            logger.info(f"Iteration {iterations_count + 1}/{self.max_iterations}")

            if ctx.is_resumable and not is_resuming:
                current_step = agent_state.current_step if agent_state else 0
                total_steps = agent_state.total_steps if agent_state else 0
                completed_steps = agent_state.completed_steps if agent_state else []
                step_results = agent_state.step_results if agent_state else {}
                step_verifications = agent_state.step_verifications if agent_state else {}

                agent_state = PlanningAgentState(
                    iterations_count=iterations_count,
                    current_step=current_step,
                    total_steps=total_steps,
                    completed_steps=completed_steps,
                    step_results=step_results,
                    step_verifications=step_verifications,
                    problem_solved=problem_solved,
                    cannot_solve=cannot_solve,
                )
                ctx.set_agent_state(self.name, agent_state=agent_state)
                yield self._create_agent_state_event(ctx)

                if agent_state.total_steps > 0:
                    completed = len(agent_state.completed_steps)
                    logger.info(f"Progress: {completed}/{agent_state.total_steps} steps completed")

            is_resuming = False

            event_count = 0
            async for event in super()._run_async_impl(ctx):
                event_count += 1

                if hasattr(event, "content") and event.content:
                    content_preview = str(event.content)[:200]
                    if len(str(event.content)) > 200:
                        content_preview += "..."
                    logger.debug(f"Event {event_count}: {content_preview}")

                if hasattr(event, "tool_calls") and event.tool_calls:
                    for tool_call in event.tool_calls:
                        tool_name = getattr(tool_call, "name", "unknown")
                        logger.info(f"Tool called: {tool_name}")

                yield event

                if event.actions.escalate:
                    should_exit = True
                    problem_solved = True
                    logger.info("Problem solved - escalation signal received")

                if ctx.should_pause_invocation(event):
                    pause_invocation = True
                    logger.info("Invocation paused")

                if hasattr(event, "content") and event.content:
                    content_str = str(event.content)
                    content_lower = content_str.lower()

                    if "final results" in content_lower and "status: solved" in content_lower:
                        should_exit = True
                        problem_solved = True
                        logger.info("SUCCESS Problem solved - FINAL RESULTS detected")
                    elif "final results" in content_lower and "status: unsolvable" in content_lower:
                        should_exit = True
                        cannot_solve = True
                        logger.warning("FAIL Problem cannot be solved - detected in content")

            iterations_count += 1

            logger.info(f"✓ Iteration {iterations_count} completed ({event_count} events)")

            if should_exit or pause_invocation:
                break

        if iterations_count >= self.max_iterations and not problem_solved:
            cannot_solve = True
            logger.warning(f"[!] Max iterations ({self.max_iterations}) reached without solving problem")

            if ctx.is_resumable:
                agent_state = PlanningAgentState(
                    iterations_count=iterations_count, problem_solved=False, cannot_solve=True, failure_reason=f"Max iterations ({self.max_iterations}) reached"
                )
                ctx.set_agent_state(self.name, agent_state=agent_state)
                yield self._create_agent_state_event(ctx)

        if pause_invocation:
            logger.info("Execution paused - waiting for resume")
            return

        if problem_solved:
            logger.info(f"SUCCESS {self.name} completed successfully in {iterations_count} iterations")
        elif cannot_solve:
            logger.error(f"FAIL {self.name} could not solve problem after {iterations_count} iterations")

        if ctx.is_resumable:
            ctx.set_agent_state(self.name, end_of_agent=True)
            yield self._create_agent_state_event(ctx)


def build_retry_options(cfg: Dict) -> types.HttpRetryOptions:
    """Build retry options from config.

    Args:
        cfg: Configuration dictionary with retry settings

    Returns:
        HttpRetryOptions object
    """
    return types.HttpRetryOptions(
        attempts=cfg.get("attempts", 5),
        exp_base=cfg.get("exp_base", 7),
        initial_delay=cfg.get("initial_delay", 1),
        http_status_codes=cfg.get("http_status_codes", [429, 500, 503, 504]),
    )


def build_model(cfg: Dict, config: PipelineConfig) -> Gemini:
    """Build model with defaults from config.

    Args:
        cfg: Agent-specific configuration
        config: Global pipeline configuration

    Returns:
        Gemini model instance
    """
    model_cfg = {
        **config.defaults.get("model", {}),
        **cfg.get("model", {}),
    }
    retry = build_retry_options(model_cfg.get("retry_options", {}))

    return Gemini(model=model_cfg.get("name", DEFAULT_GEMINI_MODEL), retry_options=retry)


def build_agent(name: str, cfg: Dict, config: PipelineConfig, agent_registry: Dict, tool_registry, get_or_build_agent: Optional[Callable] = None) -> Agent:
    """Build a basic Agent.

    Args:
        name: Agent name
        cfg: Agent configuration
        config: Pipeline configuration
        agent_registry: Registry of already-built agents
        tool_registry: Tool registry for looking up tools
        get_or_build_agent: Callback for lazy agent building

    Returns:
        Built Agent instance
    """
    tools = []
    for tool_name in cfg.get("tools", []):
        if tool_name in agent_registry:
            tools.append(AgentTool(agent_registry[tool_name]))
        elif get_or_build_agent and tool_name not in tool_registry:
            tools.append(AgentTool(get_or_build_agent(tool_name)))
        elif tool_name in tool_registry:
            tools.append(tool_registry[tool_name])
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    logger.info(f"Building agent '{name}' with tools: {[t.name if hasattr(t, 'name') else str(t) for t in tools]}")

    kwargs = {
        "name": name,
        "model": build_model(cfg, config),
        "instruction": cfg["instruction"],
    }

    if tools:
        kwargs["tools"] = tools

    if cfg.get("output_key"):
        kwargs["output_key"] = cfg["output_key"]

    if cfg.get("code_executor"):
        if cfg["code_executor"] == "BuiltInCodeExecutor":
            kwargs["code_executor"] = BuiltInCodeExecutor()
            logger.info(f"Agent '{name}' configured with BuiltInCodeExecutor")

    return Agent(**kwargs)


def build_pipeline(
    name: str,
    cfg: Dict,
    config: PipelineConfig,
    agent_registry: Dict,
    tool_registry,
    get_or_build_agent: Optional[Callable] = None,
) -> Union[Agent, SequentialAgent, ParallelAgent, LoopAgent, ThinkingAgent]:
    """Build any agent/pipeline type.

    Args:
        name: Pipeline name
        cfg: Pipeline configuration
        config: Pipeline configuration
        agent_registry: Registry of already-built agents
        tool_registry: Tool registry for looking up tools
        get_or_build_agent: Callback for lazy agent building

    Returns:
        Built agent/pipeline instance
    """
    agent_class = cfg.get("class", "Agent")

    if agent_class == "Agent":
        return build_agent(name, cfg, config, agent_registry, tool_registry, get_or_build_agent)

    if agent_class in ["PlanningAgent", "ThinkingAgent"]:
        executor_agents = []
        for item in cfg.get("executor_agents", []):
            if isinstance(item, str):
                if get_or_build_agent:
                    executor_agents.append(get_or_build_agent(item))
                elif item in agent_registry:
                    executor_agents.append(agent_registry[item])
                else:
                    raise ValueError(f"Agent not found: {item}")
            elif isinstance(item, dict):
                sub_name = item.get("name", f"{name}_executor_{len(executor_agents)}")
                executor_agents.append(build_pipeline(sub_name, item, config, agent_registry, tool_registry, get_or_build_agent))
            else:
                raise ValueError(f"Invalid executor agent definition: {item}")

        if not executor_agents:
            raise ValueError(f"PlanningAgent '{name}' requires at least one executor agent")

        logger.info(f"Building iterative planning agent '{name}' with {len(executor_agents)} executor(s)")
        for exec_agent in executor_agents:
            logger.info(f"  - Executor: {exec_agent.name}")

        kwargs = {
            "name": name,
            "model": build_model(cfg, config),
            "executor_agents": executor_agents,
        }

        if cfg.get("instruction"):
            kwargs["instruction"] = cfg["instruction"]

        if cfg.get("max_iterations") is not None:
            kwargs["max_iterations"] = cfg["max_iterations"]

        if cfg.get("max_tools_per_step") is not None:
            kwargs["max_tools_per_step"] = cfg["max_tools_per_step"]

        return ThinkingAgent(**kwargs)

    sub_agents = []
    for item in cfg.get("agents", []):
        if isinstance(item, str):
            if get_or_build_agent:
                sub_agents.append(get_or_build_agent(item))
            elif item in agent_registry:
                sub_agents.append(agent_registry[item])
            else:
                raise ValueError(f"Agent not found: {item}")
        elif isinstance(item, dict):
            sub_name = item.get("name", f"{name}_sub_{len(sub_agents)}")
            sub_agents.append(build_pipeline(sub_name, item, config, agent_registry, tool_registry, get_or_build_agent))
        else:
            raise ValueError(f"Invalid agent definition: {item}")

    if agent_class == "SequentialAgent":
        return SequentialAgent(name=name, sub_agents=sub_agents)
    elif agent_class == "ParallelAgent":
        return ParallelAgent(name=name, sub_agents=sub_agents)
    elif agent_class == "LoopAgent":
        return LoopAgent(name=name, sub_agents=sub_agents, max_iterations=cfg.get("max_iterations", DEFAULT_MAX_ITERATIONS))
    else:
        raise ValueError(f"Unknown class: {agent_class}")


def build_from_config(config: PipelineConfig, pipeline_name: str, tool_registry):
    """Build pipeline from loaded config.

    Args:
        config: Loaded pipeline configuration
        pipeline_name: Name of pipeline to build
        tool_registry: Tool registry to use

    Returns:
        Built pipeline/agent
    """
    tool_registry.load_defaults()

    if config.external_tools:
        logger.info(f"Loading {len(config.external_tools)} external tool(s)...")
        tool_registry.load_external_tools(config.external_tools)

    if pipeline_name not in config.pipelines:
        raise ValueError(f"Pipeline '{pipeline_name}' not found. Available: {list(config.pipelines.keys())}")

    agent_registry = {}

    def get_or_build_agent(name: str) -> Agent:
        if name not in agent_registry:
            if name not in config.agents:
                raise ValueError(f"Agent '{name}' not found in config")
            logger.debug(f"Lazy-building agent: {name}")
            agent_registry[name] = build_agent(name, config.agents[name], config, agent_registry, tool_registry, get_or_build_agent)
        return agent_registry[name]

    return build_pipeline(pipeline_name, config.pipelines[pipeline_name], config, agent_registry, tool_registry, get_or_build_agent)
