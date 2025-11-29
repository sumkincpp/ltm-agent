import asyncio
import logging

from google.adk.runners import InMemoryRunner

from ltm_agent.agents import build_from_config
from ltm_agent.config import resolve_pipeline
from ltm_agent.output_formatter import PipelineOutputFormatter

logger = logging.getLogger(__name__)

PIPELINES_MAX_RETRIES = 3


async def run_pipeline(config_path: str, pipeline_name: str, query: str, tool_registry, debug: bool = False, verbose: bool = False):
    """Load and run a pipeline.

    Args:
        config_path: Path to config file or directory
        pipeline_name: Name of pipeline to run
        query: Query to execute
        tool_registry: Tool registry to use
        debug: Enable debug mode
        verbose: Enable verbose output

    Returns:
        List of events from pipeline execution
    """

    config, pipeline_name = resolve_pipeline(config_path, pipeline_name)

    logger.info("=" * 80)
    logger.info(f"Pipeline: {pipeline_name}")
    logger.info(f"Config: {config.filepath}")
    logger.info(f"Query: {query}")
    logger.info("=" * 80)

    agent = build_from_config(config, pipeline_name, tool_registry)
    runner = InMemoryRunner(agent=agent, app_name="agents")

    logger.info("Starting pipeline execution...")

    events = None
    for attempt in range(PIPELINES_MAX_RETRIES):
        try:
            events = await runner.run_debug(query, quiet=(not verbose and not debug), verbose=verbose)
            break
        except Exception as e:
            logger.error(f"Pipeline execution failed (attempt {attempt + 1}/{PIPELINES_MAX_RETRIES}): {e}", exc_info=debug)
            if attempt < PIPELINES_MAX_RETRIES - 1:
                await asyncio.sleep(2)

    if events is None:
        logger.error(f"Pipeline failed after {PIPELINES_MAX_RETRIES} attempts")
        return []

    if not verbose and events:
        result = PipelineOutputFormatter.extract_result_text(events)
        PipelineOutputFormatter.display_result(result, verbose=verbose)

    logger.info("Pipeline execution complete")

    return events
