"""
Tests for TaskPilot-CLI core models.
"""

import unittest
from taskpilot.core.models import (
    LLMConfig,
    LLMProvider,
    Pipeline,
    PipelineResult,
    Step,
    StepResult,
    StepType,
    TaskStatus,
)


class TestModels(unittest.TestCase):
    """Test core data models."""

    def test_llm_config_defaults(self):
        config = LLMConfig()
        self.assertEqual(config.provider, LLMProvider.OPENAI)
        self.assertEqual(config.model, "gpt-4o-mini")
        self.assertAlmostEqual(config.temperature, 0.7)
        self.assertEqual(config.max_tokens, 4096)

    def test_llm_config_custom(self):
        config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet",
            temperature=0.3,
        )
        self.assertEqual(config.provider, LLMProvider.ANTHROPIC)
        self.assertEqual(config.model, "claude-3-5-sonnet")
        self.assertAlmostEqual(config.temperature, 0.3)

    def test_step_defaults(self):
        step = Step(name="test-step")
        self.assertEqual(step.name, "test-step")
        self.assertEqual(step.step_type, StepType.LLM_CALL)
        self.assertEqual(step.depends_on, [])
        self.assertEqual(step.retry_count, 0)

    def test_step_custom(self):
        step = Step(
            name="http-step",
            step_type=StepType.HTTP_REQUEST,
            depends_on=["prev-step"],
            retry_count=3,
        )
        self.assertEqual(step.step_type, StepType.HTTP_REQUEST)
        self.assertEqual(step.depends_on, ["prev-step"])
        self.assertEqual(step.retry_count, 3)

    def test_pipeline_defaults(self):
        pipeline = Pipeline(name="test-pipeline")
        self.assertEqual(pipeline.name, "test-pipeline")
        self.assertEqual(pipeline.version, "1.0.0")
        self.assertEqual(pipeline.steps, [])
        self.assertEqual(pipeline.max_parallel, 3)

    def test_step_result_to_dict(self):
        result = StepResult(
            step_name="test",
            step_id="abc123",
            status=TaskStatus.SUCCESS,
            output={"key": "value"},
            duration=1.5,
        )
        d = result.to_dict()
        self.assertEqual(d["step_name"], "test")
        self.assertEqual(d["status"], "success")
        self.assertEqual(d["duration"], 1.5)

    def test_pipeline_result_summary(self):
        result = PipelineResult(
            pipeline_name="test",
            pipeline_id="xyz",
            step_results=[
                StepResult(step_name="s1", step_id="1", status=TaskStatus.SUCCESS),
                StepResult(step_name="s2", step_id="2", status=TaskStatus.FAILED),
                StepResult(step_name="s3", step_id="3", status=TaskStatus.SKIPPED),
            ],
        )
        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.skipped_count, 1)

    def test_pipeline_result_to_dict(self):
        result = PipelineResult(
            pipeline_name="test",
            pipeline_id="xyz",
        )
        d = result.to_dict()
        self.assertIn("pipeline_name", d)
        self.assertIn("summary", d)
        self.assertEqual(d["summary"]["total_steps"], 0)

    def test_task_status_values(self):
        self.assertEqual(TaskStatus.PENDING.value, "pending")
        self.assertEqual(TaskStatus.RUNNING.value, "running")
        self.assertEqual(TaskStatus.SUCCESS.value, "success")
        self.assertEqual(TaskStatus.FAILED.value, "failed")
        self.assertEqual(TaskStatus.SKIPPED.value, "skipped")

    def test_step_type_values(self):
        self.assertEqual(StepType.LLM_CALL.value, "llm_call")
        self.assertEqual(StepType.HTTP_REQUEST.value, "http_request")
        self.assertEqual(StepType.SHELL_COMMAND.value, "shell_command")
        self.assertEqual(StepType.SCRIPT.value, "script")
        self.assertEqual(StepType.CONDITION.value, "condition")
        self.assertEqual(StepType.TRANSFORM.value, "transform")
        self.assertEqual(StepType.PARALLEL.value, "parallel")


if __name__ == "__main__":
    unittest.main()
