"""
YAML pipeline parser and validator.
Converts YAML definitions into Pipeline objects.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    LLMConfig,
    LLMProvider,
    Pipeline,
    Step,
    StepType,
)


class PipelineParseError(Exception):
    """Raised when pipeline YAML parsing fails."""
    pass


class PipelineValidationError(Exception):
    """Raised when pipeline validation fails."""
    pass


def _parse_llm_config(data: Dict[str, Any]) -> LLMConfig:
    """Parse LLM configuration from YAML data."""
    provider_str = data.get("provider", "openai")
    try:
        provider = LLMProvider(provider_str.lower())
    except ValueError:
        provider = LLMProvider.CUSTOM

    return LLMConfig(
        provider=provider,
        model=data.get("model", "gpt-4o-mini"),
        api_key=data.get("api_key"),
        api_base=data.get("api_base"),
        temperature=data.get("temperature", 0.7),
        max_tokens=data.get("max_tokens", 4096),
        timeout=data.get("timeout", 60),
        extra=data.get("extra", {}),
    )


def _parse_step(data: Dict[str, Any]) -> Step:
    """Parse a single step from YAML data."""
    step_type_str = data.get("type", "llm_call")
    try:
        step_type = StepType(step_type_str.lower())
    except ValueError:
        raise PipelineParseError(
            f"Unknown step type: '{step_type_str}'. "
            f"Valid types: {[t.value for t in StepType]}"
        )

    return Step(
        name=data.get("name", "unnamed"),
        step_type=step_type,
        description=data.get("description", ""),
        depends_on=data.get("depends_on", []),
        config=data.get("config", {}),
        inputs=data.get("inputs", {}),
        retry_count=data.get("retry_count", 0),
        retry_delay=data.get("retry_delay", 1.0),
        timeout=data.get("timeout", 120.0),
        condition=data.get("condition"),
    )


def parse_pipeline_yaml(yaml_content: str) -> Pipeline:
    """
    Parse a YAML string into a Pipeline object.

    Args:
        yaml_content: YAML string defining the pipeline.

    Returns:
        Pipeline object.

    Raises:
        PipelineParseError: If YAML parsing fails.
    """
    try:
        import yaml
    except ImportError:
        raise PipelineParseError(
            "PyYAML is required to parse pipeline files. "
            "Install it with: pip install pyyaml"
        )

    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise PipelineParseError(f"YAML parsing error: {e}")

    if not isinstance(data, dict):
        raise PipelineParseError("Pipeline YAML root must be a mapping.")

    if "name" not in data:
        raise PipelineParseError("Pipeline must have a 'name' field.")

    # Parse LLM config
    llm_data = data.get("llm", {})
    llm_config = _parse_llm_config(llm_data) if llm_data else LLMConfig()

    # Parse steps
    steps: List[Step] = []
    raw_steps = data.get("steps", [])
    if not isinstance(raw_steps, list):
        raise PipelineParseError("'steps' must be a list of step definitions.")

    for i, step_data in enumerate(raw_steps):
        if not isinstance(step_data, dict):
            raise PipelineParseError(f"Step {i} must be a mapping.")
        if "name" not in step_data:
            raise PipelineParseError(f"Step {i} must have a 'name' field.")
        steps.append(_parse_step(step_data))

    return Pipeline(
        name=data["name"],
        description=data.get("description", ""),
        version=data.get("version", "1.0.0"),
        steps=steps,
        env=data.get("env", {}),
        variables=data.get("variables", {}),
        llm_config=llm_config,
        max_parallel=data.get("max_parallel", 3),
    )


def parse_pipeline_file(file_path: str | Path) -> Pipeline:
    """
    Parse a pipeline YAML file.

    Args:
        file_path: Path to the YAML file.

    Returns:
        Pipeline object.
    """
    path = Path(file_path)
    if not path.exists():
        raise PipelineParseError(f"Pipeline file not found: {file_path}")
    if path.suffix not in (".yaml", ".yml"):
        raise PipelineParseError(
            f"Pipeline file must be .yaml or .yml, got: {path.suffix}"
        )

    content = path.read_text(encoding="utf-8")
    return parse_pipeline_yaml(content)


def validate_pipeline(pipeline: Pipeline) -> List[str]:
    """
    Validate a pipeline definition.

    Args:
        pipeline: Pipeline object to validate.

    Returns:
        List of validation error messages (empty if valid).

    Raises:
        PipelineValidationError: If critical validation fails.
    """
    errors: List[str] = []

    if not pipeline.name:
        errors.append("Pipeline name is required.")

    if not pipeline.steps:
        errors.append("Pipeline must have at least one step.")

    step_names = set()
    for step in pipeline.steps:
        # Check duplicate names
        if step.name in step_names:
            errors.append(f"Duplicate step name: '{step.name}'")
        step_names.add(step.name)

        # Check dependency references
        for dep in step.depends_on:
            if dep not in step_names and dep != step.name:
                # Will check after all names are collected
                pass

        # Validate step type specific config
        if step.step_type == StepType.LLM_CALL:
            if not step.config.get("prompt") and not step.config.get("system"):
                errors.append(
                    f"Step '{step.name}' (llm_call) must have 'prompt' or 'system' in config."
                )

        elif step.step_type == StepType.HTTP_REQUEST:
            if not step.config.get("url"):
                errors.append(
                    f"Step '{step.name}' (http_request) must have 'url' in config."
                )

        elif step.step_type == StepType.SHELL_COMMAND:
            if not step.config.get("command"):
                errors.append(
                    f"Step '{step.name}' (shell_command) must have 'command' in config."
                )

    # Check all dependency references exist
    for step in pipeline.steps:
        for dep in step.depends_on:
            if dep not in step_names:
                errors.append(
                    f"Step '{step.name}' depends on unknown step: '{dep}'"
                )

    # Check for circular dependencies
    if _has_circular_dependency(pipeline.steps):
        errors.append("Pipeline contains circular dependencies.")

    return errors


def _has_circular_dependency(steps: List[Step]) -> bool:
    """Detect circular dependencies using DFS."""
    graph: Dict[str, List[str]] = {}
    for step in steps:
        graph[step.name] = step.depends_on

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {name: WHITE for name in graph}

    def dfs(node: str) -> bool:
        color[node] = GRAY
        for neighbor in graph.get(node, []):
            if color.get(neighbor) == GRAY:
                return True
            if color.get(neighbor) == WHITE and dfs(neighbor):
                return True
        color[node] = BLACK
        return False

    for name in graph:
        if color[name] == WHITE:
            if dfs(name):
                return True
    return False


def resolve_variables(text: str, variables: Dict[str, Any]) -> str:
    """
    Resolve {{variable}} placeholders in text.

    Args:
        text: Text with {{variable}} placeholders.
        variables: Dictionary of variable values.

    Returns:
        Text with placeholders replaced.
    """
    def replacer(match: re.Match) -> str:
        var_name = match.group(1).strip()
        value = variables.get(var_name, match.group(0))
        return str(value) if value is not None else match.group(0)

    return re.sub(r"\{\{(.+?)\}\}", replacer, text)
