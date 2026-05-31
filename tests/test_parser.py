"""
Tests for TaskPilot-CLI YAML parser.
"""

import unittest
import tempfile
from pathlib import Path

from taskpilot.core.parser import (
    parse_pipeline_yaml,
    parse_pipeline_file,
    validate_pipeline,
    resolve_variables,
    PipelineParseError,
)


VALID_YAML = """
name: test-pipeline
description: A test pipeline
version: "1.0.0"
max_parallel: 2

llm:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.5

variables:
  api_url: "https://example.com"

steps:
  - name: step-one
    type: shell_command
    description: First step
    config:
      command: "echo hello"

  - name: step-two
    type: llm_call
    depends_on:
      - step-one
    config:
      prompt: "Analyze this: {{step-one}}"

  - name: step-three
    type: http_request
    depends_on:
      - step-one
    config:
      url: "{{api_url}}/data"
      method: GET
"""


class TestParser(unittest.TestCase):
    """Test YAML pipeline parser."""

    def test_parse_valid_yaml(self):
        pipeline = parse_pipeline_yaml(VALID_YAML)
        self.assertEqual(pipeline.name, "test-pipeline")
        self.assertEqual(pipeline.description, "A test pipeline")
        self.assertEqual(pipeline.version, "1.0.0")
        self.assertEqual(len(pipeline.steps), 3)
        self.assertEqual(pipeline.max_parallel, 2)

    def test_parse_llm_config(self):
        pipeline = parse_pipeline_yaml(VALID_YAML)
        self.assertEqual(pipeline.llm_config.provider.value, "openai")
        self.assertEqual(pipeline.llm_config.model, "gpt-4o-mini")
        self.assertAlmostEqual(pipeline.llm_config.temperature, 0.5)

    def test_parse_variables(self):
        pipeline = parse_pipeline_yaml(VALID_YAML)
        self.assertEqual(pipeline.variables["api_url"], "https://example.com")

    def test_parse_step_dependencies(self):
        pipeline = parse_pipeline_yaml(VALID_YAML)
        self.assertEqual(pipeline.steps[0].depends_on, [])
        self.assertEqual(pipeline.steps[1].depends_on, ["step-one"])
        self.assertEqual(pipeline.steps[2].depends_on, ["step-one"])

    def test_parse_step_types(self):
        pipeline = parse_pipeline_yaml(VALID_YAML)
        self.assertEqual(pipeline.steps[0].step_type.value, "shell_command")
        self.assertEqual(pipeline.steps[1].step_type.value, "llm_call")
        self.assertEqual(pipeline.steps[2].step_type.value, "http_request")

    def test_parse_invalid_yaml(self):
        with self.assertRaises(PipelineParseError):
            parse_pipeline_yaml("invalid: yaml: content: [")

    def test_parse_missing_name(self):
        with self.assertRaises(PipelineParseError):
            parse_pipeline_yaml("steps: []")

    def test_parse_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(VALID_YAML)
            f.flush()
            pipeline = parse_pipeline_file(f.name)
            self.assertEqual(pipeline.name, "test-pipeline")
            Path(f.name).unlink()

    def test_parse_file_not_found(self):
        with self.assertRaises(PipelineParseError):
            parse_pipeline_file("/nonexistent/file.yaml")

    def test_validate_valid_pipeline(self):
        pipeline = parse_pipeline_yaml(VALID_YAML)
        errors = validate_pipeline(pipeline)
        self.assertEqual(len(errors), 0)

    def test_validate_empty_pipeline(self):
        pipeline = parse_pipeline_yaml("name: empty\nsteps: []")
        errors = validate_pipeline(pipeline)
        self.assertTrue(any("at least one step" in e for e in errors))

    def test_validate_duplicate_steps(self):
        yaml_content = """
name: dup-test
steps:
  - name: same-name
    type: shell_command
    config:
      command: "echo 1"
  - name: same-name
    type: shell_command
    config:
      command: "echo 2"
"""
        pipeline = parse_pipeline_yaml(yaml_content)
        errors = validate_pipeline(pipeline)
        self.assertTrue(any("Duplicate" in e for e in errors))

    def test_validate_unknown_dependency(self):
        yaml_content = """
name: dep-test
steps:
  - name: step-a
    type: shell_command
    depends_on:
      - nonexistent-step
    config:
      command: "echo 1"
"""
        pipeline = parse_pipeline_yaml(yaml_content)
        errors = validate_pipeline(pipeline)
        self.assertTrue(any("unknown step" in e for e in errors))

    def test_validate_circular_dependency(self):
        yaml_content = """
name: circular-test
steps:
  - name: step-a
    type: shell_command
    depends_on:
      - step-b
    config:
      command: "echo 1"
  - name: step-b
    type: shell_command
    depends_on:
      - step-a
    config:
      command: "echo 2"
"""
        pipeline = parse_pipeline_yaml(yaml_content)
        errors = validate_pipeline(pipeline)
        self.assertTrue(any("circular" in e for e in errors))

    def test_resolve_variables(self):
        text = "Hello {{name}}, your score is {{score}}."
        variables = {"name": "World", "score": 42}
        result = resolve_variables(text, variables)
        self.assertEqual(result, "Hello World, your score is 42.")

    def test_resolve_variables_missing(self):
        text = "Hello {{name}}, {{unknown}}!"
        variables = {"name": "World"}
        result = resolve_variables(text, variables)
        self.assertEqual(result, "Hello World, {{unknown}}!")


if __name__ == "__main__":
    unittest.main()
