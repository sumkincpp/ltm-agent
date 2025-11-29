#!/usr/bin/env python3
import argparse
import asyncio
import logging

from dotenv import load_dotenv

from ltm_agent.config import load_all_configs
from ltm_agent.pipeline import run_pipeline
from ltm_agent.tools import ToolRegistry

logger = logging.getLogger(__name__)
load_dotenv()


async def cmd_list(args):
    """List all available pipelines."""
    all_configs = load_all_configs(args.config)

    print("\nAvailable pipelines:\n")
    for filename, config in all_configs.items():
        if config.pipelines:
            print(f"[{filename}] {config.filepath}")
            if config.external_tools:
                print(f"  External tools: {', '.join(config.external_tools.keys())}")
            for name, cfg in config.pipelines.items():
                agent_class = cfg.get("class", "Agent")
                print(f"  * {filename}::{name} ({agent_class})")
            print()


async def async_main():
    parser = argparse.ArgumentParser(description="Run YAML-configured multi-agent pipelines")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--config", default="pipelines", help="Path to config file or directory")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    run_parser = subparsers.add_parser("run", help="Run a pipeline")
    run_parser.add_argument("pipeline", help="Pipeline name to run")
    run_parser.add_argument("query", help="Query to execute")
    run_parser.add_argument("--debug", action="store_true", help="Enable debug mode (shows raw agent output)")
    run_parser.add_argument("--verbose", action="store_true", help="Show detailed event content including all internal thinking")

    subparsers.add_parser("list", help="List available pipelines")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
        logging.getLogger("google_adk.google.adk.models.google_llm").setLevel(logging.WARNING)
        logging.getLogger("google_genai.types").setLevel(logging.ERROR)
        logging.getLogger("google_adk.google.adk.runners").setLevel(logging.WARNING)
        logging.getLogger("google_adk.google.adk.agents.agent").setLevel(logging.WARNING)
        logging.getLogger("ltm_agent.output_formatter").setLevel(logging.WARNING)

    tool_registry = ToolRegistry()

    if args.command == "list":
        await cmd_list(args)
    elif args.command == "run":
        await run_pipeline(args.config, args.pipeline, args.query, tool_registry, debug=args.debug, verbose=args.verbose)
    else:
        parser.error("pipeline and query required (use list command to see available pipelines)")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
