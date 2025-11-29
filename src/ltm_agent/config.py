from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import yaml


@dataclass
class PipelineConfig:
    """Container for pipeline configuration."""

    defaults: Dict = field(default_factory=dict)
    agents: Dict = field(default_factory=dict)
    pipelines: Dict = field(default_factory=dict)
    external_tools: Dict = field(default_factory=dict)
    filepath: Optional[Path] = None


def load_config(path: Path) -> PipelineConfig:
    """Load YAML configuration file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    return PipelineConfig(
        defaults=data.get("defaults", {}),
        agents=data.get("agents", {}),
        pipelines=data.get("pipelines", {}),
        external_tools=data.get("external_tools", {}),
        filepath=path,
    )


def discover_configs(config_path: str) -> Dict[str, Path]:
    """Discover all YAML config files."""
    path = Path(config_path)
    configs = {}

    if path.is_file():
        configs[path.stem] = path
    elif path.is_dir():
        for yaml_file in sorted(path.glob("*.yaml")) + sorted(path.glob("*.yml")):
            configs[yaml_file.stem] = yaml_file
    else:
        raise ValueError(f"Config path not found: {config_path}")

    return configs


def load_all_configs(config_path: str) -> Dict[str, PipelineConfig]:
    """Load all configurations from config path."""
    configs = discover_configs(config_path)
    all_configs = {}

    for filename, filepath in configs.items():
        all_configs[filename] = load_config(filepath)

    return all_configs


def resolve_pipeline(config_path: str, pipeline_ref: str) -> tuple[PipelineConfig, str]:
    """Resolve pipeline reference to (PipelineConfig, pipeline_name).

    Args:
        config_path: Path to config file or directory
        pipeline_ref: Pipeline reference in format "file::name" or just "name"

    Returns:
        Tuple of (PipelineConfig, pipeline_name)

    Raises:
        ValueError: If pipeline not found or ambiguous
    """
    if "::" in pipeline_ref:
        filename, pipeline_name = pipeline_ref.split("::", 1)
        configs = discover_configs(config_path)
        if filename not in configs:
            raise ValueError(f"Config file '{filename}' not found. Available: {list(configs.keys())}")
        config = load_config(configs[filename])
        if pipeline_name not in config.pipelines:
            raise ValueError(f"Pipeline '{pipeline_name}' not found in {filename}")
        return config, pipeline_name
    else:
        all_configs = load_all_configs(config_path)
        matches = []

        for filename, config in all_configs.items():
            if pipeline_ref in config.pipelines:
                matches.append((filename, config))

        if len(matches) == 0:
            raise ValueError(f"Pipeline '{pipeline_ref}' not found in any config file")
        elif len(matches) > 1:
            filenames = [f for f, _ in matches]
            raise ValueError(f"Ambiguous pipeline name '{pipeline_ref}'. Use file::name format. Found in: {filenames}")

        return matches[0][1], pipeline_ref
